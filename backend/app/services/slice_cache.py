"""Per-(creative, country, OS, day) slice cache for the advisor.

The production fatigue endpoint collapses the slice grain in
``datastore.py``'s startup ``per_day`` aggregation. The advisor needs that
detail back: a daily series per ``(creative_id, country, os)`` so it can
emit recommendations like "pause in BR" or "cut iOS bid" at the slice the
marketer actually controls.

Computed once at startup. Exposes four artefacts on the Datastore:

- ``slice_timeseries``     — list of daily rollups per slice key
- ``slice_features``       — 7 fatigue features + slice-shape features per slice
- ``cohort_baselines_by_country`` — (vertical, format, country) → first-7d
  median + last-7d 25th-percentile CTR, with fallback to (vertical, format)
- ``marginal_roas_by_slice`` — (alpha, beta, marginal_roas_at_current_spend)
  fit by log-log OLS on the trailing 14d (spend, revenue) curve

Sparse-slice handling, per ``data_findings.md``:

- A slice must have ≥ 14 active days AND ≥ 5,000 cumulative impressions to
  produce features. Below that, the changepoint search is unstable and the
  CTR is too noisy to recommend on.
- Cohort cells with < 5 creatives fall back to the parent (vertical,
  format) cohort. Logged as a warning.
- Slices with zero spend or zero revenue across the trailing 14 days skip
  the marginal-ROAS fit; the reallocation rule treats them as
  unrecommendable rather than fitting a meaningless curve.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from .fatigue import _changepoint_lr

log = logging.getLogger(__name__)


# Minimum days/impressions a slice needs before it's eligible for features.
SLICE_MIN_DAYS = 14
SLICE_MIN_IMPRESSIONS = 5_000

# Marginal-ROAS curve fit window.
MARGINAL_ROAS_WINDOW_DAYS = 14
MARGINAL_ROAS_MIN_POINTS = 5

# Cohort sample-size floor before falling back to the parent cohort.
COHORT_MIN_CREATIVES = 5


SliceKey = tuple[int, str, str]  # (creative_id, country, os)
CountryCohortKey = tuple[str, str, str]  # (vertical, format, country)
ParentCohortKey = tuple[str, str]  # (vertical, format)


# ────────────────────────────────────────────────────────────────────
# 1. Slice-grain daily timeseries.
# ────────────────────────────────────────────────────────────────────


def compute_slice_timeseries(
    daily: pd.DataFrame,
) -> dict[SliceKey, list[dict[str, Any]]]:
    """Group ``daily`` by (creative_id, country, os, date) and return a
    dict keyed by slice → list of daily rollups, sorted by date ascending.
    Slices that fail the activity floor are dropped.
    """
    if daily.empty:
        return {}

    g = (
        daily.groupby(
            ["creative_id", "country", "os", "date"], as_index=False
        )
        .agg(
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
            conversions=("conversions", "sum"),
            spend_usd=("spend_usd", "sum"),
            revenue_usd=("revenue_usd", "sum"),
        )
        .sort_values(["creative_id", "country", "os", "date"])
    )
    # Format date once for JSON.
    g["date"] = pd.to_datetime(g["date"]).dt.strftime("%Y-%m-%d")

    out: dict[SliceKey, list[dict[str, Any]]] = {}
    dropped = 0
    for (cid, country, os_), group in g.groupby(
        ["creative_id", "country", "os"], sort=False
    ):
        if len(group) < SLICE_MIN_DAYS:
            dropped += 1
            continue
        if int(group["impressions"].sum()) < SLICE_MIN_IMPRESSIONS:
            dropped += 1
            continue
        out[(int(cid), str(country), str(os_))] = group.drop(
            columns=["creative_id", "country", "os"]
        ).to_dict("records")

    log.info(
        "slice_timeseries: %d slices kept, %d dropped (sparse)",
        len(out),
        dropped,
    )
    return out


# ────────────────────────────────────────────────────────────────────
# 2. Country-aware cohort baselines.
# ────────────────────────────────────────────────────────────────────


def compute_country_cohort_baselines(
    slice_timeseries: dict[SliceKey, list[dict[str, Any]]],
    creative_meta: dict[int, dict[str, Any]],
) -> tuple[
    dict[CountryCohortKey, dict[str, float]],
    dict[ParentCohortKey, dict[str, float]],
]:
    """Compute first-7d-median and last-7d-p25 CTR baselines at two grains:

    - ``(vertical, format, country)`` — preferred when the cohort has ≥5
      creatives.
    - ``(vertical, format)`` — fallback for sparse country cells (matches
      the production fatigue baselines).

    The advisor's rule layer should look up the country grain first; on
    miss (or if the cohort had < 5 creatives), fall back to the parent.
    """
    country_first: dict[CountryCohortKey, list[float]] = {}
    country_last: dict[CountryCohortKey, list[float]] = {}
    parent_first: dict[ParentCohortKey, list[float]] = {}
    parent_last: dict[ParentCohortKey, list[float]] = {}

    for (cid, country, _os), points in slice_timeseries.items():
        meta = creative_meta.get(int(cid)) or {}
        vertical = meta.get("vertical")
        fmt = meta.get("format")
        if vertical is None or fmt is None:
            continue
        if len(points) < SLICE_MIN_DAYS:
            continue

        n_anchor = min(7, len(points) // 3)
        first = points[:n_anchor]
        last = points[-n_anchor:]
        f_imp = sum((p.get("impressions") or 0) for p in first)
        f_clk = sum((p.get("clicks") or 0) for p in first)
        l_imp = sum((p.get("impressions") or 0) for p in last)
        l_clk = sum((p.get("clicks") or 0) for p in last)

        cc_key = (str(vertical), str(fmt), str(country))
        pp_key = (str(vertical), str(fmt))
        if f_imp > 0:
            country_first.setdefault(cc_key, []).append(f_clk / f_imp)
            parent_first.setdefault(pp_key, []).append(f_clk / f_imp)
        if l_imp > 0:
            country_last.setdefault(cc_key, []).append(l_clk / l_imp)
            parent_last.setdefault(pp_key, []).append(l_clk / l_imp)

    country_baselines: dict[CountryCohortKey, dict[str, float]] = {}
    parent_baselines: dict[ParentCohortKey, dict[str, float]] = {}
    sparse_drops = 0
    for key, vals in country_first.items():
        if len(vals) < COHORT_MIN_CREATIVES:
            sparse_drops += 1
            continue
        last_vals = country_last.get(key, [])
        country_baselines[key] = {
            "first_median": float(np.median(vals)),
            "last_p25": (
                float(np.percentile(last_vals, 25)) if last_vals else 0.0
            ),
            "n": float(len(vals)),
        }
    for key, vals in parent_first.items():
        last_vals = parent_last.get(key, [])
        parent_baselines[key] = {
            "first_median": float(np.median(vals)) if vals else 0.0,
            "last_p25": float(np.percentile(last_vals, 25)) if last_vals else 0.0,
            "n": float(len(vals)),
        }

    log.info(
        "cohort baselines: %d country-grain, %d parent-grain, %d sparse (fell back)",
        len(country_baselines),
        len(parent_baselines),
        sparse_drops,
    )
    return country_baselines, parent_baselines


def lookup_cohort(
    vertical: str,
    fmt: str,
    country: str,
    country_baselines: dict[CountryCohortKey, dict[str, float]],
    parent_baselines: dict[ParentCohortKey, dict[str, float]],
) -> dict[str, float]:
    """Cohort lookup with country → parent fallback. Returns
    ``{"first_median", "last_p25", "n"}``; zeros if neither grain
    matched (rules should treat that as 'no cohort comparison
    possible' and skip)."""
    cc = country_baselines.get((vertical, fmt, country))
    if cc is not None:
        return cc
    pp = parent_baselines.get((vertical, fmt))
    if pp is not None:
        return pp
    return {"first_median": 0.0, "last_p25": 0.0, "n": 0.0}


# ────────────────────────────────────────────────────────────────────
# 3. Per-slice features.
# ────────────────────────────────────────────────────────────────────


def compute_slice_features(
    slice_timeseries: dict[SliceKey, list[dict[str, Any]]],
    creative_meta: dict[int, dict[str, Any]],
    country_baselines: dict[CountryCohortKey, dict[str, float]],
    parent_baselines: dict[ParentCohortKey, dict[str, float]],
) -> dict[SliceKey, dict[str, float]]:
    """For every eligible slice, compute the same seven engineered features
    the production fatigue classifier uses, plus a few slice-specific
    extras (slice spend totals, last-7d daily spend rate). Returns a dict
    keyed by slice → feature dict.
    """
    out: dict[SliceKey, dict[str, float]] = {}
    for key, points in slice_timeseries.items():
        cid, country, _os = key
        meta = creative_meta.get(int(cid)) or {}
        vertical = str(meta.get("vertical") or "")
        fmt = str(meta.get("format") or "")
        cohort = lookup_cohort(
            vertical, fmt, country, country_baselines, parent_baselines
        )

        impr = np.array([p.get("impressions") or 0 for p in points], dtype=float)
        clk = np.array([p.get("clicks") or 0 for p in points], dtype=float)
        rev = np.array([p.get("revenue_usd") or 0.0 for p in points], dtype=float)
        spd = np.array([p.get("spend_usd") or 0.0 for p in points], dtype=float)
        n = len(impr)
        total_imp = float(impr.sum())
        total_clk = float(clk.sum())
        if total_imp <= 0 or total_clk <= 0:
            continue

        n_anchor = min(7, n // 3)
        f_imp = float(impr[:n_anchor].sum())
        f_clk = float(clk[:n_anchor].sum())
        l_imp = float(impr[-n_anchor:].sum())
        l_clk = float(clk[-n_anchor:].sum())
        p_first = float(f_clk / f_imp) if f_imp > 0 else 0.0
        p_last = float(l_clk / l_imp) if l_imp > 0 else 0.0
        drop_ratio = (p_last / p_first) if p_first > 0 else 1.0

        cp = _changepoint_lr(impr, clk)
        if cp is None:
            lr_stat = 0.0
            best_k = float("nan")
            p_pre = p_first
            p_post = p_last
        else:
            best_k_i, lr_stat_f, p_pre_f, p_post_f = cp
            best_k = float(best_k_i)
            lr_stat = float(lr_stat_f)
            p_pre = float(p_pre_f)
            p_post = float(p_post_f)

        daily_ctr = clk / np.maximum(impr, 1.0)
        ctr_mean = float(daily_ctr.mean())
        ctr_std = float(daily_ctr.std())

        # Last-7d slice-level numbers — used by impact estimates and the
        # frequency-cap rule.
        recent = points[-7:]
        recent_spend = float(sum((p.get("spend_usd") or 0.0) for p in recent))
        recent_impr = float(sum((p.get("impressions") or 0) for p in recent))
        recent_clicks = float(sum((p.get("clicks") or 0) for p in recent))
        recent_revenue = float(
            sum((p.get("revenue_usd") or 0.0) for p in recent)
        )
        slice_roas = (
            float(rev.sum()) / float(spd.sum()) if spd.sum() > 0 else 0.0
        )
        recent_roas = (
            recent_revenue / recent_spend if recent_spend > 0 else 0.0
        )
        # Average daily spend over the last 7 days; used as the impact
        # baseline ($/day at risk if we pause this slice).
        daily_spend_recent = recent_spend / max(len(recent), 1)
        # CTR decay defined the way the industry anchors describe it:
        # (first-7d − last-7d) / first-7d, expressed as a positive number
        # when the slice is decaying.
        ctr_decay_pct = (
            (p_first - p_last) / p_first if p_first > 0 else 0.0
        )

        first_vs_cohort = (
            p_first / cohort["first_median"]
            if cohort["first_median"] > 0
            else 1.0
        )
        last_vs_cohort = (
            p_last / cohort["last_p25"] if cohort["last_p25"] > 0 else 1.0
        )

        out[key] = {
            "p_first": p_first,
            "p_last": p_last,
            "drop_ratio": drop_ratio,
            "ctr_decay_pct": ctr_decay_pct,
            "first_vs_cohort": first_vs_cohort,
            "last_vs_cohort": last_vs_cohort,
            "lr_stat": lr_stat,
            "log_total_impr": float(np.log1p(total_imp)),
            "ctr_cv": float(ctr_std / max(ctr_mean, 1e-9)),
            "days_active": float(n),
            "best_k": best_k,
            "p_pre": p_pre,
            "p_post": p_post,
            "total_spend_usd": float(spd.sum()),
            "total_revenue_usd": float(rev.sum()),
            "slice_roas": slice_roas,
            "recent_spend_usd": recent_spend,
            "recent_revenue_usd": recent_revenue,
            "recent_roas": recent_roas,
            "daily_spend_recent": daily_spend_recent,
            "recent_impr": recent_impr,
            "recent_clicks": recent_clicks,
            "cohort_n": cohort["n"],
        }

    log.info("slice_features: computed %d slices", len(out))
    return out


# ────────────────────────────────────────────────────────────────────
# 4. Marginal-ROAS curve fit per slice.
# ────────────────────────────────────────────────────────────────────


def compute_marginal_roas(
    slice_timeseries: dict[SliceKey, list[dict[str, Any]]],
) -> dict[SliceKey, dict[str, float]]:
    """Fit ``revenue ≈ α · spend^β`` on the last 14 days per slice via
    log-log OLS. Returns ``{alpha, beta, marginal_roas_at_current_spend,
    spend_recent_mean}`` per slice. Skipped (key absent) if the trailing
    window has fewer than ``MARGINAL_ROAS_MIN_POINTS`` non-zero points.

    The advisor surfaces the marginal_roas number with the verbatim hedge
    `"Estimated lift based on observed spend-response curve — not an
    experimental result."` per ``data_findings.md``.
    """
    out: dict[SliceKey, dict[str, float]] = {}
    skipped = 0
    for key, points in slice_timeseries.items():
        recent = points[-MARGINAL_ROAS_WINDOW_DAYS:]
        spend = np.array(
            [p.get("spend_usd") or 0.0 for p in recent], dtype=float
        )
        revenue = np.array(
            [p.get("revenue_usd") or 0.0 for p in recent], dtype=float
        )
        # Only valid (>0, >0) days enter the fit; log undefined elsewhere.
        mask = (spend > 0) & (revenue > 0)
        if int(mask.sum()) < MARGINAL_ROAS_MIN_POINTS:
            skipped += 1
            continue
        xs = np.log(spend[mask])
        ys = np.log(revenue[mask])
        # OLS: ys = log(alpha) + beta * xs. Use np.polyfit for stability.
        try:
            beta, log_alpha = np.polyfit(xs, ys, 1)
        except Exception as e:  # noqa: BLE001
            log.warning("marginal_roas fit failed for %s: %s", key, e)
            skipped += 1
            continue
        alpha = float(np.exp(log_alpha))
        beta = float(beta)
        # Marginal ROAS at current spend = derivative of revenue wrt spend.
        # d/dspend [alpha · spend^beta] = alpha · beta · spend^(beta-1).
        spend_recent_mean = float(spend[mask].mean())
        if spend_recent_mean <= 0:
            skipped += 1
            continue
        marginal = alpha * beta * (spend_recent_mean ** (beta - 1.0))
        out[key] = {
            "alpha": alpha,
            "beta": beta,
            "marginal_roas": float(marginal),
            "spend_recent_mean": spend_recent_mean,
            "n_fit_points": float(int(mask.sum())),
        }

    log.info(
        "marginal_roas: fit %d slices, skipped %d (insufficient points)",
        len(out),
        skipped,
    )
    return out


# ────────────────────────────────────────────────────────────────────
# 5. Per-creative geographic-shape rollup (aggregates across slices).
# ────────────────────────────────────────────────────────────────────


def compute_creative_geo_shape(
    slice_features: dict[SliceKey, dict[str, float]],
) -> dict[int, dict[str, Any]]:
    """Roll slice features back up to the creative level: top-country share,
    geographic dispersion, OS divergence. These are the inputs to the
    Concentration Risk and OS Frequency Cap rules.

    Returns ``dict[int, dict[str, Any]]`` because we carry both numeric
    summaries and the ``top_country`` country code string side by side.
    """
    by_creative: dict[int, list[tuple[SliceKey, dict[str, float]]]] = {}
    for key, feats in slice_features.items():
        by_creative.setdefault(int(key[0]), []).append((key, feats))

    out: dict[int, dict[str, Any]] = {}
    for cid, slices in by_creative.items():
        # Total impressions per country (sum across OS).
        country_impr: dict[str, float] = {}
        for (_cid, country, _os), feats in slices:
            country_impr.setdefault(str(country), 0.0)
            country_impr[country] += float(feats.get("recent_impr") or 0.0)
        total = float(sum(country_impr.values()))
        top_country, top_share = "", 0.0
        herfindahl = 0.0
        if total > 0:
            for c, v in country_impr.items():
                share = v / total
                herfindahl += share * share
                if share > top_share:
                    top_share = share
                    top_country = c

        # Geographic CTR dispersion = std of last-7d CTR across served
        # countries (one observation per country, OS-aggregated).
        country_ctr: dict[str, list[float]] = {}
        for (_cid, country, _os), feats in slices:
            recent_impr = feats.get("recent_impr") or 0.0
            recent_clicks = feats.get("recent_clicks") or 0.0
            if recent_impr > 0:
                country_ctr.setdefault(str(country), []).append(
                    recent_clicks / recent_impr
                )
        country_ctr_means = [
            float(np.mean(vs)) for vs in country_ctr.values() if vs
        ]
        country_ctr_dispersion = (
            float(np.std(country_ctr_means)) if len(country_ctr_means) >= 2 else 0.0
        )

        # OS divergence: average Android_drop − iOS_drop across served
        # countries. drop_ratio < 1 = decay (smaller = more decay), so
        # positive divergence flags iOS-first fatigue (the post-ATT
        # industry anchor in data_findings.md).
        ios_drops, android_drops = [], []
        for (_cid, _country, os_), feats in slices:
            dr = feats.get("drop_ratio")
            if dr is None:
                continue
            if os_ == "iOS":
                ios_drops.append(float(dr))
            elif os_ == "Android":
                android_drops.append(float(dr))
        os_drop_divergence = 0.0
        if ios_drops and android_drops:
            os_drop_divergence = float(
                np.mean(android_drops) - np.mean(ios_drops)
            )

        out[int(cid)] = {
            "n_active_countries": float(len(country_impr)),
            "top_country": top_country,
            "top_country_share": top_share,
            "concentration_herfindahl": herfindahl,
            "country_ctr_dispersion": country_ctr_dispersion,
            "os_drop_divergence": os_drop_divergence,
            "country_impressions": country_impr,
        }

    log.info("creative_geo_shape: rolled up %d creatives", len(out))
    return out
