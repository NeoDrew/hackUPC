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

log = logging.getLogger(__name__)

load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash"
GENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_LOOP_TURNS = 6

_SYSTEM_PROMPT = (
    "You are Smadex Copilot, a creative-strategy agent for mobile advertisers. "
    "You have tools that inspect any creative's diagnosis, cohort summaries, "
    "and top performers in our portfolio. Use them aggressively before "
    "answering. Always cite specific numbers from the tool output (CTR%, CVR%, "
    "ROAS, health, days-active). Speak in DSP-native vocabulary. Never invent "
    "creative IDs, headlines, or metrics that the tools didn't return. If the "
    "user asks something unrelated to the dataset, say you can only help with "
    "Smadex creative analysis. Keep answers tight (3-5 sentences) unless the "
    "user asks for detail. End with a single concrete next step. "
    "The UI renders **bold**, *italic*, `code`, and `- ` bullet lists — use "
    "them lightly to highlight numbers and IDs, never headings."
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


_TOOL_FUNCTIONS = {
    "get_creative_diagnosis": _tool_get_creative_diagnosis,
    "get_cohort_summary": _tool_get_cohort_summary,
    "list_top_creatives": _tool_list_top_creatives,
    "get_twin": _tool_get_twin,
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
                resp = await client.post(url, json=body)
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
