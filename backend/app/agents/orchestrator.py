"""Smadex Copilot orchestrator.

Gemini 2.5 Flash with function-calling tools that read deterministic
analysis from the in-memory ``Datastore``. The LLM proposes a tool call;
the backend runs it; the result is fed back; the LLM either calls another
tool or writes the final answer. Final answer streams back to the client
as an SSE event stream so token-by-token rendering feels live.

Falls back gracefully if ``GEMINI_API_KEY`` is unset — ``stream_chat()``
emits a single error event and returns.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, AsyncIterator

import httpx
from dotenv import load_dotenv

from ..datastore import Datastore
from ..services import queries
from ._llm_retry import post_with_retry

log = logging.getLogger(__name__)

load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash"
GENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_LOOP_TURNS = 6

_SYSTEM_PROMPT = (
    "You are Smadex Copilot, advising a marketer named Maya on her ad portfolio. "
    "Speak like a senior creative-strategy advisor at the meeting — never like "
    "a data engineer or a database. Maya wants recommendations and decisions, "
    "not column dumps.\n"
    "\n"
    "HARD RULES — these matter:\n"
    "1. NEVER mention raw column names: do not say 'creative_id', 'status_band', "
    "'creative_status', 'health_breakdown', 'S/C/T/R/E/B', 'objective_mode', "
    "'posterior', 'percentile', 'credible interval'. Use plain English: 'this ad', "
    "'a similar ad', 'confidence', 'the trend', 'cohort'. Numbers are formatted "
    "(4.10× ROAS, 0.18% CTR, $24k spend, 70-day flight) — never raw decimals "
    "like 0.045 or 0.7042.\n"
    "2. When you reference a specific ad, render it as a markdown link with a "
    "short descriptive name: `[your fintech ROAS spot](#creative-500071)` or "
    "`[a similar ad in the same cohort](#creative-500147)`. The frontend turns "
    "the `#creative-NNNNNN` anchor into a clickable link to the ad's page.\n"
    "3. Each reply is 1–3 sentences in plain English. End with a SINGLE question "
    "that drives the next action — 'Would you like me to find a similar "
    "successful ad?', 'Shall I queue these changes?', 'Should I push these to "
    "the live ad?'.\n"
    "4. Read-only tools (get_creative_diagnosis, get_cohort_summary, "
    "list_top_creatives, get_twin, get_slice_recommendations) — call freely "
    "before answering.\n"
    "5. Mutating tools (apply_variant, apply_slice_recommendation, "
    "snooze_slice_recommendation, dismiss_slice_recommendation) write state. "
    "Call them ONLY after Maya has explicitly said yes ('apply', 'do it', "
    "'pause that', 'snooze it', 'dismiss it'). If unsure, ask first.\n"
    "\n"
    "THE /actions PAGE — Maya's daily action queue:\n"
    "Per-(creative · country · OS) advisor recommendations live at /actions. "
    "Each card has a single canonical verb (Pause / Rotate / Scale / Shift / "
    "Refresh / Archive), a severity (critical / warning / opportunity), and "
    "an estimated $/day impact. When Maya asks 'what should I do today?', "
    "'where is money being wasted?', 'what should I scale?' — call "
    "get_slice_recommendations and walk her through the top 2–3, leading with "
    "the dollar impact. When she says yes to one, call "
    "apply_slice_recommendation with the matching recommendation_id and a "
    "one-line rationale. When she says 'not now' / 'remind me later', call "
    "snooze_slice_recommendation. When she says 'ignore that', call "
    "dismiss_slice_recommendation.\n"
    "\n"
    "RECOMMENDATION PATTERN — diagnose, recommend, confirm:\n"
    "Turn 1: Maya asks a question → you call read tools → you reply with the "
    "diagnosis + a recommended next step + a question.\n"
    "Turn 2: Maya says yes → you call the next read tool → you describe the "
    "fix + a question asking to apply it.\n"
    "Turn 3 (only after explicit approval): you call the matching mutating "
    "tool → you confirm with a plain-language sentence (and for "
    "apply_variant, an undo link).\n"
    "\n"
    "EXAMPLES OF GOOD vs BAD OUTPUT:\n"
    "BAD:  'Creative 500071 has status_band=rescue, S=0.045, T=0.609. "
    "creative_status=stable. Recommend cohort_replace.'\n"
    "GOOD: '[Your fintech ROAS spot](#creative-500071) is fading — confidence "
    "is low and the trend is dropping. Would you like me to find a similar "
    "successful ad to compare?'"
)


# ──────────────────────────────────────────────────────────────
# Tool surface — one function per tool, mirrored in TOOL_SCHEMA.
# ──────────────────────────────────────────────────────────────


def _tool_get_creative_diagnosis(store: Datastore, creative_id: int) -> dict[str, Any]:
    detail = store.creative_detail.get(int(creative_id))
    if detail is None:
        return {"error": f"creative {creative_id} not found"}
    keep = {
        "creative_id",
        "headline",
        "advertiser_name",
        "vertical",
        "format",
        "creative_status",
        "status_band",
        "health",
        "overall_ctr",
        "overall_cvr",
        "overall_roas",
        "ctr_decay_pct",
        "cvr_decay_pct",
        "fatigue_day",
        "first_7d_ctr",
        "last_7d_ctr",
        "total_spend_usd",
        "total_revenue_usd",
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
        "quadrant",
        "saturation",
    }
    return {k: v for k, v in detail.items() if k in keep}


def _tool_get_cohort_summary(
    store: Datastore, vertical: str | None = None, format: str | None = None
) -> dict[str, Any]:
    rows = list(store.flat_row_by_creative.values())
    if vertical:
        rows = [r for r in rows if r.get("vertical") == vertical]
    if format:
        rows = [r for r in rows if r.get("format") == format]
    if not rows:
        return {"error": "no creatives match the requested cohort"}

    n = len(rows)
    avg = lambda key: sum(_safe_num(r.get(key)) for r in rows) / n
    bands: dict[str, int] = {}
    for r in rows:
        bands[r.get("status_band", "unknown")] = bands.get(r.get("status_band", "unknown"), 0) + 1

    top = sorted(rows, key=lambda r: r.get("health", 0) or 0, reverse=True)[:3]
    bottom = sorted(rows, key=lambda r: r.get("health", 0) or 0)[:3]
    summarise_row = lambda r: {
        "creative_id": r["creative_id"],
        "headline": r.get("headline"),
        "advertiser_name": r.get("advertiser_name"),
        "health": r.get("health"),
        "ctr": r.get("ctr"),
        "cvr": r.get("cvr"),
        "roas": r.get("roas"),
        "status_band": r.get("status_band"),
    }

    return {
        "cohort_size": n,
        "vertical": vertical,
        "format": format,
        "avg_ctr": round(avg("ctr"), 6),
        "avg_cvr": round(avg("cvr"), 6),
        "avg_roas": round(avg("roas"), 4),
        "avg_health": round(avg("health"), 1),
        "band_counts": bands,
        "top_3": [summarise_row(r) for r in top],
        "bottom_3": [summarise_row(r) for r in bottom],
    }


def _tool_list_top_creatives(
    store: Datastore, tab: str = "scale", limit: int = 5
) -> dict[str, Any]:
    listing = queries.list_creatives_flat(store, tab=tab, limit=limit)
    return {
        "tab": tab,
        "total": listing["total"],
        "rows": [
            {
                "creative_id": r["creative_id"],
                "headline": r.get("headline"),
                "advertiser_name": r.get("advertiser_name"),
                "vertical": r.get("vertical"),
                "format": r.get("format"),
                "status": r.get("status"),
                "status_band": r.get("status_band"),
                "health": r.get("health"),
                "ctr": r.get("ctr"),
                "cvr": r.get("cvr"),
                "roas": r.get("roas"),
            }
            for r in listing["rows"]
        ],
    }


async def _tool_get_twin(store: Datastore, creative_id: int) -> dict[str, Any]:
    twin = await queries.get_twin_stub(store, int(creative_id))
    if twin is None:
        return {"error": f"no twin found for creative {creative_id}"}
    return {
        "fatigued_id": twin["fatigued_id"],
        "winner_id": twin["winner_id"],
        "similarity": twin["similarity"],
        "segment": twin["segment"],
        "diffs": twin["diffs"],
    }


def _tool_apply_variant(
    store: Datastore, creative_id: int, rationale: str | None = None
) -> dict[str, Any]:
    """Mutating tool — only call after the user explicitly confirms. Writes
    to the in-memory queue; idempotent (re-applying the same creative_id
    overwrites the entry)."""
    return queries.queue_variant(store, int(creative_id), rationale)


def _tool_get_slice_recommendations(
    store: Datastore,
    advertiser_id: int | None = None,
    severity: str | None = None,
    top_n: int = 5,
) -> dict[str, Any]:
    """Read the pre-computed slice advisor queue. Returns the top N
    recommendations across all advertisers (or the named one), filtered
    by severity if given."""
    if advertiser_id is not None:
        flat = list(
            store.recommendations_by_advertiser.get(int(advertiser_id), [])
        )
    else:
        flat = [
            r
            for recs in store.recommendations_by_advertiser.values()
            for r in recs
        ]
    cache = store.recommendation_cache
    out: list[dict[str, Any]] = []
    for r in flat:
        if cache is not None and not cache.is_active(r.recommendation_id):
            continue
        if severity is not None and r.severity != severity:
            continue
        out.append(
            {
                "creative_id": r.creative_id,
                "country": r.country,
                "os": r.os,
                "advertiser_id": r.advertiser_id,
                "campaign_id": r.campaign_id,
                "action_type": r.action_type,
                "severity": r.severity,
                "headline": r.headline,
                "rationale": r.rationale,
                "est_daily_impact_usd": round(r.est_daily_impact_usd, 2),
            }
        )
    out.sort(key=lambda d: d["est_daily_impact_usd"], reverse=True)
    return {
        "recommendations": out[: max(1, int(top_n))],
        "total_returned": len(out[: max(1, int(top_n))]),
        "total_available": len(out),
    }


def _find_recommendation(store: Datastore, recommendation_id: str) -> Any | None:
    for recs in store.recommendations_by_advertiser.values():
        for r in recs:
            if r.recommendation_id == recommendation_id:
                return r
    return None


def _serialise_rec(rec: Any) -> dict[str, Any]:
    return {
        "recommendation_id": rec.recommendation_id,
        "creative_id": rec.creative_id,
        "country": rec.country,
        "os": rec.os,
        "action_type": rec.action_type,
        "severity": rec.severity,
        "headline": rec.headline,
        "rationale": rec.rationale,
        "est_daily_impact_usd": round(rec.est_daily_impact_usd, 2),
        "applied_at": rec.applied_at,
        "snoozed_until": rec.snoozed_until,
        "dismissed_at": rec.dismissed_at,
    }


def _tool_apply_slice_recommendation(
    store: Datastore, recommendation_id: str, rationale: str | None = None
) -> dict[str, Any]:
    """Mark a slice-level advisor recommendation as applied. MUTATES STATE
    via the recommendation cache. Caller should only invoke after explicit
    user confirmation (the system prompt enforces that pattern)."""
    rec = _find_recommendation(store, recommendation_id)
    if rec is None:
        return {"error": f"recommendation {recommendation_id} not found"}
    cache = store.recommendation_cache
    if cache is None:
        return {"error": "recommendation cache unavailable"}
    cache.mark_applied(recommendation_id)
    rec.applied_at = cache.get_state(recommendation_id).applied_at
    out = _serialise_rec(rec)
    if rationale:
        out["audit_rationale"] = rationale
    return out


def _tool_snooze_slice_recommendation(
    store: Datastore, recommendation_id: str, hours: int = 24
) -> dict[str, Any]:
    """Snooze a slice recommendation for N hours. Default 24h. MUTATES STATE."""
    rec = _find_recommendation(store, recommendation_id)
    if rec is None:
        return {"error": f"recommendation {recommendation_id} not found"}
    cache = store.recommendation_cache
    if cache is None:
        return {"error": "recommendation cache unavailable"}
    from datetime import datetime, timedelta, timezone

    h = max(1, min(24 * 30, int(hours)))
    until = (datetime.now(timezone.utc) + timedelta(hours=h)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    cache.mark_snoozed(recommendation_id, until)
    rec.snoozed_until = until
    out = _serialise_rec(rec)
    out["snoozed_for_hours"] = h
    return out


def _tool_dismiss_slice_recommendation(
    store: Datastore, recommendation_id: str
) -> dict[str, Any]:
    """Permanently dismiss a slice recommendation. MUTATES STATE."""
    rec = _find_recommendation(store, recommendation_id)
    if rec is None:
        return {"error": f"recommendation {recommendation_id} not found"}
    cache = store.recommendation_cache
    if cache is None:
        return {"error": "recommendation cache unavailable"}
    cache.mark_dismissed(recommendation_id)
    rec.dismissed_at = cache.get_state(recommendation_id).dismissed_at
    return _serialise_rec(rec)


_TOOL_FUNCTIONS = {
    "get_creative_diagnosis": _tool_get_creative_diagnosis,
    "get_cohort_summary": _tool_get_cohort_summary,
    "list_top_creatives": _tool_list_top_creatives,
    "get_twin": _tool_get_twin,
    "apply_variant": _tool_apply_variant,
    "get_slice_recommendations": _tool_get_slice_recommendations,
    "apply_slice_recommendation": _tool_apply_slice_recommendation,
    "snooze_slice_recommendation": _tool_snooze_slice_recommendation,
    "dismiss_slice_recommendation": _tool_dismiss_slice_recommendation,
}


_TOOL_SCHEMA: list[dict[str, Any]] = [
    {
        "name": "get_creative_diagnosis",
        "description": (
            "Get the full diagnosis for one creative: lifetime metrics, "
            "fatigue trajectory, attribute metadata, cohort quadrant, and "
            "portfolio saturation. Use this when the user asks about a "
            "specific creative_id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "creative_id": {
                    "type": "integer",
                    "description": "Creative ID, e.g. 500001.",
                }
            },
            "required": ["creative_id"],
        },
    },
    {
        "name": "get_cohort_summary",
        "description": (
            "Roll up performance across a cohort. Filter by vertical, format, "
            "or both. Returns size, average CTR/CVR/ROAS/health, the band "
            "distribution, and the top-3 / bottom-3 creatives by health. Use "
            "for portfolio-level questions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "vertical": {
                    "type": "string",
                    "description": (
                        "One of: ecommerce, entertainment, fintech, food_delivery, "
                        "gaming, travel. Optional."
                    ),
                },
                "format": {
                    "type": "string",
                    "description": (
                        "One of: banner, interstitial, native, playable, "
                        "rewarded_video. Optional."
                    ),
                },
            },
        },
    },
    {
        "name": "list_top_creatives",
        "description": (
            "List the top N creatives within a tab (scale=top performers, "
            "watch=stable, rescue=fatigued, cut=underperformers). Use to "
            "surface specific creative_ids the user can drill into."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tab": {
                    "type": "string",
                    "description": "One of: scale, watch, rescue, cut.",
                },
                "limit": {"type": "integer", "description": "Default 5, max 20."},
            },
        },
    },
    {
        "name": "get_twin",
        "description": (
            "For a fatigued creative, find its cohort-leader 'twin' (the "
            "highest-perf top_performer in the same vertical+format) and "
            "return the structured attribute diffs. Use when the user asks "
            "why something is losing or what the winner does differently."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "creative_id": {
                    "type": "integer",
                    "description": "Creative ID of the fatigued creative.",
                }
            },
            "required": ["creative_id"],
        },
    },
    {
        "name": "get_slice_recommendations",
        "description": (
            "Get the top N slice-level advisor recommendations across the "
            "portfolio (or for one advertiser). These are deterministic "
            "rules over per-(creative, country, OS) performance — pause/scale/"
            "rotate/shift/refresh/archive actions with $/day impact estimates. "
            "Use this when the user asks 'what should I do today?', 'where is "
            "money being wasted?', or 'what should I scale?'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "advertiser_id": {
                    "type": "integer",
                    "description": "Optional advertiser scope.",
                },
                "severity": {
                    "type": "string",
                    "description": "Optional filter: critical | warning | opportunity.",
                },
                "top_n": {
                    "type": "integer",
                    "description": "How many to return. Default 5, max 20.",
                },
            },
        },
    },
    {
        "name": "apply_slice_recommendation",
        "description": (
            "Mark a slice-level advisor recommendation as applied (the same "
            "as clicking 'Apply' on its card on the /actions page). MUTATES "
            "STATE. Only call AFTER the user has explicitly confirmed they "
            "want to take the action — phrases like 'apply', 'do it', 'yes "
            "push it', 'pause that one'. Never call proactively. Pass the "
            "exact ``recommendation_id`` from a prior get_slice_recommendations "
            "call."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "recommendation_id": {
                    "type": "string",
                    "description": "The 16-char hex id from get_slice_recommendations.",
                },
                "rationale": {
                    "type": "string",
                    "description": (
                        "One short sentence describing why we're applying this, "
                        "in plain English. Stored alongside the audit log entry."
                    ),
                },
            },
            "required": ["recommendation_id"],
        },
    },
    {
        "name": "snooze_slice_recommendation",
        "description": (
            "Snooze a slice-level advisor recommendation so it won't appear "
            "in the queue until the snooze expires. MUTATES STATE. Use when "
            "the user says 'remind me later', 'not now', 'check back tomorrow'. "
            "Default 24 hours; user can specify another duration."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "recommendation_id": {
                    "type": "string",
                    "description": "The 16-char hex id from get_slice_recommendations.",
                },
                "hours": {
                    "type": "integer",
                    "description": "How many hours to snooze. Default 24, min 1, max 720 (30 days).",
                },
            },
            "required": ["recommendation_id"],
        },
    },
    {
        "name": "dismiss_slice_recommendation",
        "description": (
            "Permanently dismiss a slice-level advisor recommendation. The "
            "recommendation will not return to the queue until the underlying "
            "data changes. MUTATES STATE. Use when the user says 'ignore that', "
            "'not relevant', 'remove it'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "recommendation_id": {
                    "type": "string",
                    "description": "The 16-char hex id from get_slice_recommendations.",
                },
            },
            "required": ["recommendation_id"],
        },
    },
    {
        "name": "apply_variant",
        "description": (
            "Queue a variant change against a creative. MUTATES STATE. Only "
            "call this after the user has explicitly confirmed — phrases like "
            "'apply', 'do it', 'yes push it'. If unsure, ask first; never call "
            "this proactively."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "creative_id": {
                    "type": "integer",
                    "description": "Creative ID of the ad to update.",
                },
                "rationale": {
                    "type": "string",
                    "description": (
                        "One-sentence explanation of what's being changed and "
                        "why, in plain English. Stored alongside the queued "
                        "entry for the audit trail."
                    ),
                },
            },
            "required": ["creative_id"],
        },
    },
]


# ──────────────────────────────────────────────────────────────
# Streaming chat
# ──────────────────────────────────────────────────────────────


def is_configured() -> bool:
    return bool(_api_key())


def _api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


async def stream_chat(
    *,
    store: Datastore,
    messages: list[dict[str, str]],
    context: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Yield SSE-formatted lines (``data: {json}\\n\\n``) describing the
    agent's progress: tool calls, tool results, streamed text deltas, and
    a final ``done`` event."""

    api_key = _api_key()
    if not api_key:
        yield _sse_event(
            "error",
            {
                "message": (
                    "Smadex Copilot needs a Gemini API key. Add "
                    "GEMINI_API_KEY to backend/.env."
                )
            },
        )
        yield _sse_event("done", {})
        return

    # Compose the conversation. Gemini takes "user"/"model" roles; we put the
    # system prompt + any UI context into the first user turn for portability
    # across model versions.
    contents: list[dict[str, Any]] = []
    preamble_parts = [_SYSTEM_PROMPT]
    context_directive = _format_context_directive(context)
    if context_directive:
        preamble_parts.append(context_directive)
    contents.append(
        {"role": "user", "parts": [{"text": "\n\n".join(preamble_parts)}]}
    )
    contents.append({"role": "model", "parts": [{"text": "Ready."}]})
    for m in messages:
        role = "user" if m.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

    model = os.environ.get("CHAT_MODEL", DEFAULT_MODEL)
    url = f"{GENAI_BASE}/{model}:generateContent?key={api_key}"

    for turn in range(MAX_LOOP_TURNS):
        body = {
            "contents": contents,
            "tools": [{"functionDeclarations": _TOOL_SCHEMA}],
            "generationConfig": {
                "temperature": 0.4,
                # Gemini 2.5 Flash thinking tokens count against this budget,
                # so a low cap clips visible prose mid-sentence. 2048 leaves
                # plenty of room even when thinking is verbose.
                "maxOutputTokens": 2048,
                # Cap thinking so most of the budget goes to the user-visible
                # answer. -1 = dynamic; 0 = disabled (faster but worse tool
                # selection).
                "thinkingConfig": {"thinkingBudget": 512},
            },
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await post_with_retry(client, url, json=body, label="gemini-chat")
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            log.warning("chat orchestrator call failed: %s", e)
            yield _sse_event("error", {"message": f"LLM error: {e}"})
            yield _sse_event("done", {})
            return

        candidates = data.get("candidates") or []
        if not candidates:
            yield _sse_event("error", {"message": "Empty response from model."})
            yield _sse_event("done", {})
            return

        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        function_calls = [p["functionCall"] for p in parts if "functionCall" in p]

        if function_calls:
            # Append the model's tool call(s) verbatim, then run each and
            # append a functionResponse turn.
            contents.append(
                {"role": "model", "parts": [{"functionCall": fc} for fc in function_calls]}
            )
            response_parts: list[dict[str, Any]] = []
            for fc in function_calls:
                name = fc.get("name", "")
                args = fc.get("args") or {}
                yield _sse_event("tool_call", {"name": name, "args": args})
                result = await _run_tool(store, name, args)
                yield _sse_event(
                    "tool_result", {"name": name, "result": _truncate(result)}
                )
                response_parts.append(
                    {"functionResponse": {"name": name, "response": {"content": result}}}
                )
            contents.append({"role": "user", "parts": response_parts})
            continue

        # Otherwise, the model produced text — emit it and finish.
        text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
        if text:
            yield _sse_event("delta", {"text": text})
        finish_reason = candidate.get("finishReason")
        if finish_reason == "MAX_TOKENS":
            log.warning("chat orchestrator hit MAX_TOKENS")
            yield _sse_event(
                "delta",
                {"text": "\n\n_…response truncated by token budget._"},
            )
        yield _sse_event("done", {})
        return

    # Loop budget exhausted.
    yield _sse_event(
        "error",
        {"message": "Reached the tool-call limit before producing an answer."},
    )
    yield _sse_event("done", {})


async def _run_tool(store: Datastore, name: str, args: dict[str, Any]) -> Any:
    fn = _TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    try:
        if name == "get_twin":
            return await fn(store, **args)  # type: ignore[arg-type]
        return fn(store, **args)
    except TypeError as e:
        return {"error": f"bad args for {name}: {e}"}
    except Exception as e:  # noqa: BLE001
        log.exception("tool %s failed", name)
        return {"error": f"tool {name} failed: {e}"}


def _truncate(value: Any, max_chars: int = 2000) -> Any:
    s = json.dumps(value, default=str)
    if len(s) <= max_chars:
        return value
    return {"truncated": True, "preview": s[:max_chars] + "…"}


def _sse_event(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _format_context_directive(context: dict[str, Any] | None) -> str | None:
    """Turn the UI context dict into an explicit directive the model will use.

    The frontend captures whatever creative/advertiser/tab the user is staring at;
    without a directive, the model treats it as background noise. With one, it
    resolves "this", "it", "why is this losing" against the right ID by default.
    """
    if not context:
        return None
    lines: list[str] = ["The user is currently viewing the Smadex Copilot UI."]
    creative_id = context.get("creative_id")
    advertiser_id = context.get("advertiser_id")
    tab = context.get("tab")
    pathname = context.get("pathname")

    if creative_id is not None:
        lines.append(
            f"They are on the page for creative {creative_id}. When they say "
            f"'this', 'it', 'this creative', or ask why something is losing/winning "
            f"without naming an ID, default to creative {creative_id} and call "
            f"get_creative_diagnosis on it before answering."
        )
        if isinstance(pathname, str) and pathname.endswith("/twin"):
            lines.append(
                f"Specifically the twin-comparison page — questions about "
                f"'the winner' or 'the twin' refer to creative {creative_id}'s "
                f"cohort leader; call get_twin first."
            )
        elif isinstance(pathname, str) and "/variant" in pathname:
            lines.append(
                "Specifically the variant page — they are about to ship a "
                "remix of this creative."
            )
    if advertiser_id is not None:
        lines.append(
            f"They are scoped to advertiser {advertiser_id}. Cohort and 'top "
            f"creatives' questions should be filtered to that advertiser when "
            f"possible."
        )
    if tab in {"scale", "watch", "rescue", "cut"}:
        lines.append(
            f"They are on the '{tab}' tab. If they ask about 'top' or 'these' "
            f"creatives without specifying, default list_top_creatives to "
            f"tab='{tab}'."
        )
    if len(lines) == 1:
        # No actionable context found — still pass the raw payload so the
        # model can decide what (if anything) it means.
        return "Current UI context: " + json.dumps(context)
    return "\n".join(lines)


def _safe_num(v: Any) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
