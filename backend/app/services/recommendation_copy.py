"""Marketer-voice copy for slice recommendations.

Two layers, in this order:

1. ``render_template`` — deterministic f-string templates per action_type.
   Always runs; never throws. Numbers are formatted but exact.
2. ``polish_with_gemma`` — single-shot Gemma 3 27B IT call to rewrite the
   headline+rationale in tighter marketer voice. Soft-fails to the
   deterministic output if Gemma is unconfigured or errors. Strict prompt
   keeps the numbers exact and forbids new claims.

The polished copy is cached on the recommendation (``is_polished=True``)
so the request path never blocks on Gemma — polish runs once at startup
after rules fire.

The prompt borrows the same "Gemma JSON-only, system prompt folded into
user turn" pattern from ``variant_brief.py`` since AI Studio still
ignores ``systemInstruction`` for Gemma.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from ..agents._llm_retry import post_with_retry
from ..schemas import SliceRecommendation

log = logging.getLogger(__name__)

load_dotenv()

DEFAULT_MODEL = "gemma-3-27b-it"
GENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Total time budget for polishing the entire batch. Polish is a nice-to-
# have; if Gemma is slow we'd rather ship deterministic copy than block
# startup.
POLISH_BATCH_TIMEOUT_S = 60.0
POLISH_PER_REQUEST_TIMEOUT_S = 6.0


# ────────────────────────────────────────────────────────────────────
# Deterministic templates
# ────────────────────────────────────────────────────────────────────


def _fmt_money(x: float) -> str:
    if x >= 1000:
        return f"${x / 1000:.1f}k"
    return f"${x:.0f}"


def _fmt_pct(x: float) -> str:
    """x is a fraction (0.42 → '42%')."""
    return f"{x * 100:.0f}%"


def _fmt_x(x: float) -> str:
    return f"{x:.1f}×"


def render_template(rec: SliceRecommendation) -> tuple[str, str]:
    """Return ``(headline, rationale)`` for a recommendation. Headline is
    the punchy ≤8-word lead-with-delta line; rationale is the longer
    sentence with the full explanation + hedging language for projected
    impact."""
    t = rec.trigger_magnitude
    impact = _fmt_money(rec.est_daily_impact_usd)
    country = rec.country
    os_ = rec.os
    slice_label = (
        f"{country} · {os_}"
        if os_ in ("Android", "iOS")
        else country
    )

    if rec.action_type == "pause":
        # Geographic Prune
        decay = _fmt_pct(t.get("ctr_decay_pct", 0.0))
        slice_dr = t.get("slice_drop_ratio", 1.0)
        creative_dr = t.get("creative_drop_ratio", 1.0)
        head = f"Pause in {slice_label} · CTR -{decay} (7d)"
        rat = (
            f"This slice is decaying {creative_dr / max(slice_dr, 1e-6):.1f}× "
            f"faster than the creative average. Saves est. {impact}/day "
            f"at current ROAS — observational projection over the trailing "
            f"7-day window, not an experimental result."
        )
        return head, rat

    if rec.action_type == "scale":
        # Geographic Scale
        ratio = t.get("slice_roas", 0.0) / max(
            t.get("creative_roas", 1.0), 1e-9
        )
        head = f"Scale in {slice_label} · ROAS {_fmt_x(ratio)} creative avg"
        rat = (
            f"Slice is in the top decile of its (vertical, format, country) "
            f"cohort with ROAS {_fmt_x(ratio)} the creative average. Est. "
            f"+{impact}/day at a +25% bid — observational projection over "
            f"the trailing 7-day window."
        )
        return head, rat

    # Both OS Frequency Cap and Reallocation emit action_type="shift" —
    # disambiguate by which trigger keys are present.
    if rec.action_type == "shift" and "target_decay" in t:
        # OS Frequency Cap
        decay = _fmt_pct(t.get("target_decay", 0.0))
        opp = "Android" if rec.os == "iOS" else "iOS"
        head = f"Cut {rec.os} bid in {country} · CTR -{decay}"
        rat = (
            f"{rec.os} is showing fatigue (CTR -{decay}, last 7d) while "
            f"{opp} is still healthy. Industry rule of thumb: post-ATT "
            f"iOS pools fatigue 2–5 days before Android. Saves est. "
            f"{impact}/day in wasted spend."
        )
        return head, rat

    if rec.action_type == "shift" and "donor_marginal_roas" in t:
        # Reallocation
        donor_m = t.get("donor_marginal_roas", 0.0)
        recv_m = t.get("receiver_marginal_roas", 0.0)
        shift = t.get("shift_usd", 0.0)
        head = f"Shift {_fmt_money(shift)}/day · marginal ROAS {donor_m:.2f} → {recv_m:.2f}"
        rat = (
            f"Reallocate {_fmt_money(shift)}/day from a low-margin slice "
            f"(marginal ROAS {donor_m:.2f}) to a high-margin slice "
            f"(marginal ROAS {recv_m:.2f}) within this advertiser. "
            f"Est. +{impact}/day net at constant total spend — "
            f"observational projection from the trailing 14-day spend-"
            f"response curve, not an experimental result."
        )
        return head, rat

    if rec.action_type == "rotate":
        cluster = getattr(rec, "cluster_name", None)
        if cluster:
            decaying = getattr(rec, "decaying_countries_csv", "")
            n = int(t.get("cluster_size_decaying", 0))
            total = int(t.get("cluster_total_size", 0))
            head = f"Rotate creative in {cluster} · {n} of {total} markets decaying"
            rat = (
                f"{n} markets in the {cluster} cluster ({decaying}) have "
                f"crossed the 30% CTR-decay threshold. Industry rule of "
                f"thumb: cluster fatigue propagates within 3–7 days. "
                f"Rotate creative in cluster before remaining markets "
                f"follow. Est. {impact}/day at risk."
            )
            return head, rat
        # Pattern Transfer
        sib = int(getattr(rec, "sibling_creative_id", 0))
        sib_roas = t.get("sibling_target_country_roas", 0.0)
        head = f"Test in {country} · sibling wins at ROAS {_fmt_x(sib_roas)}"
        rat = (
            f"Your sibling creative #{sib} (high attribute similarity) "
            f"ranks top decile in {country} at ROAS {_fmt_x(sib_roas)}. "
            f"This creative has not been tested there. Est. +{impact}/day "
            f"if launched — observational projection from sibling slice "
            f"performance."
        )
        return head, rat

    if rec.action_type == "refresh":
        share = _fmt_pct(t.get("top_country_share", 0.0))
        drop = _fmt_pct(1.0 - t.get("top_country_drop_ratio", 1.0))
        head = f"Refresh creative · {share} concentrated in {country}, CTR -{drop}"
        rat = (
            f"{share} of this creative's impressions sit in {country}, "
            f"where CTR has dropped {drop}. Single-market dependency: if "
            f"{country} keeps fatiguing you lose the creative outright. "
            f"Diversify or replace. Est. {impact}/day at risk."
        )
        return head, rat

    if rec.action_type == "archive":
        peer_fmt = getattr(rec, "peer_format", "the leading format")
        my_fmt = getattr(rec, "my_format", "this format")
        lift = t.get("lift_multiple", 1.0)
        head = f"Replace {my_fmt} in {country} · {peer_fmt} {_fmt_x(lift)} ROAS"
        rat = (
            f"In {country}'s {my_fmt} cohort, {peer_fmt} creatives are "
            f"outperforming by {_fmt_x(lift)} on ROAS. Rotate this "
            f"creative's spend into the {peer_fmt} format to capture "
            f"the cohort lift. Est. +{impact}/day."
        )
        return head, rat

    # Unknown action_type — generic fallback.
    return (
        f"Review {slice_label}",
        f"Slice triggered an advisor rule. Est. {impact}/day at stake.",
    )


# ────────────────────────────────────────────────────────────────────
# Gemma polish (optional, soft-fails)
# ────────────────────────────────────────────────────────────────────


_POLISH_PROMPT = (
    "You are a senior media-strategy advisor writing one short sentence "
    "of guidance for a marketer named Maya. Rewrite the recommendation "
    "below in a tighter, more conversational marketer voice.\n"
    "\n"
    "HARD RULES:\n"
    "1. Keep ALL numbers exactly as given (percentages, dollar amounts, "
    "ROAS multiples, country codes, OS names). Do not invent new numbers.\n"
    "2. No new claims. Don't add reasons that aren't already in the input.\n"
    "3. One sentence, ≤ 25 words. End with a period, not a question.\n"
    "4. Output JSON only, no markdown fences. Schema:\n"
    '{"headline": string (≤ 8 words), "rationale": string (≤ 25 words)}\n'
)


def _api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def is_configured() -> bool:
    return bool(_api_key())


async def _polish_one(
    client: httpx.AsyncClient, headline: str, rationale: str, model: str, key: str
) -> tuple[str, str] | None:
    """Single Gemma call. Returns ``None`` on any failure so caller falls
    back to the deterministic copy."""
    user_text = (
        f"{_POLISH_PROMPT}\n\n"
        f'Input:\n{{"headline": {json.dumps(headline)}, '
        f'"rationale": {json.dumps(rationale)}}}\n'
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 200,
        },
    }
    url = f"{GENAI_BASE}/{model}:generateContent?key={key}"
    try:
        resp = await post_with_retry(client, url, json=body, label="gemma-polish")
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return None
        text = (
            candidates[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        # Tolerant JSON parse — strip possible code fences.
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        parsed = json.loads(cleaned)
        h = str(parsed.get("headline") or "").strip()
        r = str(parsed.get("rationale") or "").strip()
        if not h or not r:
            return None
        return h, r
    except Exception as e:  # noqa: BLE001
        log.debug("Gemma polish failed: %s", e)
        return None


async def polish_batch(
    recs: list[SliceRecommendation],
) -> None:
    """Polish every recommendation in place. Soft-fails on missing key
    (every rec keeps its deterministic template). Wall-clock capped at
    POLISH_BATCH_TIMEOUT_S — better to ship some polished + some raw than
    block startup."""
    key = _api_key()
    if not key:
        log.info("Gemma polish skipped: no API key configured")
        return
    model = os.environ.get("RECOMMENDATION_POLISH_MODEL", DEFAULT_MODEL)

    async def go() -> None:
        async with httpx.AsyncClient(timeout=POLISH_PER_REQUEST_TIMEOUT_S) as client:
            sem = asyncio.Semaphore(8)  # gentle concurrency

            async def one(rec: SliceRecommendation) -> None:
                async with sem:
                    out = await _polish_one(
                        client, rec.headline, rec.rationale, model, key
                    )
                    if out is not None:
                        rec.headline, rec.rationale = out
                        rec.is_polished = True

            await asyncio.gather(*(one(r) for r in recs))

    try:
        await asyncio.wait_for(go(), timeout=POLISH_BATCH_TIMEOUT_S)
    except asyncio.TimeoutError:
        log.warning(
            "Gemma polish batch timed out after %.0fs; some recs unpolished",
            POLISH_BATCH_TIMEOUT_S,
        )
    polished_n = sum(1 for r in recs if r.is_polished)
    log.info(
        "Gemma polish: %d / %d recommendations polished",
        polished_n,
        len(recs),
    )


def fill_copy(recs: list[SliceRecommendation]) -> None:
    """Render deterministic templates for every rec in place. Run this
    before ``polish_batch`` so every rec has at least the deterministic
    text even if Gemma is unavailable."""
    for r in recs:
        head, rat = render_template(r)
        r.headline = head
        r.rationale = rat
