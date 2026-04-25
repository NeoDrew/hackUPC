"""Gemma-4 backed vision-insight agent.

Given a fatigued creative + its winning twin in the same (vertical, format)
cohort plus the structured attribute diffs, produce a 2-sentence creative
strategy insight as JSON: {headline, body, confidence}.

We talk to Gemma via the Google AI Studio (Gemini) HTTP API directly using
``httpx`` so we don't need to add the ``google-genai`` SDK. The API key is
read from ``GEMINI_API_KEY`` (or the legacy ``GOOGLE_API_KEY``) at call
time. If no key is configured, the agent returns ``None`` and the caller
falls back to canned templates and stamps ``is_stub: True`` on the response.

Outputs are cached in-memory by ``(source_id, winner_id)`` for the lifetime
of the process; the dataset is static so this is safe.
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

# Load .env once at import time so the agent picks up GEMINI_API_KEY without
# the team having to export it manually for each shell.
load_dotenv()

# Google AI Studio's Generative Language API. We use the Gemma 3 27B
# instruction-tuned model — currently the largest Gemma exposed on AI Studio.
# Override via ``VISION_INSIGHT_MODEL`` if Google promotes a newer Gemma
# variant during the hackathon.
DEFAULT_MODEL = "gemma-3-27b-it"
GENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_SYSTEM_PROMPT = (
    "You are a senior creative strategist on a mobile-advertising team. "
    "Given a fatigued creative, its winning twin, and the structured "
    "attribute differences, write a tight customer-facing insight that "
    "names the single most actionable lever the marketer can pull.\n"
    "\n"
    "HARD RULES — these matter, the marketer will read every word:\n"
    "1. The diffs array contains EVERY attribute that differs between "
    "   source and winner. If an attribute is NOT in diffs, source and "
    "   winner have IDENTICAL values for it — DO NOT mention it, DO NOT "
    "   invent a delta, DO NOT make up a value. Talking about a "
    "   non-differing attribute is grounds for failure.\n"
    "2. NEVER predict CTR / CVR / ROAS lift percentages. You have not "
    "   been given any lift data. Phrases like '+86% CTR' or 'lift of 23%' "
    "   are forbidden. Speak qualitatively: 'this attribute correlates "
    "   with higher engagement in the cohort'. The actual metrics for "
    "   source and winner are provided — quote those if you must "
    "   reference numbers, never invented deltas.\n"
    "3. NEVER use raw column names. The marketer doesn't know what "
    "   `clutter_score`, `text_density`, `cta_text`, `has_discount_badge`, "
    "   or `faces_count` mean. Translate EVERY mention to plain English:\n"
    "      clutter_score → visual clutter\n"
    "      text_density → on-screen text\n"
    "      cta_text → call-to-action wording\n"
    "      hook_type → opening hook\n"
    "      dominant_color → primary colour\n"
    "      has_discount_badge → discount badge\n"
    "      has_ugc_style → user-generated style\n"
    "      faces_count → number of people on-screen\n"
    "      novelty_score → how fresh the visual is\n"
    "      duration_sec → ad length in seconds\n"
    "      emotional_tone → emotional tone\n"
    "   Using a column name verbatim (with or without backticks) is "
    "   grounds for failure.\n"
    "4. Pick exactly ONE lever from the diffs list. Don't list multiple "
    "   changes — the marketer asked what's the *one* thing to try.\n"
    "\n"
    "Output JSON ONLY, no prose, no code fences. Schema:\n"
    "  {\"headline\": string (<= 8 words),\n"
    "   \"body\": string (<= 60 words, plain English),\n"
    "   \"confidence\": number between 0 and 1}\n"
)

# Bump this when the prompt or payload shape changes so previously-cached
# fabrications don't keep showing up after a deploy.
_CACHE_VERSION = "v3-plain-english"

# Belt-and-braces: even with the prompt forbidding column names, Gemma
# occasionally leaks one. Run the body through these substitutions before
# returning so the marketer never sees `clutter_score` etc.
_COLUMN_TRANSLATIONS: list[tuple[str, str]] = [
    # Underscore form, space-separated form (in that order so longer
    # patterns don't get partially replaced by single-word substitutions).
    ("clutter_score", "visual clutter"),
    ("clutter score", "visual clutter"),
    ("text_density", "on-screen text density"),
    ("text density", "on-screen text density"),
    ("cta_text", "call-to-action wording"),
    ("hook_type", "opening hook"),
    ("hook type", "opening hook"),
    ("dominant_color", "primary colour"),
    ("dominant color", "primary colour"),
    ("has_discount_badge", "discount badge"),
    ("has_ugc_style", "user-generated style"),
    ("ugc style", "user-generated style"),
    ("faces_count", "number of people on-screen"),
    ("faces count", "number of people on-screen"),
    ("novelty_score", "visual freshness"),
    ("novelty score", "visual freshness"),
    ("duration_sec", "ad length"),
    ("emotional_tone", "emotional tone"),
]


def _sanitize(text: str) -> str:
    """Replace any leaked raw column names + backtick-wrapped + space-
    separated variants with the plain-English equivalent."""
    out = text
    for raw, plain in _COLUMN_TRANSLATIONS:
        out = out.replace(f"`{raw}`", plain)
        out = out.replace(raw, plain)
    return out

# Process-lifetime cache.
_cache: dict[tuple[int, int], dict[str, Any]] = {}


def is_configured() -> bool:
    return bool(_api_key())


def _api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


async def generate_insight(
    *,
    source: dict[str, Any],
    winner: dict[str, Any],
    diffs: list[dict[str, Any]],
    segment: dict[str, str],
) -> dict[str, Any] | None:
    """Returns ``{headline, body, confidence}`` from Gemma, or ``None`` if the
    LLM is unavailable / errored. Caller should fall back to templates on
    None."""

    cache_key = (
        _CACHE_VERSION,
        int(source.get("creative_id", -1)),
        int(winner.get("creative_id", -1)),
    )
    cached = _cache.get(cache_key)
    if cached:
        return cached

    api_key = _api_key()
    if not api_key:
        return None

    # Send ONLY:
    #   - the cohort segment
    #   - actual measured metrics for each side (so the LLM can quote real
    #     numbers instead of inventing them)
    #   - the diffs list (every attribute that actually differs).
    # We deliberately do NOT send the full source/winner objects — that
    # invited the LLM to "compare" identical fields and fabricate deltas.
    user_payload = {
        "segment": segment,
        "source_metrics": _metrics(source),
        "winner_metrics": _metrics(winner),
        "diffs": diffs,
        "diff_field_names_present": sorted({d.get("field") for d in diffs if d.get("field")}),
    }
    # Gemma doesn't support `systemInstruction` or `responseMimeType` on
    # AI Studio yet — fold the system prompt into the user turn and parse
    # JSON from the prose response.
    user_text = (
        f"{_SYSTEM_PROMPT}\n\n"
        "Below is the structured comparison between SOURCE (fatigued) and "
        "WINNER (cohort leader). The `diffs` array is exhaustive — every "
        "attribute not in it is identical between the two. The "
        "`*_metrics` objects contain the real, measured CTR/CVR/ROAS for "
        "each side; you may quote those directly. Pick exactly ONE lever "
        "from the diffs and respond with ONLY the JSON object.\n\n"
        + json.dumps(user_payload, ensure_ascii=False)
    )

    body = {
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.2,  # tight — we want grounded output, not creative
            "maxOutputTokens": 256,
        },
    }
    model = os.environ.get("VISION_INSIGHT_MODEL", DEFAULT_MODEL)
    url = f"{GENAI_BASE}/{model}:generateContent?key={api_key}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        log.warning("vision_insight LLM call failed: %s", e)
        return None
    except Exception as e:  # noqa: BLE001
        log.warning("vision_insight unexpected error: %s", e)
        return None

    text = _extract_text(data)
    if not text:
        log.warning("vision_insight empty response: %s", data)
        return None

    parsed = _parse_json(text)
    if parsed is None:
        log.warning("vision_insight non-JSON output: %s", text[:200])
        return None

    insight = {
        "headline": _sanitize(str(parsed.get("headline") or "").strip())[:120],
        "body": _sanitize(str(parsed.get("body") or "").strip())[:600],
        "confidence": _coerce_confidence(parsed.get("confidence")),
    }
    if not insight["headline"] or not insight["body"]:
        return None
    _cache[cache_key] = insight
    return insight


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
        # If the model wrapped JSON in prose, find the first {...} block.
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _coerce_confidence(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.7
    return max(0.0, min(1.0, f))


def _metrics(creative: dict[str, Any]) -> dict[str, Any]:
    """Just the measured performance numbers for one side. Used so the LLM
    can quote real CTR/CVR/ROAS without seeing — and pattern-matching on —
    the full attribute payload."""
    keep = {
        "creative_id",
        "overall_ctr",
        "overall_cvr",
        "overall_roas",
        "ctr_decay_pct",
        "total_days_active",
    }
    return {k: v for k, v in creative.items() if k in keep}
