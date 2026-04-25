"""Gemma-4 backed variant-brief agent.

Given a fatigued source creative + its cohort-leader twin + the structured
attribute diffs, produce a fully-realised creative brief for the *next* ad
to run: a fresh headline / subhead / CTA written in the source advertiser's
voice plus 3–4 bullet-point rationales that explain why each choice was made.

Replaces the previous templated brief on the variant page (which was just
the winner's metadata copy-pasted with hardcoded rationale strings).

Same pattern as ``vision_insight.py`` — direct httpx call to Google AI
Studio, system prompt folded into the user turn (Gemma doesn't honour
``systemInstruction`` on AI Studio), tolerant JSON parser, in-memory cache
keyed by ``(source_id, winner_id)``. Returns ``None`` if Gemma is
unconfigured or errors; caller falls back to the template brief.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv

log = logging.getLogger(__name__)

load_dotenv()

DEFAULT_MODEL = "gemma-3-27b-it"
GENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_SYSTEM_PROMPT = (
    "You are a senior creative director on a mobile-advertising team writing "
    "the brief for a fresh ad creative. The current ad is fatiguing; you've "
    "been shown a similar ad in the same vertical and format that's "
    "outperforming, plus the structured attribute differences between them. "
    "Write a NEW brief — don't just paraphrase the winner. Adopt the winner's "
    "winning attributes (CTA copy, dominant colour, hook, discount proof if "
    "present) but tailor the headline + subhead to the source advertiser's "
    "brand voice. The marketer will read this and decide whether to push it.\n"
    "\n"
    "Output JSON ONLY, no prose, no code fences. Schema:\n"
    "{\n"
    '  "headline": string (<= 8 words, punchy, in the source advertiser\'s voice),\n'
    '  "subhead":  string (<= 12 words, complements the headline),\n'
    '  "cta":      string (<= 4 words, action verb),\n'
    '  "dominant_color": string (the colour to lean on),\n'
    '  "emotional_tone": string (one word),\n'
    '  "rationale": array of 3 to 4 strings (each <= 25 words, plain English, '
    "explaining why this choice — never mention DB columns like creative_id "
    "or status_band; speak to the marketer)\n"
    "}\n"
)

# Process-lifetime cache keyed by (source_id, winner_id).
_cache: dict[tuple[int, int], dict[str, Any]] = {}


def is_configured() -> bool:
    return bool(_api_key())


def _api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


async def generate_brief(
    *,
    source: dict[str, Any],
    winner: dict[str, Any],
    diffs: list[dict[str, Any]],
    segment: dict[str, str],
) -> dict[str, Any] | None:
    """Returns the brief dict from Gemma, or ``None`` if the model is
    unavailable / errored. Caller should fall back to a template.
    """
    cache_key = (
        int(source.get("creative_id", -1)),
        int(winner.get("creative_id", -1)),
    )
    cached = _cache.get(cache_key)
    if cached:
        return cached

    api_key = _api_key()
    if not api_key:
        return None

    payload = {
        "segment": segment,
        "source_advertiser": source.get("advertiser_name"),
        "source": _trim(source),
        "winner": _trim(winner),
        "diffs": diffs,
    }
    user_text = (
        f"{_SYSTEM_PROMPT}\n\n"
        "Read the inputs below and write the new brief. Return ONLY the JSON.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    body = {
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.7,  # higher than vision_insight — we want creative variety
            "maxOutputTokens": 512,
        },
    }
    model = os.environ.get("VARIANT_BRIEF_MODEL", DEFAULT_MODEL)
    url = f"{GENAI_BASE}/{model}:generateContent?key={api_key}"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        log.warning("variant_brief LLM call failed: %s", e)
        return None
    except Exception as e:  # noqa: BLE001
        log.warning("variant_brief unexpected error: %s", e)
        return None

    text = _extract_text(data)
    if not text:
        log.warning("variant_brief empty response: %s", data)
        return None

    parsed = _parse_json(text)
    if parsed is None:
        log.warning("variant_brief non-JSON output: %s", text[:300])
        return None

    rationale_raw = parsed.get("rationale") or []
    if not isinstance(rationale_raw, list):
        return None

    brief = {
        "headline": str(parsed.get("headline") or "").strip()[:120],
        "subhead": str(parsed.get("subhead") or "").strip()[:160],
        "cta": str(parsed.get("cta") or "").strip()[:40],
        "dominant_color": str(parsed.get("dominant_color") or "").strip()[:24],
        "emotional_tone": str(parsed.get("emotional_tone") or "").strip()[:24],
        "rationale": [str(r).strip()[:240] for r in rationale_raw if str(r).strip()][:5],
    }
    if (
        not brief["headline"]
        or not brief["cta"]
        or len(brief["rationale"]) < 2
    ):
        return None

    _cache[cache_key] = brief
    return brief


def _extract_text(data: dict[str, Any]) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts).strip()


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def _parse_json(text: str) -> dict[str, Any] | None:
    cleaned = _FENCE_RE.sub("", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _trim(creative: dict[str, Any]) -> dict[str, Any]:
    keep = {
        "creative_id",
        "advertiser_name",
        "headline",
        "subhead",
        "vertical",
        "format",
        "theme",
        "hook_type",
        "cta_text",
        "dominant_color",
        "emotional_tone",
        "duration_sec",
        "text_density",
        "clutter_score",
        "novelty_score",
        "has_discount_badge",
        "has_ugc_style",
        "faces_count",
        "language",
    }
    return {k: v for k, v in creative.items() if k in keep}
