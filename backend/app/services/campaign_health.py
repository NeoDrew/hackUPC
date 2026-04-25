"""Campaign-level composite health score.

Transparent rollup of existing per-creative outputs:

  * **% creatives fatigued**  — Krish's changepoint detector (high = bad)
  * **Mean drop_ratio**       — last-week CTR / first-week CTR (low = bad)
  * **Aggregate ctr_cv**      — std/mean of campaign daily CTR (high = bad)
  * **Cohort rank pct**       — campaign's percentile in (vertical, objective)
                                cohort across all 36 advertisers, by lifetime
                                ROAS (high = good)

No new training. Weights are heuristic, not learned — surfaced honestly in
the breakdown panel so judges can defend it.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..datastore import Datastore


WEIGHTS = {
    "fatigued": 0.30,
    "drop_ratio": 0.25,
    "ctr_cv": 0.20,
    "cohort_rank": 0.25,
}


def _clip01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def compute(store: "Datastore", campaign_id: int) -> dict[str, Any]:
    """Composite health score for one campaign.

    Returns a dict with ``health`` (int 0-100) and ``components`` (the four
    raw inputs for the breakdown panel). Returns a zeroed payload if the
    campaign has no creatives in scope.
    """
    cids = sorted(
        cid
        for cid, row in store.flat_row_by_creative.items()
        if row.get("campaign_id") == campaign_id
    )
    if not cids:
        return _empty()

    # 1. % creatives fatigued.
    fatigued = sum(
        1
        for cid in cids
        if (store.predicted_fatigue.get(cid) or {}).get("is_fatigued")
    )
    pct_fatigued = fatigued / len(cids)

    # 2. Mean drop_ratio across creatives that have non-zero pre_ctr.
    ratios: list[float] = []
    for cid in cids:
        v = store.predicted_fatigue.get(cid) or {}
        pre = float(v.get("pre_ctr") or 0.0)
        post = float(v.get("post_ctr") or 0.0)
        if pre > 0:
            ratios.append(post / pre)
    mean_drop_ratio = float(np.mean(ratios)) if ratios else 1.0

    # 3. Aggregate ctr_cv: std/mean of campaign daily CTR over the dataset.
    df = store.daily
    cdf = df[df["creative_id"].isin(cids)]
    if not cdf.empty:
        per_day = cdf.groupby("date").agg(
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
        )
        daily_ctr = np.where(
            per_day["impressions"].to_numpy() > 0,
            per_day["clicks"].to_numpy()
            / np.maximum(per_day["impressions"].to_numpy(), 1),
            0.0,
        )
        mu = float(daily_ctr.mean())
        sigma = float(daily_ctr.std())
        agg_ctr_cv = (sigma / mu) if mu > 1e-9 else 0.0
    else:
        agg_ctr_cv = 0.0

    # 4. Cohort rank pct — precomputed at startup. Falls back to 0.5 (median)
    # when the cohort wasn't built (e.g. unseen campaign).
    cohort_rank_pct = float(
        store.campaign_cohort_rank_pct.get(int(campaign_id), 0.5)
    )

    # Composite. Each component normalised so high = good before weighting.
    score_unit = (
        WEIGHTS["fatigued"] * (1.0 - pct_fatigued)
        + WEIGHTS["drop_ratio"] * _clip01(mean_drop_ratio)
        + WEIGHTS["ctr_cv"] * (1.0 - _clip01(agg_ctr_cv / 1.5))
        + WEIGHTS["cohort_rank"] * cohort_rank_pct
    )
    health = int(round(100 * score_unit))
    if health < 0:
        health = 0
    if health > 100:
        health = 100

    return {
        "health": health,
        "components": {
            "pct_fatigued": round(pct_fatigued, 4),
            "mean_drop_ratio": round(mean_drop_ratio, 4),
            "agg_ctr_cv": round(agg_ctr_cv, 4),
            "cohort_rank_pct": round(cohort_rank_pct, 4),
            "creative_count": len(cids),
            "fatigued_count": fatigued,
        },
        "weights": dict(WEIGHTS),
    }


def _empty() -> dict[str, Any]:
    return {
        "health": 0,
        "components": {
            "pct_fatigued": 0.0,
            "mean_drop_ratio": 1.0,
            "agg_ctr_cv": 0.0,
            "cohort_rank_pct": 0.5,
            "creative_count": 0,
            "fatigued_count": 0,
        },
        "weights": dict(WEIGHTS),
    }


def precompute_cohort_ranks(store: "Datastore") -> dict[int, float]:
    """Rank every campaign within its (vertical, objective) cohort by
    lifetime ROAS, across all 36 advertisers. Returns ``{campaign_id:
    pct}`` where pct ∈ [0, 1] and 1 = best in cohort.
    """
    # Sum spend + revenue per campaign from creative_summary via creatives→campaigns join.
    creatives = store.creatives[["creative_id", "campaign_id"]]
    s = store.creative_summary[
        ["creative_id", "total_spend_usd", "total_revenue_usd"]
    ]
    joined = creatives.merge(s, on="creative_id", how="left")
    per_campaign = joined.groupby("campaign_id", as_index=False).agg(
        total_spend_usd=("total_spend_usd", "sum"),
        total_revenue_usd=("total_revenue_usd", "sum"),
    )
    per_campaign["roas"] = np.where(
        per_campaign["total_spend_usd"] > 0,
        per_campaign["total_revenue_usd"] / per_campaign["total_spend_usd"],
        0.0,
    )

    # Attach cohort key (vertical, objective) from campaigns.
    cohort_meta = store.campaigns[["campaign_id", "vertical", "objective"]]
    per_campaign = per_campaign.merge(cohort_meta, on="campaign_id", how="left")

    # Rank within each (vertical, objective) cohort. pct=True gives [0, 1]
    # where 1 = highest ROAS. NaNs land at 0.5 (median) — defensive.
    per_campaign["rank_pct"] = (
        per_campaign.groupby(["vertical", "objective"])["roas"]
        .rank(pct=True)
        .fillna(0.5)
    )

    return {
        int(r["campaign_id"]): float(r["rank_pct"])
        for _, r in per_campaign.iterrows()
    }
