"""Slice-advisor recommendation routes.

GET  /api/recommendations          — ranked list (filterable)
POST /api/recommendations/{id}/apply
POST /api/recommendations/{id}/snooze
POST /api/recommendations/{id}/dismiss

The recommendations themselves are computed at startup (see
``Datastore._compute_slice_advisor``); the routes here read from that
cache and overlay the user's mutable state from
``store.recommendation_cache``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..datastore import get_store
from ..schemas import (
    ApplyRecommendationResponse,
    RecommendationsList,
    SliceRecommendation,
    SnoozeRequest,
)

log = logging.getLogger(__name__)
router = APIRouter()


def _apply_state(
    rec: SliceRecommendation, store: Any
) -> SliceRecommendation:
    """Overlay the user-touched state from the cache onto a freshly-emitted
    recommendation. Cheap copy because we're mutating a Pydantic model in
    place; the cache is the source of truth for state."""
    cache = store.recommendation_cache
    if cache is None:
        return rec
    state = cache.get_state(rec.recommendation_id)
    rec.applied_at = state.applied_at
    rec.snoozed_until = state.snoozed_until
    rec.dismissed_at = state.dismissed_at
    return rec


def _find_rec(
    store: Any, recommendation_id: str
) -> SliceRecommendation | None:
    for recs in store.recommendations_by_advertiser.values():
        for r in recs:
            if r.recommendation_id == recommendation_id:
                return r
    return None


@router.get("/recommendations", response_model=RecommendationsList)
def list_recommendations(
    advertiser_id: int | None = Query(None),
    campaign_id: int | None = Query(None),
    severity: str | None = Query(None),
    action_type: str | None = Query(None),
    include_inactive: bool = Query(
        False,
        description="If true, return snoozed/dismissed recs as well (for the audit trail).",
    ),
) -> dict:
    store = get_store()
    cache = store.recommendation_cache

    # Flatten (optionally) advertiser-scoped recs.
    if advertiser_id is not None:
        flat = list(store.recommendations_by_advertiser.get(advertiser_id, []))
    else:
        flat = [
            r
            for recs in store.recommendations_by_advertiser.values()
            for r in recs
        ]

    out: list[SliceRecommendation] = []
    for r in flat:
        if campaign_id is not None and r.campaign_id != campaign_id:
            continue
        if severity is not None and r.severity != severity:
            continue
        if action_type is not None and r.action_type != action_type:
            continue
        # Apply mutable state.
        _apply_state(r, store)
        if not include_inactive and cache is not None:
            if not cache.is_active(r.recommendation_id):
                continue
        out.append(r)

    # Resort by impact desc (state mutation may not have moved them).
    out.sort(key=lambda r: r.est_daily_impact_usd, reverse=True)

    counts_by_severity: dict[str, int] = {}
    counts_by_action: dict[str, int] = {}
    total_impact = 0.0
    for r in out:
        total_impact += r.est_daily_impact_usd
        counts_by_severity[r.severity] = counts_by_severity.get(r.severity, 0) + 1
        counts_by_action[r.action_type] = counts_by_action.get(r.action_type, 0) + 1

    return {
        "recommendations": [r.model_dump() for r in out],
        "total_daily_impact_usd": float(total_impact),
        "counts_by_severity": counts_by_severity,
        "counts_by_action_type": counts_by_action,
    }


@router.post(
    "/recommendations/{recommendation_id}/apply",
    response_model=ApplyRecommendationResponse,
)
def apply_recommendation(recommendation_id: str) -> dict:
    store = get_store()
    rec = _find_rec(store, recommendation_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="recommendation not found")
    cache = store.recommendation_cache
    if cache is None:
        raise HTTPException(status_code=503, detail="recommendation cache unavailable")
    cache.mark_applied(recommendation_id)
    _apply_state(rec, store)
    return {
        "recommendation_id": recommendation_id,
        "applied": True,
        "entry": rec.model_dump(),
    }


@router.post(
    "/recommendations/{recommendation_id}/snooze",
    response_model=ApplyRecommendationResponse,
)
def snooze_recommendation(recommendation_id: str, body: SnoozeRequest) -> dict:
    store = get_store()
    rec = _find_rec(store, recommendation_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="recommendation not found")
    cache = store.recommendation_cache
    if cache is None:
        raise HTTPException(status_code=503, detail="recommendation cache unavailable")
    cache.mark_snoozed(recommendation_id, body.until)
    _apply_state(rec, store)
    return {
        "recommendation_id": recommendation_id,
        "applied": False,
        "entry": rec.model_dump(),
    }


@router.post(
    "/recommendations/{recommendation_id}/dismiss",
    response_model=ApplyRecommendationResponse,
)
def dismiss_recommendation(recommendation_id: str) -> dict:
    store = get_store()
    rec = _find_rec(store, recommendation_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="recommendation not found")
    cache = store.recommendation_cache
    if cache is None:
        raise HTTPException(status_code=503, detail="recommendation cache unavailable")
    cache.mark_dismissed(recommendation_id)
    _apply_state(rec, store)
    return {
        "recommendation_id": recommendation_id,
        "applied": False,
        "entry": rec.model_dump(),
    }


@router.get("/portfolio/advisor-diagnostics")
def advisor_diagnostics() -> dict:
    """Coverage stats for the demo: how many creatives produced ≥1
    recommendation, distribution of action types, mean impact per type,
    top 10 advertisers by total at-stake $/day."""
    store = get_store()
    flat: list[SliceRecommendation] = [
        r
        for recs in store.recommendations_by_advertiser.values()
        for r in recs
    ]
    total = len(flat)
    by_action: dict[str, list[float]] = {}
    by_severity: dict[str, int] = {}
    creatives_with_rec: set[int] = set()
    impact_by_advertiser: dict[int, float] = {}
    polished = 0
    for r in flat:
        creatives_with_rec.add(r.creative_id)
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_action.setdefault(r.action_type, []).append(r.est_daily_impact_usd)
        impact_by_advertiser[r.advertiser_id] = (
            impact_by_advertiser.get(r.advertiser_id, 0.0) + r.est_daily_impact_usd
        )
        if r.is_polished:
            polished += 1

    action_summary = {
        a: {
            "count": len(vs),
            "mean_impact_usd": float(sum(vs) / max(len(vs), 1)),
            "total_impact_usd": float(sum(vs)),
        }
        for a, vs in by_action.items()
    }
    top_adv = sorted(
        impact_by_advertiser.items(), key=lambda kv: kv[1], reverse=True
    )[:10]

    return {
        "total_recommendations": total,
        "n_creatives_covered": len(creatives_with_rec),
        "n_creatives_total": len(store.creative_detail),
        "coverage_pct": (
            len(creatives_with_rec) / max(len(store.creative_detail), 1)
        ),
        "by_severity": by_severity,
        "by_action_type": action_summary,
        "top_advertisers_by_impact": [
            {"advertiser_id": adv, "total_daily_impact_usd": float(v)}
            for adv, v in top_adv
        ],
        "polished_pct": polished / max(total, 1),
        "n_slices_with_features": len(store.slice_features),
        "n_slices_with_marginal_roas": len(store.marginal_roas_by_slice),
    }
