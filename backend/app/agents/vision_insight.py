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
    "Given a fatigued creative and its winning twin in the same vertical and "
    "format, plus structured attribute diffs, write a tight insight that "
    "names the single most actionable lever the marketer can pull. Output "
    "JSON only, no prose, no code fences. Schema: {\"headline\": string "
    "(<= 8 words), \"body\": string (<= 60 words), \"confidence\": number "
    "between 0 and 1}. Speak in DSP-native terms: cite specific attributes, "
    "name the trade-off, recommend a concrete next step."
)

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

    cache_key = (int(source.get("creative_id", -1)), int(winner.get("creative_id", -1)))
    cached = _cache.get(cache_key)
    if cached:
        return cached

    api_key = _api_key()
    if not api_key:
        return None

    user_payload = {
        "segment": segment,
        "source": _trim(source),
        "winner": _trim(winner),
        "diffs": diffs,
    }
    # Gemma doesn't support `systemInstruction` or `responseMimeType` on
    # AI Studio yet — fold the system prompt into the user turn and parse
    # JSON from the prose response.
    user_text = (
        f"{_SYSTEM_PROMPT}\n\n"
        "Analyse the diffs between SOURCE (fatigued) and WINNER (cohort leader). "
        "Pick the single most actionable lever and respond with ONLY the JSON "
        "object — no prose, no code fences.\n\n"
        + json.dumps(user_payload, ensure_ascii=False)
    )

    body = {
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.4,
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
        "headline": str(parsed.get("headline") or "").strip()[:120],
        "body": str(parsed.get("body") or "").strip()[:600],
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


def _trim(creative: dict[str, Any]) -> dict[str, Any]:
    """Drop bulky fields before sending to the LLM."""
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
        "overall_ctr",
        "overall_cvr",
        "creative_status",
        "ctr_decay_pct",
    }
    return {k: v for k, v in creative.items() if k in keep}
