"""Windowed metric recomputation over the daily fact table.

When the user picks a custom date range, we cannot reuse precomputed
``creative_summary`` (which is lifetime) or ``perf_score`` (which is a
synthetic per-creative label that doesn't decompose into daily rows).
Everything has to be re-rolled from ``store.daily``.

Health in windowed mode is **redefined** as a cohort-relative composite:

  base = (ctr_pctile + cvr_pctile) / 2          # in (vertical, format)
  trajectory = clamp(0.30, 1.0, 1.0 + slope_norm)
  health = round(base * trajectory * 100)

where ``slope_norm`` is the linear-fit slope of daily CTR over the window
divided by the window-mean CTR. So a creative whose CTR is decaying gets a
trajectory penalty even if it sits at a high cohort percentile.

Tab membership in windowed mode is driven by the **status_band** (derived
from windowed health), not the dataset's lifetime ``creative_status`` —
the lifetime label can't speak to a window it didn't see.
"""

from __future__ import annotations

import logging
from datetime import date as date_cls
from typing import Any

import numpy as np
import pandas as pd

from ..datastore import Datastore, _band_from_health

log = logging.getLogger(__name__)


# Cache by (start, end) — the dataset is static so a window's metrics never
# change once computed. Bounded by the number of distinct (start, end) pairs
# the user picks during a session, so memory is fine.
_cache: dict[tuple[str, str], dict[str, Any]] = {}


def reset_cache() -> None:
    _cache.clear()


_camp_to_adv_cache: dict[int, int] | None = None


def _advertiser_id_for_campaign(store: Datastore, campaign_id: int) -> int:
    global _camp_to_adv_cache
    if _camp_to_adv_cache is None:
        _camp_to_adv_cache = (
            store.campaigns.set_index("campaign_id")["advertiser_id"]
            .astype(int)
            .to_dict()
        )
    return int(_camp_to_adv_cache.get(campaign_id, -1))


def is_full_range(store: Datastore, start: str | None, end: str | None) -> bool:
    """The chip "All time" / no params should bypass windowing entirely so
    the cockpit reuses the precomputed lifetime metrics. This returns True
    when (start, end) covers the dataset bounds (or is missing).
    """
    if start is None and end is None:
        return True
    full_start, full_end = dataset_bounds(store)
    s = start or full_start
    e = end or full_end
    return s <= full_start and e >= full_end


def dataset_bounds(store: Datastore) -> tuple[str, str]:
    if store.daily.empty:
        return ("2026-01-01", "2026-03-16")
    dmin = store.daily["date"].min()
    dmax = store.daily["date"].max()
    return (
        dmin.strftime("%Y-%m-%d") if hasattr(dmin, "strftime") else str(dmin),
        dmax.strftime("%Y-%m-%d") if hasattr(dmax, "strftime") else str(dmax),
    )


def parse_date(v: str | None, fallback: str) -> str:
    """Tolerant ISO-date normaliser. Returns fallback on bad input."""
    if not v:
        return fallback
    try:
        return date_cls.fromisoformat(v).strftime("%Y-%m-%d")
    except ValueError:
        return fallback


def normalize_window(
    store: Datastore, start: str | None, end: str | None
) -> tuple[str, str]:
    """Clamp a (start, end) request to the dataset bounds. Swap if reversed."""
    full_start, full_end = dataset_bounds(store)
    s = parse_date(start, full_start)
    e = parse_date(end, full_end)
    if s < full_start:
        s = full_start
    if e > full_end:
        e = full_end
    if s > e:
        s, e = e, s
    return s, e


