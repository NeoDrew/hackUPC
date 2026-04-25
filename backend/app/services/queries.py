"""Pure-function lookups over the in-memory Datastore.

These functions return JSON-serialisable dicts that pydantic schemas in
`app.schemas` validate. No FastAPI imports here — keeps the analysis layer
testable in isolation.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..agents import vision_insight as vision_insight_agent
from ..datastore import Datastore
from ..schemas import to_jsonable


def list_advertisers(store: Datastore) -> list[dict[str, Any]]:
    return store.advertisers.to_dict("records")


def get_advertiser(store: Datastore, advertiser_id: int) -> dict[str, Any] | None:
    rows = store.advertisers[store.advertisers["advertiser_id"] == advertiser_id]
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()


def list_campaigns_for_advertiser(
    store: Datastore, advertiser_id: int
) -> list[dict[str, Any]]:
    rows = store.campaigns[store.campaigns["advertiser_id"] == advertiser_id]
    return [_campaign_record(row) for _, row in rows.iterrows()]


def get_campaign(store: Datastore, campaign_id: int) -> dict[str, Any] | None:
    rows = store.campaigns[store.campaigns["campaign_id"] == campaign_id]
    if rows.empty:
        return None
    return _campaign_record(rows.iloc[0])


def list_creatives_for_campaign(
    store: Datastore, campaign_id: int
) -> list[dict[str, Any]]:
    rows = store.creatives[store.creatives["campaign_id"] == campaign_id]
    summary = store.creative_summary.set_index("creative_id")["creative_status"].to_dict()
    out: list[dict[str, Any]] = []
    for _, row in rows.iterrows():
        creative_id = int(row["creative_id"])
        out.append(
            {
                "creative_id": creative_id,
                "campaign_id": int(row["campaign_id"]),
                "advertiser_name": row["advertiser_name"],
                "vertical": row["vertical"],
                "format": row["format"],
                "theme": row["theme"],
                "creative_status": summary.get(creative_id),
                "asset_file": row["asset_file"],
            }
        )
    return out


def get_creative_detail(
    store: Datastore, creative_id: int
) -> dict[str, Any] | None:
    record = store.creative_detail.get(creative_id)
    if record is None:
        return None
    return to_jsonable(record)


def get_creative_timeseries(
    store: Datastore, creative_id: int
) -> dict[str, Any] | None:
    points = store.timeseries_by_creative.get(creative_id)
    if points is None:
        return None
    return {"creative_id": creative_id, "points": points}


# --- Cockpit / portfolio queries ---


_STATUS_TAB_MAP: dict[str, str] = {
    "scale": "top_performer",
    "watch": "stable",
    "rescue": "fatigued",
    "cut": "underperformer",
}

_ROW_SORTABLE = {
    "ctr",
    "cvr",
    "roas",
    "spend_usd",
    "revenue_usd",
    "impressions",
    "clicks",
    "conversions",
    "health",
    "days_active",
}


def portfolio_kpis(store: Datastore) -> dict[str, Any]:
    return store.portfolio_kpis


def tab_counts(store: Datastore) -> dict[str, int]:
    return store.tab_counts


def search_creatives(
    store: Datastore, query: str, limit: int = 8
) -> list[dict[str, Any]]:
    """Return weighted-relevance matches for ``query`` across creative fields.

    Priority order (descending weight):
      - Exact creative_id match (numeric query)
      - Headline substring
      - Advertiser name substring
      - Theme / hook_type / cta_text substring
      - Vertical / format substring
    """
    q = query.strip().lower()
    if not q:
        return []
    rows = list(store.flat_row_by_creative.values())

    # Pull richer fields from creative_detail for theme/hook/cta matches.
    detail_lookup = store.creative_detail

    matches: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        cid = row["creative_id"]
        d = detail_lookup.get(cid, {})
        score = 0.0

        # Exact creative-id match (when the user types a number).
        if q.isdigit() and int(q) == cid:
            score += 10.0

        headline = (row.get("headline") or "").lower()
        if q in headline:
            # Boost when the headline starts with the query.
            score += 6.0 if headline.startswith(q) else 5.0

        advertiser = (row.get("advertiser_name") or "").lower()
        if q in advertiser:
            score += 3.0

        for field in ("theme", "hook_type", "cta_text"):
            v = str(d.get(field) or "").lower()
            if v and q in v:
                score += 1.5

        for field in ("vertical", "format"):
            v = (row.get(field) or "").lower()
            if v and q in v:
                score += 1.0

        if score <= 0:
            continue
        matches.append((score, row))

    matches.sort(key=lambda t: (t[0], t[1].get("health") or 0), reverse=True)
    out: list[dict[str, Any]] = []
    for score, row in matches[:limit]:
        d = detail_lookup.get(row["creative_id"], {})
        out.append(
            {
                "creative_id": row["creative_id"],
                "headline": row.get("headline"),
                "advertiser_name": row.get("advertiser_name"),
                "vertical": row.get("vertical"),
                "format": row.get("format"),
                "status_band": row.get("status_band"),
                "status": row.get("status"),
                "health": row.get("health"),
                "asset_file": row.get("asset_file"),
                "theme": d.get("theme"),
                "hook_type": d.get("hook_type"),
                "score": round(float(score), 2),
            }
        )
    return out


def list_creatives_flat(
    store: Datastore,
    *,
    tab: str | None = None,
    status: str | None = None,
    vertical: str | None = None,
    format: str | None = None,
    sort: str | None = None,
    desc: bool = True,
    limit: int | None = None,
) -> dict[str, Any]:
    """Flat creative list, wrapped with pre-pagination ``total``.

    ``tab`` filters by our computed ``status_band`` (scale/watch/rescue/cut).
    ``explore`` (or no tab) returns the whole portfolio. ``status`` filters by
    the dataset's raw ``creative_status`` label — used only by debug paths.
    """
    rows = list(store.flat_row_by_creative.values())

    if tab and tab != "explore":
        target = _STATUS_TAB_MAP.get(tab)
        if target is None:
            return {"rows": [], "total": 0, "limit": limit}
        rows = [r for r in rows if r["status"] == target]
    elif status:
        rows = [r for r in rows if r["status"] == status]

    if vertical:
        rows = [r for r in rows if r["vertical"] == vertical]
    if format:
        rows = [r for r in rows if r["format"] == format]

    if sort and sort in _ROW_SORTABLE:
        rows.sort(key=lambda r: r.get(sort) or 0, reverse=desc)
    else:
        rows.sort(key=lambda r: r.get("health") or 0, reverse=True)

    total = len(rows)
    if limit is not None:
        rows = rows[:limit]
    return {"rows": rows, "total": total, "limit": limit}


# --- Twin stub ---


_VISION_TEMPLATES: dict[str, dict[str, str]] = {
    "text_density": {
        "headline": "Twin runs leaner copy",
        "body": (
            "Your fatigued creative carries roughly twice the on-screen text. "
            "The cohort leader keeps text density low and lets the product hero "
            "carry the message; the audience reads it in under a second."
        ),
    },
    "clutter_score": {
        "headline": "Twin reduces visual clutter",
        "body": (
            "The winner sits on a cleaner background with one clear focal point. "
            "Lower clutter correlates with higher CTR in this cohort: the eye "
            "lands on the offer instead of having to scan."
        ),
    },
    "has_discount_badge": {
        "headline": "Twin leans on a price proof",
        "body": (
            "The winner shows a discount badge prominently; your fatigued "
            "creative does not. In this cohort the winning attribute combo "
            "average 1.6× the conversion rate of equivalents without it."
        ),
    },
    "novelty_score": {
        "headline": "Twin feels less repetitive",
        "body": (
            "The winner's novelty score sits well above average for its cohort. "
            "Your fatigued creative is one of several near-duplicates in the "
            "portfolio — audience saturation is suppressing CTR."
        ),
    },
    "default": {
        "headline": "Twin is winning on attribute fit",
        "body": (
            "The winning creative in this cohort outperforms on the dominant "
            "attributes for its vertical and format. The diffs below show "
            "where to focus the next test."
        ),
    },
}


_TWIN_FIELDS: list[str] = [
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
]


async def get_twin_stub(store: Datastore, creative_id: int) -> dict[str, Any] | None:
    """Pick the *most attribute-similar* top_performer within the same
    (vertical, format) cohort using cosine similarity over a per-creative
    feature vector (one-hot categoricals + normalised numerics + binary
    flags). Returns the real similarity score in ``similarity``.

    The diff table is computed on the picked twin's attributes vs the
    source. Vision insight comes from Gemma when configured; otherwise
    falls back to a 3-template body keyed on the largest diff.
    """
    import numpy as np

    source = store.creative_detail.get(creative_id)
    if source is None:
        return None

    summary = store.creative_summary
    cohort = summary[
        (summary["vertical"] == source["vertical"])
        & (summary["format"] == source["format"])
        & (summary["creative_status"] == "top_performer")
        & (summary["creative_id"] != creative_id)
    ]
    if cohort.empty:
        # Fall back to any top performer in the same vertical.
        cohort = summary[
            (summary["vertical"] == source["vertical"])
            & (summary["creative_status"] == "top_performer")
            & (summary["creative_id"] != creative_id)
        ]
    if cohort.empty:
        return None

    source_vec = store.creative_vectors.get(creative_id)
    if source_vec is None:
        # Vector unavailable for some reason — fall back to the cohort leader.
        winner_row = cohort.sort_values("perf_score", ascending=False).iloc[0]
        winner_id = int(winner_row["creative_id"])
        similarity = 0.0
    else:
        best_id: int | None = None
        best_sim = -1.0
        for cid in cohort["creative_id"]:
            cid_int = int(cid)
            v = store.creative_vectors.get(cid_int)
            if v is None:
                continue
            sim = float(np.dot(source_vec, v))
            if sim > best_sim:
                best_sim = sim
                best_id = cid_int
        if best_id is None:
            return None
        winner_id = best_id
        similarity = max(0.0, min(1.0, best_sim))

    winner = store.creative_detail.get(winner_id)
    if winner is None:
        return None

    diffs: list[dict[str, Any]] = []
    largest_field = "default"
    largest_template_magnitude = 0.0
    for field_name in _TWIN_FIELDS:
        sv = source.get(field_name)
        wv = winner.get(field_name)
        if sv == wv:
            continue
        diffs.append(_diff_row(field_name, sv, wv))
        # Only score template-eligible fields against each other so 0–1 scores
        # are not dominated by raw counts.
        if field_name in _VISION_TEMPLATES:
            magnitude = _diff_magnitude(field_name, sv, wv)
            if magnitude > largest_template_magnitude:
                largest_template_magnitude = magnitude
                largest_field = field_name

    segment = {"vertical": source["vertical"], "format": source["format"]}
    template = _VISION_TEMPLATES.get(largest_field, _VISION_TEMPLATES["default"])
    template_insight = {
        "headline": template["headline"],
        "body": template["body"],
        "confidence": 0.74,
    }

    # Try Gemma; on success the response is non-stub (UI hides [preview] chip).
    llm_insight = await vision_insight_agent.generate_insight(
        source=source,
        winner=winner,
        diffs=diffs,
        segment=segment,
    )
    insight = llm_insight or template_insight
    is_stub = llm_insight is None

    return {
        "fatigued_id": creative_id,
        "winner_id": winner_id,
        "similarity": round(similarity, 3),
        "segment": segment,
        "diffs": diffs,
        "vision_insight": insight,
        # is_stub now reflects only the Vision Insight provenance — the twin
        # pick itself is real attribute-cosine matching.
        "is_stub": is_stub,
    }


def _diff_row(field_name: str, sv: Any, wv: Any) -> dict[str, Any]:
    direction = "neu"
    impact = "low"
    if isinstance(sv, (int, float)) and isinstance(wv, (int, float)):
        delta = (wv - sv) if sv is not None and wv is not None else 0
        if delta > 0:
            direction = "pos"
        elif delta < 0:
            direction = "neg"
        magnitude = abs(delta) / (abs(sv) + 1e-6) if sv else abs(delta)
        if magnitude > 0.5:
            impact = "high"
        elif magnitude > 0.15:
            impact = "medium"
    elif isinstance(wv, str) and isinstance(sv, str):
        impact = "medium"
    return {
        "field": field_name,
        "source_value": sv,
        "twin_value": wv,
        "direction": direction,
        "impact": impact,
    }


def _diff_magnitude(field_name: str, sv: Any, wv: Any) -> float:
    if isinstance(sv, (int, float)) and isinstance(wv, (int, float)):
        return abs((wv or 0) - (sv or 0))
    if sv != wv:
        return 1.0
    return 0.0


def _campaign_record(row: pd.Series) -> dict[str, Any]:
    record = row.to_dict()
    return to_jsonable(record)
