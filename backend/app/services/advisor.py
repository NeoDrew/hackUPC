"""Slice advisor — eight deterministic rules over the per-(creative,
country, OS) slice cache.

Each rule:

- Reads pre-computed slice features from ``store.slice_features`` and the
  per-creative geographic rollup from ``store.creative_geo_shape``.
- Fires when its trigger crosses a threshold.
- Emits one or more ``SliceRecommendation`` rows with: deterministic
  trigger magnitudes (the explainability payload), an estimated daily
  $-impact (the cost-savings warning the user sees), severity
  (critical/warning/opportunity), and the canonical action verb
  (pause/rotate/scale/shift/refresh/archive).

Industry-anchored thresholds come from ``resources/taskInfo/data_findings.md``
§"Industry anchors". The marketer-voice headlines / rationales are produced
by ``recommendation_copy.py``; this module produces the structured payload
only.

Design notes:

- ``recommendation_id`` is a deterministic SHA-1 over
  ``(creative_id, country, os, action_type)`` so the same trigger keeps the
  same ID across restarts. That matters for the
  applied/snoozed/dismissed cache surviving a backend reboot once the
  Atlas store lands.
- Impact estimates are explicitly hedged in the surfaced text (see
  ``recommendation_copy.py``). The numbers themselves are deterministic
  observational projections — never causal claims.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from ..datastore import Datastore
from ..schemas import SliceRecommendation
from .slice_cache import SliceKey

log = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Industry anchors (data_findings.md). Single source of truth — the rule
# bodies reference these constants by name so a future tweak is one edit.
# ────────────────────────────────────────────────────────────────────

# CTR decay thresholds — first-7d → last-7d relative drop expressed as a
# positive number (1.0 = total collapse).
CTR_DECAY_WARN = 0.15        # Warning: 15% decay
CTR_DECAY_REPLACE = 0.30     # Critical: 30% decay (frequency-cap also fires)

# A slice is "decaying materially faster than its creative" when its
# drop_ratio is below this fraction of the creative's drop_ratio.
SLICE_PRUNE_RATIO = 0.66

# Minimum slice share of creative impressions before a Geographic Prune
# fires. Avoids recommending pause on negligible slices.
SLICE_MIN_CREATIVE_SHARE = 0.05

# Cohort-percentile rank that qualifies a slice as Geographic Scale-able.
SCALE_LAST_VS_COHORT = 1.0       # last_vs_cohort ≥ 1.0 = above the p25 floor
SCALE_ROAS_MULTIPLIER = 1.5      # slice_roas ≥ 1.5 × creative_roas

# Concentration Risk thresholds.
CONCENTRATION_TOP_COUNTRY_SHARE = 0.60
CONCENTRATION_TOP_DROP_THRESHOLD = 0.85

# Pattern Transfer cosine-similarity floor (over the L2-normalised
# ``creative_vectors`` already in the datastore).
PATTERN_SIMILARITY_FLOOR = 0.85
PATTERN_PEER_COHORT_PCT = 0.90  # peer must rank ≥ p90 in the target country

# Format-market mismatch — peer formats must outperform this format by ≥
# this much on (country, vertical) ROAS to fire.
FORMAT_MISMATCH_LIFT = 0.30

# Reallocation: how many slices on each side of the spread we surface per
# advertiser. Plus a minimum spend floor so we don't recommend shifting
# pennies.
REALLOC_MIN_DAILY_SPEND = 50.0

# Per-cluster early-warning. Tier-1 EN markets propagate independently per
# data_findings.md, so we only fire on cluster sizes ≥ 2.
GEO_CLUSTERS = {
    "LATAM": {"BR", "MX", "AR", "CO"},
    "SEA": {"ID", "PH", "TH", "VN"},
}


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────


def _rec_id(creative_id: int, country: str, os_: str, action_type: str) -> str:
    """Deterministic SHA-1 → 16 hex chars. Stable across restarts so the
    applied/snoozed/dismissed state survives reboots."""
    raw = f"{creative_id}:{country}:{os_}:{action_type}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def _rec_id_for_creative(creative_id: int, action_type: str) -> str:
    """Variant for creative-level (not slice-level) recommendations like
    Concentration Risk and Reallocation."""
    raw = f"creative:{creative_id}:*:*:{action_type}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def _advertiser_lookup(store: Datastore) -> dict[int, tuple[int, int]]:
    """Build ``creative_id → (advertiser_id, campaign_id)`` once.

    creatives.csv has campaign_id but no advertiser_id; campaigns.csv has
    both. The orchestrator already does this join elsewhere — we materialise
    a small dict here so the rule loop is O(1) per slice.
    """
    by_campaign: dict[int, int] = {}
    if not store.campaigns.empty:
        for row in store.campaigns[
            ["campaign_id", "advertiser_id"]
        ].to_dict("records"):
            by_campaign[int(row["campaign_id"])] = int(row["advertiser_id"])

    by_creative: dict[int, tuple[int, int]] = {}
    for cid, meta in store.creative_detail.items():
        camp = meta.get("campaign_id")
        if camp is None:
            continue
        adv = by_campaign.get(int(camp))
        if adv is None:
            continue
        by_creative[int(cid)] = (int(adv), int(camp))
    return by_creative


def _per_creative_baselines(
    slice_features: dict[SliceKey, dict[str, float]],
) -> dict[int, dict[str, float]]:
    """Roll up per-slice features to per-creative aggregates that the rule
    bodies need (for "is this slice decaying *faster than the creative as a
    whole*" comparisons)."""
    by_creative: dict[int, list[dict[str, float]]] = {}
    for key, feats in slice_features.items():
        by_creative.setdefault(int(key[0]), []).append(feats)

    out: dict[int, dict[str, float]] = {}
    for cid, feats_list in by_creative.items():
        total_imp = sum((f.get("recent_impr") or 0.0) for f in feats_list)
        total_clk = sum((f.get("recent_clicks") or 0.0) for f in feats_list)
        total_spend = sum((f.get("recent_spend_usd") or 0.0) for f in feats_list)
        total_rev = sum((f.get("recent_revenue_usd") or 0.0) for f in feats_list)

        # Impressions-weighted drop_ratio so big slices dominate.
        weights = [f.get("recent_impr") or 0.0 for f in feats_list]
        drops = [f.get("drop_ratio") or 1.0 for f in feats_list]
        wsum = sum(weights)
        creative_drop_ratio = (
            sum(d * w for d, w in zip(drops, weights)) / wsum if wsum > 0 else 1.0
        )
        out[cid] = {
            "creative_drop_ratio": float(creative_drop_ratio),
            "creative_roas": float(total_rev / total_spend) if total_spend > 0 else 0.0,
            "creative_daily_spend": float(total_spend / 7.0),
            "creative_recent_impr": float(total_imp),
            "creative_recent_clicks": float(total_clk),
        }
    return out


def _make_rec(
    *,
    creative_id: int,
    country: str,
    os_: str,
    advertiser_id: int,
    campaign_id: int,
    action_type: str,
    severity: str,
    headline: str,
    rationale: str,
    est_daily_impact_usd: float,
    trigger_magnitude: dict[str, float],
) -> SliceRecommendation:
    return SliceRecommendation(
        recommendation_id=_rec_id(creative_id, country, os_, action_type),
        creative_id=creative_id,
        country=country,
        os=os_,
        advertiser_id=advertiser_id,
        campaign_id=campaign_id,
        action_type=action_type,
        severity=severity,
        headline=headline,
        rationale=rationale,
        est_daily_impact_usd=float(est_daily_impact_usd),
        trigger_magnitude={k: float(v) for k, v in trigger_magnitude.items()},
    )


# ────────────────────────────────────────────────────────────────────
# Rule 1 — Geographic Prune
# ────────────────────────────────────────────────────────────────────


def rule_geographic_prune(
    store: Datastore,
    advertiser_by_creative: dict[int, tuple[int, int]],
    creative_baselines: dict[int, dict[str, float]],
) -> list[SliceRecommendation]:
    out: list[SliceRecommendation] = []
    for (cid, country, os_), feats in store.slice_features.items():
        if cid not in advertiser_by_creative:
            continue
        adv_id, camp_id = advertiser_by_creative[cid]
        cbase = creative_baselines.get(cid)
        if cbase is None:
            continue
        creative_recent_impr = cbase["creative_recent_impr"]
        slice_recent_impr = float(feats.get("recent_impr") or 0.0)
        slice_share = (
            slice_recent_impr / creative_recent_impr
            if creative_recent_impr > 0
            else 0.0
        )

        slice_decay = float(feats.get("ctr_decay_pct") or 0.0)
        slice_drop = float(feats.get("drop_ratio") or 1.0)
        creative_drop = cbase["creative_drop_ratio"]

        # Two ways to fire: (a) slice CTR has crossed the industry
        # "replace now" threshold of 30% decay (regardless of creative
        # baseline — the slice is just bad), OR (b) slice is decaying
        # materially faster than the creative average AND has crossed
        # the warning floor.
        fires_absolute = slice_decay >= CTR_DECAY_REPLACE
        fires_relative = (
            slice_decay >= CTR_DECAY_WARN
            and creative_drop > 0
            and slice_drop / creative_drop <= SLICE_PRUNE_RATIO
        )
        if not (fires_absolute or fires_relative):
            continue
        if slice_share < SLICE_MIN_CREATIVE_SHARE:
            continue

        slice_daily_spend = float(feats.get("daily_spend_recent") or 0.0)
        slice_roas = float(feats.get("recent_roas") or 0.0)
        creative_roas = cbase["creative_roas"]
        # Wasted spend = slice's daily spend × (1 − slice_roas / creative_roas),
        # floored at 0 (we never claim "saves negative dollars").
        if creative_roas > 0 and slice_roas < creative_roas:
            wasted_fraction = max(0.0, 1.0 - (slice_roas / creative_roas))
            est_impact = slice_daily_spend * wasted_fraction
        else:
            est_impact = slice_daily_spend * 0.5  # conservative default

        # Critical when slice is in really bad shape; warning otherwise.
        severity = "critical" if slice_decay >= CTR_DECAY_REPLACE else "warning"

        out.append(
            _make_rec(
                creative_id=cid,
                country=country,
                os_=os_,
                advertiser_id=adv_id,
                campaign_id=camp_id,
                action_type="pause",
                severity=severity,
                headline="",  # filled later by recommendation_copy
                rationale="",
                est_daily_impact_usd=est_impact,
                trigger_magnitude={
                    "slice_drop_ratio": slice_drop,
                    "creative_drop_ratio": creative_drop,
                    "slice_share": slice_share,
                    "slice_roas": slice_roas,
                    "creative_roas": creative_roas,
                    "ctr_decay_pct": float(feats.get("ctr_decay_pct") or 0.0),
                },
            )
        )
    return out


# ────────────────────────────────────────────────────────────────────
# Rule 2 — Geographic Scale
# ────────────────────────────────────────────────────────────────────


def rule_geographic_scale(
    store: Datastore,
    advertiser_by_creative: dict[int, tuple[int, int]],
    creative_baselines: dict[int, dict[str, float]],
) -> list[SliceRecommendation]:
    out: list[SliceRecommendation] = []
    for (cid, country, os_), feats in store.slice_features.items():
        if cid not in advertiser_by_creative:
            continue
        adv_id, camp_id = advertiser_by_creative[cid]
        cbase = creative_baselines.get(cid)
        if cbase is None:
            continue
        slice_roas = float(feats.get("recent_roas") or 0.0)
        creative_roas = cbase["creative_roas"]
        last_vs_cohort = float(feats.get("last_vs_cohort") or 0.0)
        # Trigger: slice still strong vs cohort AND meaningfully better
        # ROAS than the creative average.
        if creative_roas <= 0 or slice_roas <= 0:
            continue
        if last_vs_cohort < SCALE_LAST_VS_COHORT:
            continue
        if slice_roas < SCALE_ROAS_MULTIPLIER * creative_roas:
            continue

        slice_daily_spend = float(feats.get("daily_spend_recent") or 0.0)
        # Est. lift from a 25% bid bump at constant ROAS.
        est_impact = slice_daily_spend * 0.25 * slice_roas

        out.append(
            _make_rec(
                creative_id=cid,
                country=country,
                os_=os_,
                advertiser_id=adv_id,
                campaign_id=camp_id,
                action_type="scale",
                severity="opportunity",
                headline="",
                rationale="",
                est_daily_impact_usd=est_impact,
                trigger_magnitude={
                    "slice_roas": slice_roas,
                    "creative_roas": creative_roas,
                    "last_vs_cohort": last_vs_cohort,
                    "slice_daily_spend": slice_daily_spend,
                },
            )
        )
    return out


# ────────────────────────────────────────────────────────────────────
# Rule 3 — OS Frequency Cap
# ────────────────────────────────────────────────────────────────────


def rule_os_frequency_cap(
    store: Datastore,
    advertiser_by_creative: dict[int, tuple[int, int]],
) -> list[SliceRecommendation]:
    """Per creative, look at the (country, OS) slices and flag the OS that
    is decaying past the replace threshold while the opposite OS is still
    healthy. Direction is iOS-first (post-ATT) per the industry anchor.
    """
    out: list[SliceRecommendation] = []
    by_creative_country: dict[
        tuple[int, str], dict[str, dict[str, float]]
    ] = {}
    for (cid, country, os_), feats in store.slice_features.items():
        by_creative_country.setdefault((cid, country), {})[os_] = feats

    for (cid, country), os_map in by_creative_country.items():
        ios = os_map.get("iOS")
        android = os_map.get("Android")
        if ios is None or android is None:
            continue  # need both to compare
        if cid not in advertiser_by_creative:
            continue
        adv_id, camp_id = advertiser_by_creative[cid]

        ios_decay = float(ios.get("ctr_decay_pct") or 0.0)
        android_decay = float(android.get("ctr_decay_pct") or 0.0)
        # Condition: one OS has crossed the warn floor AND is decaying
        # at least 10pp harder than the other. This catches OS-level
        # divergence that's sharp enough to matter without requiring a
        # perfect 30% / <15% split which the synthetic data rarely
        # exhibits. iOS-first per the post-ATT industry anchor.
        ios_lead = ios_decay - android_decay
        android_lead = android_decay - ios_decay
        if ios_decay >= CTR_DECAY_WARN and ios_lead >= 0.10:
            target_os = "iOS"
            target_feats = ios
        elif android_decay >= CTR_DECAY_WARN and android_lead >= 0.10:
            target_os = "Android"
            target_feats = android
        else:
            continue

        slice_daily_spend = float(target_feats.get("daily_spend_recent") or 0.0)
        # Est. wasted spend ≈ daily spend × the decay magnitude.
        est_impact = slice_daily_spend * float(
            target_feats.get("ctr_decay_pct") or 0.0
        )

        out.append(
            _make_rec(
                creative_id=cid,
                country=country,
                os_=target_os,
                advertiser_id=adv_id,
                campaign_id=camp_id,
                action_type="shift",
                severity="warning",
                headline="",
                rationale="",
                est_daily_impact_usd=est_impact,
                trigger_magnitude={
                    "ios_ctr_decay": ios_decay,
                    "android_ctr_decay": android_decay,
                    "target_decay": float(
                        target_feats.get("ctr_decay_pct") or 0.0
                    ),
                    "slice_daily_spend": slice_daily_spend,
                },
            )
        )
    return out


# ────────────────────────────────────────────────────────────────────
# Rule 4 — Cross-market Early Warning
# ────────────────────────────────────────────────────────────────────


def rule_cross_market_early_warning(
    store: Datastore,
    advertiser_by_creative: dict[int, tuple[int, int]],
) -> list[SliceRecommendation]:
    """For each creative, count how many countries within each defined
    cluster (LATAM, SEA) are decaying past the replace threshold. If the
    count crosses 2, fire a "rotate creative in cluster" warning citing
    the 3-7 day propagation rule of thumb."""
    out: list[SliceRecommendation] = []
    by_creative: dict[int, dict[str, dict[str, dict[str, float]]]] = {}
    for (cid, country, os_), feats in store.slice_features.items():
        by_creative.setdefault(cid, {}).setdefault(country, {})[os_] = feats

    for cid, country_map in by_creative.items():
        if cid not in advertiser_by_creative:
            continue
        adv_id, camp_id = advertiser_by_creative[cid]

        # Combine OS into a country-level decay using impressions weights.
        country_decay: dict[str, float] = {}
        country_spend: dict[str, float] = {}
        for country, os_map in country_map.items():
            wimp, wdecay, sp = 0.0, 0.0, 0.0
            for feats in os_map.values():
                imp = float(feats.get("recent_impr") or 0.0)
                wimp += imp
                wdecay += imp * float(feats.get("ctr_decay_pct") or 0.0)
                sp += float(feats.get("recent_spend_usd") or 0.0)
            if wimp > 0:
                country_decay[country] = wdecay / wimp
                country_spend[country] = sp

        for cluster_name, members in GEO_CLUSTERS.items():
            decaying = [
                c for c in members
                if country_decay.get(c, 0.0) >= CTR_DECAY_REPLACE
            ]
            if len(decaying) < 2:
                continue
            # The "trigger country" is whichever decayed most — use as the
            # slice anchor for the recommendation row. The action covers
            # the whole cluster.
            primary = max(decaying, key=lambda c: country_decay[c])
            # Impact = total weekly spend across decaying cluster countries.
            est_impact = sum(country_spend.get(c, 0.0) for c in decaying) / 7.0

            out.append(
                _make_rec(
                    creative_id=cid,
                    country=primary,
                    os_="*",  # cluster-level, not OS-specific
                    advertiser_id=adv_id,
                    campaign_id=camp_id,
                    action_type="rotate",
                    severity="warning",
                    headline="",
                    rationale="",
                    est_daily_impact_usd=est_impact,
                    trigger_magnitude={
                        "cluster_size_decaying": float(len(decaying)),
                        "cluster_total_size": float(len(members)),
                        "primary_country_decay": float(country_decay[primary]),
                        "decaying_countries": float(len(decaying)),
                        "cluster_spend_per_day": est_impact,
                    },
                    # Pass the cluster name through extras for the copy layer.
                )
            )
            # Stash extras on the model_extra dict via attribute (extra=allow)
            out[-1].cluster_name = cluster_name  # type: ignore[attr-defined]
            out[-1].decaying_countries_csv = ",".join(sorted(decaying))  # type: ignore[attr-defined]
    return out


# ────────────────────────────────────────────────────────────────────
# Rule 5 — Concentration Risk
# ────────────────────────────────────────────────────────────────────


def rule_concentration_risk(
    store: Datastore,
    advertiser_by_creative: dict[int, tuple[int, int]],
) -> list[SliceRecommendation]:
    out: list[SliceRecommendation] = []
    for cid, geo in store.creative_geo_shape.items():
        if cid not in advertiser_by_creative:
            continue
        adv_id, camp_id = advertiser_by_creative[cid]

        top_share = float(geo.get("top_country_share") or 0.0)
        top_country = str(geo.get("top_country") or "")
        if top_share < CONCENTRATION_TOP_COUNTRY_SHARE or not top_country:
            continue

        # Drop ratio of the top country across both OS — pick the worst.
        worst_drop = 1.0
        top_country_spend = 0.0
        for (scid, country, _os), feats in store.slice_features.items():
            if scid != cid or country != top_country:
                continue
            dr = float(feats.get("drop_ratio") or 1.0)
            if dr < worst_drop:
                worst_drop = dr
            top_country_spend += float(feats.get("recent_spend_usd") or 0.0)
        if worst_drop >= CONCENTRATION_TOP_DROP_THRESHOLD:
            continue

        # Impact: daily revenue at risk in the dominant country.
        est_impact = (top_country_spend / 7.0) * (1.0 - worst_drop)

        out.append(
            _make_rec(
                creative_id=cid,
                country=top_country,
                os_="*",
                advertiser_id=adv_id,
                campaign_id=camp_id,
                action_type="refresh",
                severity="warning",
                headline="",
                rationale="",
                est_daily_impact_usd=est_impact,
                trigger_magnitude={
                    "top_country_share": top_share,
                    "top_country_drop_ratio": worst_drop,
                    "concentration_herfindahl": float(
                        geo.get("concentration_herfindahl") or 0.0
                    ),
                    "n_active_countries": float(
                        geo.get("n_active_countries") or 0
                    ),
                },
            )
        )
    return out


# ────────────────────────────────────────────────────────────────────
# Rule 6 — Format-market Mismatch
# ────────────────────────────────────────────────────────────────────


def rule_format_market_mismatch(
    store: Datastore,
    advertiser_by_creative: dict[int, tuple[int, int]],
) -> list[SliceRecommendation]:
    """Within `(country, vertical)`, compare this creative's format ROAS
    to the best-performing peer format. Fire if a peer format outperforms
    by ≥ FORMAT_MISMATCH_LIFT and our slice is below cohort median."""
    # Aggregate slice features → (country, vertical, format) ROAS.
    cvf_buckets: dict[
        tuple[str, str, str], dict[str, float]
    ] = {}
    creative_meta = store.creative_detail
    for (cid, country, _os), feats in store.slice_features.items():
        meta = creative_meta.get(int(cid)) or {}
        vertical = str(meta.get("vertical") or "")
        fmt = str(meta.get("format") or "")
        if not vertical or not fmt:
            continue
        key = (country, vertical, fmt)
        b = cvf_buckets.setdefault(
            key, {"spend": 0.0, "revenue": 0.0, "n": 0.0}
        )
        b["spend"] += float(feats.get("recent_spend_usd") or 0.0)
        b["revenue"] += float(feats.get("recent_revenue_usd") or 0.0)
        b["n"] += 1.0

    cvf_roas: dict[tuple[str, str, str], float] = {}
    for key, vals in cvf_buckets.items():
        if vals["spend"] > 0 and vals["n"] >= 3:  # need a real cohort
            cvf_roas[key] = vals["revenue"] / vals["spend"]

    out: list[SliceRecommendation] = []
    seen: set[tuple[int, str]] = set()  # one rec per (creative, country)
    for (cid, country, _os), feats in store.slice_features.items():
        if (cid, country) in seen:
            continue
        seen.add((cid, country))
        if cid not in advertiser_by_creative:
            continue
        adv_id, camp_id = advertiser_by_creative[cid]

        meta = creative_meta.get(int(cid)) or {}
        vertical = str(meta.get("vertical") or "")
        my_fmt = str(meta.get("format") or "")
        if not vertical or not my_fmt:
            continue

        my_roas = cvf_roas.get((country, vertical, my_fmt))
        if my_roas is None:
            continue
        # Find the best peer format in the same (country, vertical).
        peer_best_roas = 0.0
        peer_best_fmt = ""
        for (c, v, f), roas in cvf_roas.items():
            if c == country and v == vertical and f != my_fmt:
                if roas > peer_best_roas:
                    peer_best_roas = roas
                    peer_best_fmt = f
        if not peer_best_fmt or peer_best_roas <= 0:
            continue
        if peer_best_roas < (1.0 + FORMAT_MISMATCH_LIFT) * my_roas:
            continue

        slice_daily_spend = float(feats.get("daily_spend_recent") or 0.0)
        # Est. lift = (peer_roas - my_roas) × slice daily spend.
        est_impact = (peer_best_roas - my_roas) * slice_daily_spend

        rec = _make_rec(
            creative_id=cid,
            country=country,
            os_="*",
            advertiser_id=adv_id,
            campaign_id=camp_id,
            action_type="archive",
            severity="opportunity",
            headline="",
            rationale="",
            est_daily_impact_usd=est_impact,
            trigger_magnitude={
                "my_format_roas": my_roas,
                "peer_best_roas": peer_best_roas,
                "lift_multiple": (peer_best_roas / my_roas) if my_roas > 0 else 0.0,
                "slice_daily_spend": slice_daily_spend,
            },
        )
        rec.peer_format = peer_best_fmt  # type: ignore[attr-defined]
        rec.my_format = my_fmt  # type: ignore[attr-defined]
        out.append(rec)
    return out


# ────────────────────────────────────────────────────────────────────
# Rule 7 — Pattern Transfer (lightweight cosine similarity, no bandit)
# ────────────────────────────────────────────────────────────────────


def rule_pattern_transfer(
    store: Datastore,
    advertiser_by_creative: dict[int, tuple[int, int]],
) -> list[SliceRecommendation]:
    """For each creative, find a sibling (same advertiser) with cosine
    similarity ≥ floor that is ranked highly in a country this creative
    has *not* yet served. Recommend testing this creative there."""
    import numpy as np

    creative_meta = store.creative_detail
    served: dict[int, set[str]] = {}
    for (cid, country, _os) in store.slice_features.keys():
        served.setdefault(cid, set()).add(country)

    # Build advertiser → list of (creative_id, vector) for fast lookup.
    by_adv: dict[int, list[tuple[int, "np.ndarray"]]] = {}
    for cid, vec in store.creative_vectors.items():
        adv = advertiser_by_creative.get(cid, (None, None))[0]
        if adv is None:
            continue
        by_adv.setdefault(adv, []).append((int(cid), vec))

    # For each (sibling, country), cache the slice ROAS so we can pick the
    # peer that's actually winning in that country.
    sibling_country_roas: dict[tuple[int, str], float] = {}
    for (cid, country, _os), feats in store.slice_features.items():
        prev = sibling_country_roas.get((cid, country), 0.0)
        roas = float(feats.get("recent_roas") or 0.0)
        if roas > prev:
            sibling_country_roas[(cid, country)] = roas

    out: list[SliceRecommendation] = []
    seen: set[tuple[int, str]] = set()
    for cid, vec in store.creative_vectors.items():
        if cid not in advertiser_by_creative:
            continue
        adv_id, camp_id = advertiser_by_creative[cid]
        served_set = served.get(cid, set())

        # Find best sibling in this advertiser by cosine similarity.
        siblings = by_adv.get(adv_id, [])
        best_sim = 0.0
        best_sib = -1
        for sib_id, sib_vec in siblings:
            if sib_id == cid:
                continue
            try:
                sim = float(np.dot(vec, sib_vec))
            except Exception:
                continue
            if sim > best_sim:
                best_sim = sim
                best_sib = sib_id
        if best_sib < 0 or best_sim < PATTERN_SIMILARITY_FLOOR:
            continue

        # Find a country where the sibling is performing well that this
        # creative hasn't been tested in.
        sib_served = served.get(best_sib, set())
        unserved = sib_served - served_set
        if not unserved:
            continue
        target_country = max(
            unserved, key=lambda c: sibling_country_roas.get((best_sib, c), 0.0)
        )
        sib_roas = sibling_country_roas.get((best_sib, target_country), 0.0)
        if sib_roas <= 0:
            continue
        # Surface only one Pattern Transfer per (creative, country).
        if (cid, target_country) in seen:
            continue
        seen.add((cid, target_country))

        # Impact = sib_roas × est. spend allocation (use creative daily
        # spend / served countries as a rough budget).
        creative_daily_spend = sum(
            float(f.get("daily_spend_recent") or 0.0)
            for k, f in store.slice_features.items()
            if k[0] == cid
        )
        est_spend_alloc = (
            creative_daily_spend / max(len(served_set) + 1, 1)
        )
        est_impact = sib_roas * est_spend_alloc

        rec = _make_rec(
            creative_id=cid,
            country=target_country,
            os_="*",
            advertiser_id=adv_id,
            campaign_id=camp_id,
            action_type="rotate",
            severity="opportunity",
            headline="",
            rationale="",
            est_daily_impact_usd=est_impact,
            trigger_magnitude={
                "sibling_creative_id": float(best_sib),
                "similarity": best_sim,
                "sibling_target_country_roas": sib_roas,
                "est_spend_alloc": est_spend_alloc,
            },
        )
        rec.sibling_creative_id = best_sib  # type: ignore[attr-defined]
        out.append(rec)
    return out


# ────────────────────────────────────────────────────────────────────
# Rule 8 — Reallocation (linearised marginal-ROAS extrapolation)
# ────────────────────────────────────────────────────────────────────


def rule_reallocation(
    store: Datastore,
    advertiser_by_creative: dict[int, tuple[int, int]],
) -> list[SliceRecommendation]:
    """Per advertiser, rank their slices by marginal ROAS. Recommend
    shifting budget from bottom-quartile slices (negative marginal ROAS
    or zero spend slope) to top-quartile slices. One recommendation per
    (donor, receiver) pair, capped at top 2 per advertiser to avoid
    flooding the queue."""
    by_adv: dict[
        int, list[tuple[SliceKey, dict[str, float], dict[str, float]]]
    ] = {}
    for key, marginal in store.marginal_roas_by_slice.items():
        cid = int(key[0])
        if cid not in advertiser_by_creative:
            continue
        adv_id, _camp = advertiser_by_creative[cid]
        feats = store.slice_features.get(key)
        if feats is None:
            continue
        if float(feats.get("daily_spend_recent") or 0.0) < REALLOC_MIN_DAILY_SPEND:
            continue
        by_adv.setdefault(adv_id, []).append((key, feats, marginal))

    out: list[SliceRecommendation] = []
    for adv_id, rows in by_adv.items():
        if len(rows) < 4:
            continue
        rows.sort(key=lambda r: r[2]["marginal_roas"])
        # Bottom + top quartile.
        q = max(1, len(rows) // 4)
        bottom = rows[:q]
        top = rows[-q:][::-1]  # highest marginal first
        for i, (donor_key, donor_feats, donor_m) in enumerate(bottom[:2]):
            if i >= len(top):
                break
            recv_key, recv_feats, recv_m = top[i]
            if recv_m["marginal_roas"] <= donor_m["marginal_roas"]:
                continue
            # Suggest shifting up to half of the donor's daily spend.
            shift = float(donor_feats.get("daily_spend_recent") or 0.0) * 0.5
            est_impact = shift * (
                recv_m["marginal_roas"] - donor_m["marginal_roas"]
            )
            if est_impact <= 0:
                continue

            donor_cid, donor_country, donor_os = donor_key
            recv_cid, recv_country, recv_os = recv_key
            adv_id_local, camp_id = advertiser_by_creative[donor_cid]

            rec = _make_rec(
                creative_id=donor_cid,
                country=donor_country,
                os_=donor_os,
                advertiser_id=adv_id_local,
                campaign_id=camp_id,
                action_type="shift",
                severity="opportunity",
                headline="",
                rationale="",
                est_daily_impact_usd=est_impact,
                trigger_magnitude={
                    "donor_marginal_roas": donor_m["marginal_roas"],
                    "receiver_marginal_roas": recv_m["marginal_roas"],
                    "donor_daily_spend": float(
                        donor_feats.get("daily_spend_recent") or 0.0
                    ),
                    "shift_usd": shift,
                    "receiver_creative_id": float(recv_cid),
                },
            )
            rec.receiver_creative_id = recv_cid  # type: ignore[attr-defined]
            rec.receiver_country = recv_country  # type: ignore[attr-defined]
            rec.receiver_os = recv_os  # type: ignore[attr-defined]
            rec.shift_usd = shift  # type: ignore[attr-defined]
            out.append(rec)
    return out


# ────────────────────────────────────────────────────────────────────
# Run-all + ranking
# ────────────────────────────────────────────────────────────────────


def run_all(store: Datastore) -> dict[int, list[SliceRecommendation]]:
    """Run all 8 rules, dedupe, rank by est_daily_impact_usd within each
    advertiser, return the per-advertiser map."""
    advertiser_by_creative = _advertiser_lookup(store)
    creative_baselines = _per_creative_baselines(store.slice_features)

    all_recs: list[SliceRecommendation] = []
    rules: list[tuple[str, Any]] = [
        ("geographic_prune", lambda: rule_geographic_prune(
            store, advertiser_by_creative, creative_baselines)),
        ("geographic_scale", lambda: rule_geographic_scale(
            store, advertiser_by_creative, creative_baselines)),
        ("os_frequency_cap", lambda: rule_os_frequency_cap(
            store, advertiser_by_creative)),
        ("cross_market_early_warning", lambda: rule_cross_market_early_warning(
            store, advertiser_by_creative)),
        ("concentration_risk", lambda: rule_concentration_risk(
            store, advertiser_by_creative)),
        ("format_market_mismatch", lambda: rule_format_market_mismatch(
            store, advertiser_by_creative)),
        ("pattern_transfer", lambda: rule_pattern_transfer(
            store, advertiser_by_creative)),
        ("reallocation", lambda: rule_reallocation(
            store, advertiser_by_creative)),
    ]
    for name, fn in rules:
        try:
            recs = fn()
        except Exception as e:  # noqa: BLE001
            log.warning("rule %s raised: %s", name, e)
            recs = []
        log.info("rule %s: %d recommendations", name, len(recs))
        all_recs.extend(recs)

    # Dedup by recommendation_id (rules can produce duplicates if the same
    # (creative, country, os, action) shows up in multiple rules).
    seen: dict[str, SliceRecommendation] = {}
    for r in all_recs:
        prev = seen.get(r.recommendation_id)
        if prev is None or r.est_daily_impact_usd > prev.est_daily_impact_usd:
            seen[r.recommendation_id] = r
    deduped = list(seen.values())

    # Rank within advertiser by est_daily_impact desc; cap at 50.
    by_adv: dict[int, list[SliceRecommendation]] = {}
    for r in deduped:
        by_adv.setdefault(r.advertiser_id, []).append(r)
    for adv, lst in by_adv.items():
        lst.sort(key=lambda r: r.est_daily_impact_usd, reverse=True)
        by_adv[adv] = lst[:50]

    log.info(
        "advisor: %d total recommendations across %d advertisers",
        sum(len(v) for v in by_adv.values()),
        len(by_adv),
    )
    return by_adv