def compute_window(
    store: Datastore, start: str, end: str
) -> dict[str, Any]:
    """Roll every metric inside the half-open-but-inclusive window [start, end].
    Returns a dict with:
      - ``rows_by_cid``: flat-row payloads keyed by creative_id (same shape
        as ``store.flat_row_by_creative``)
      - ``kpis``: portfolio KPIs over the window
      - ``tab_counts``: counts by status_band (windowed bands drive tabs in
        windowed mode)
      - ``window``: {start, end, days}
    """
    key = (start, end)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    # Filter daily rows to the window. Pandas date comparisons on Timestamp
    # vs string work because pandas coerces.
    df = store.daily
    mask = (df["date"] >= start) & (df["date"] <= end)
    win = df.loc[mask]

    # Per-creative rollup over the window.
    grouped = win.groupby("creative_id", as_index=False).agg(
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        conversions=("conversions", "sum"),
        spend_usd=("spend_usd", "sum"),
        revenue_usd=("revenue_usd", "sum"),
        days_active=("date", "nunique"),
    )

    # Cohort-relative percentiles (vertical, format) for CTR and CVR.
    # Pull the cohort keys + headline + asset_file from creative metadata.
    meta = store.creatives.set_index("creative_id")
    detail_lookup = store.creative_detail

    # Compute CTR/CVR/ROAS once.
    grouped["ctr"] = np.where(
        grouped["impressions"] > 0,
        grouped["clicks"] / grouped["impressions"],
        0.0,
    )
    grouped["cvr"] = np.where(
        grouped["clicks"] > 0,
        grouped["conversions"] / grouped["clicks"],
        0.0,
    )
    grouped["roas"] = np.where(
        grouped["spend_usd"] > 0,
        grouped["revenue_usd"] / grouped["spend_usd"],
        0.0,
    )

    # Attach cohort keys.
    grouped["vertical"] = grouped["creative_id"].map(meta["vertical"])
    grouped["format"] = grouped["creative_id"].map(meta["format"])

    # Cohort percentiles.
    grouped["ctr_pct"] = grouped.groupby(["vertical", "format"])["ctr"].rank(
        pct=True
    )
    grouped["cvr_pct"] = grouped.groupby(["vertical", "format"])["cvr"].rank(
        pct=True
    )
    grouped["ctr_pct"] = grouped["ctr_pct"].fillna(0.0)
    grouped["cvr_pct"] = grouped["cvr_pct"].fillna(0.0)

    # Per-creative trajectory: linear fit slope over the windowed daily CTR
    # series, normalised by mean CTR. Negative → penalty. Skip creatives with
    # < 3 days in the window (slope is unstable).
    per_day = (
        win.groupby(["creative_id", "date"], as_index=False).agg(
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
        )
    )
    trajectory_by_cid: dict[int, float] = {}
    sparkline_by_cid: dict[int, list[float]] = {}
    for cid_raw, g in per_day.groupby("creative_id", sort=False):
        cid = int(cid_raw)
        g = g.sort_values("date")
        ctr_series = np.where(
            g["impressions"].to_numpy() > 0,
            g["clicks"].to_numpy() / np.maximum(g["impressions"].to_numpy(), 1),
            0.0,
        )
        n = len(ctr_series)
        if n >= 3 and ctr_series.mean() > 0:
            x = np.arange(n, dtype=float)
            # numpy polyfit returns [slope, intercept]
            slope, _ = np.polyfit(x, ctr_series, 1)
            slope_norm = float(slope * n / (ctr_series.mean() + 1e-9))
            # slope_norm is "fractional change across the whole window".
            # -0.5 means CTR halved end-to-end → strong penalty.
            trajectory_by_cid[cid] = max(
                0.30, min(1.0, 1.0 + min(0.0, slope_norm))
            )
        else:
            trajectory_by_cid[cid] = 1.0
        # Sparkline: tail 30 days for the row payload.
        tail = ctr_series[-30:].tolist()
        sparkline_by_cid[cid] = [round(float(v), 6) for v in tail]

    rows_by_cid: dict[int, dict[str, Any]] = {}

    # Build flat rows. We iterate over all creatives in metadata; creatives
    # with no daily rows in the window get a zeroed row with health = 0.
    all_cids = meta.index.astype(int).tolist()
    grouped_indexed = grouped.set_index("creative_id")

    for cid in all_cids:
        meta_row = meta.loc[cid]
        if cid in grouped_indexed.index:
            r = grouped_indexed.loc[cid]
            ctr = float(r["ctr"])
            cvr = float(r["cvr"])
            roas = float(r["roas"])
            spend = float(r["spend_usd"])
            revenue = float(r["revenue_usd"])
            impressions = int(r["impressions"])
            clicks = int(r["clicks"])
            conversions = int(r["conversions"])
            days_active = int(r["days_active"])
            ctr_pct = float(r["ctr_pct"])
            cvr_pct = float(r["cvr_pct"])
            # Stretch the cohort percentile so the distribution doesn't
            # cluster around 0.5 (every percentile-based score does). x^0.7
            # bends the curve up so a median creative lands in Watch (~60),
            # genuine winners reach Scale, and only the bottom decile hits
            # Cut.
            base = ((ctr_pct + cvr_pct) / 2.0) ** 0.7
            trajectory = trajectory_by_cid.get(cid, 1.0)
            health = max(0, min(100, int(round(base * trajectory * 100))))
            sparkline = sparkline_by_cid.get(cid, [])
        else:
            ctr = cvr = roas = spend = revenue = 0.0
            impressions = clicks = conversions = days_active = 0
            health = 0
            sparkline = []

        # Pull the lifetime fatigue_day so the FatigueChart annotation still
        # works. status (the lifetime label) is shown alongside as validation.
        detail = detail_lookup.get(cid, {})
        fatigue_day = detail.get("fatigue_day")
        try:
            fatigue_day_v = (
                int(fatigue_day) if fatigue_day is not None and not pd.isna(fatigue_day) else None
            )
        except (TypeError, ValueError):
            fatigue_day_v = None

        rows_by_cid[cid] = {
            "creative_id": cid,
            "campaign_id": int(meta_row["campaign_id"]),
            "advertiser_id": _advertiser_id_for_campaign(store, int(meta_row["campaign_id"])),
            "advertiser_name": meta_row["advertiser_name"],
            "headline": meta_row.get("headline") or "",
            "vertical": meta_row["vertical"],
            "format": meta_row["format"],
            "status": detail.get("creative_status"),
            "status_band": _band_from_health(health),
            "ctr": ctr,
            "cvr": cvr,
            "roas": roas,
            "spend_usd": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "revenue_usd": revenue,
            "days_active": days_active,
            "health": health,
            "sparkline": sparkline,
            "fatigue_day": fatigue_day_v,
            "asset_file": meta_row["asset_file"],
        }

    # Portfolio KPIs over the window.
    total_impressions = int(grouped["impressions"].sum())
    total_clicks = int(grouped["clicks"].sum())
    total_conversions = int(grouped["conversions"].sum())
    total_spend = float(grouped["spend_usd"].sum())
    total_revenue = float(grouped["revenue_usd"].sum())
    # "Need attention" in windowed mode: rescue + cut bands.
    attention = sum(
        1
        for r in rows_by_cid.values()
        if r["status_band"] in ("rescue", "cut")
    )
    # Daily aggregates over the window for the KPI sparklines.
    daily_agg = (
        win.groupby("date", as_index=False)
        .agg(
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
            conversions=("conversions", "sum"),
            spend_usd=("spend_usd", "sum"),
            revenue_usd=("revenue_usd", "sum"),
        )
        .sort_values("date")
    )
    spend_series = [float(v) for v in daily_agg["spend_usd"].tolist()]
    ctr_series = [
        (float(c) / float(i)) if i else 0.0
        for c, i in zip(daily_agg["clicks"], daily_agg["impressions"])
    ]
    cvr_series = [
        (float(c) / float(k)) if k else 0.0
        for c, k in zip(daily_agg["conversions"], daily_agg["clicks"])
    ]
    roas_series = [
        (float(r) / float(s)) if s else 0.0
        for r, s in zip(daily_agg["revenue_usd"], daily_agg["spend_usd"])
    ]

    kpis = {
        "total_spend_usd": total_spend,
        "total_revenue_usd": total_revenue,
        "roas": (total_revenue / total_spend) if total_spend else 0.0,
        "ctr": (total_clicks / total_impressions) if total_impressions else 0.0,
        "cvr": (total_conversions / total_clicks) if total_clicks else 0.0,
        "attention_count": attention,
        "spend_series": spend_series,
        "ctr_series": ctr_series,
        "cvr_series": cvr_series,
        "roas_series": roas_series,
    }

    # Tab counts by band (windowed mode).
    band_counts: dict[str, int] = {"scale": 0, "watch": 0, "rescue": 0, "cut": 0}
    for r in rows_by_cid.values():
        b = r["status_band"]
        if b in band_counts:
            band_counts[b] += 1
    tab_counts = {
        **band_counts,
        "explore": len(rows_by_cid),
    }

    days = (date_cls.fromisoformat(end) - date_cls.fromisoformat(start)).days + 1

    out = {
        "rows_by_cid": rows_by_cid,
        "kpis": kpis,
        "tab_counts": tab_counts,
        "window": {"start": start, "end": end, "days": days},
    }
    _cache[key] = out
    return out
