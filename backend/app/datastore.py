from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .config import (
    DATASET_ROOT,
    EXPECTED_ADVERTISERS,
    EXPECTED_CAMPAIGNS,
    EXPECTED_CREATIVES,
    EXPECTED_DAILY_ROWS,
)

log = logging.getLogger(__name__)


@dataclass
class Datastore:
    advertisers: pd.DataFrame = field(default_factory=pd.DataFrame)
    campaigns: pd.DataFrame = field(default_factory=pd.DataFrame)
    creatives: pd.DataFrame = field(default_factory=pd.DataFrame)
    daily: pd.DataFrame = field(default_factory=pd.DataFrame)
    creative_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    campaign_summary: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Precomputed per-creative daily aggregate keyed by creative_id.
    timeseries_by_creative: dict[int, list[dict[str, Any]]] = field(default_factory=dict)
    # Joined creatives + creative_summary keyed by creative_id for O(1) detail lookup.
    creative_detail: dict[int, dict[str, Any]] = field(default_factory=dict)
    # Flat per-creative row payload used by /api/creatives — includes health, sparkline, days_active.
    flat_row_by_creative: dict[int, dict[str, Any]] = field(default_factory=dict)
    # Cached portfolio aggregates computed at startup.
    portfolio_kpis: dict[str, Any] = field(default_factory=dict)
    tab_counts: dict[str, int] = field(default_factory=dict)
    # L2-normalised attribute feature vectors for cosine-similarity twin lookup.
    creative_vectors: dict[int, np.ndarray] = field(default_factory=dict)
    creative_vector_dims: int = 0

    def load(self) -> None:
        self.advertisers = pd.read_csv(DATASET_ROOT / "advertisers.csv")
        self.campaigns = pd.read_csv(
            DATASET_ROOT / "campaigns.csv",
            parse_dates=["start_date", "end_date"],
        )
        self.creatives = pd.read_csv(
            DATASET_ROOT / "creatives.csv",
            parse_dates=["creative_launch_date"],
        )
        self.daily = pd.read_csv(
            DATASET_ROOT / "creative_daily_country_os_stats.csv",
            parse_dates=["date"],
        )
        self.creative_summary = pd.read_csv(
            DATASET_ROOT / "creative_summary.csv",
            parse_dates=["creative_launch_date"],
        )
        self.campaign_summary = pd.read_csv(
            DATASET_ROOT / "campaign_summary.csv",
            parse_dates=["start_date", "end_date"],
        )

        # Explode pipe-separated country lists on campaigns.
        self.campaigns["country_list"] = self.campaigns["countries"].fillna("").str.split("|")
        self.campaign_summary["country_list"] = (
            self.campaign_summary["countries"].fillna("").str.split("|")
        )

        # Pre-aggregate per-creative daily time series across country × OS.
        per_day = (
            self.daily.groupby(["creative_id", "date"], as_index=False)
            .agg(
                impressions=("impressions", "sum"),
                clicks=("clicks", "sum"),
                conversions=("conversions", "sum"),
                spend_usd=("spend_usd", "sum"),
                revenue_usd=("revenue_usd", "sum"),
            )
            .sort_values(["creative_id", "date"])
        )
        per_day["date"] = per_day["date"].dt.strftime("%Y-%m-%d")
        self.timeseries_by_creative = {
            int(cid): group.drop(columns=["creative_id"]).to_dict("records")
            for cid, group in per_day.groupby("creative_id", sort=False)
        }

        # Pre-join creative + creative_summary for detail lookup.
        creative_meta = self.creatives.set_index("creative_id")
        summary = self.creative_summary.set_index("creative_id")
        # Right-join columns from summary that aren't already in creatives.
        summary_only_cols = [c for c in summary.columns if c not in creative_meta.columns]
        joined = creative_meta.join(summary[summary_only_cols], how="left")

        # Convert datetimes to ISO strings for JSON serialisation.
        for col in joined.columns:
            if pd.api.types.is_datetime64_any_dtype(joined[col]):
                joined[col] = joined[col].dt.strftime("%Y-%m-%d")

        # NaN → None so pydantic produces null in JSON. pd.NA / NaN round-trips via object dtype.
        joined_nullable = joined.astype(object).where(joined.notna(), None)
        joined_records = joined_nullable.reset_index().to_dict("records")
        self.creative_detail = {int(r["creative_id"]): r for r in joined_records}

        self._compute_quadrants()
        self._compute_flat_rows()
        self._compute_saturation()
        self._compute_creative_vectors()
        self._compute_portfolio_aggregates()
        self._verify_counts()

    def _compute_creative_vectors(self) -> None:
        """Build a per-creative attribute feature vector for cosine-similarity
        twin lookup. Concatenates one-hot categorical attributes with
        normalised numeric scores and binary flags. Each vector is L2-
        normalised so cosine similarity is just a dot product at lookup time.
        """
        df = self.creatives.copy()

        cat_cols = [
            "theme",
            "hook_type",
            "dominant_color",
            "emotional_tone",
            "cta_text",
            "language",
        ]
        cat_part = pd.get_dummies(
            df[cat_cols].astype(str).fillna("__missing__"),
            dtype=float,
        )

        # Numeric scores in [0, 1] already; just clip + fill.
        num_cols = [
            "text_density",
            "clutter_score",
            "novelty_score",
            "brand_visibility_score",
            "motion_score",
            "readability_score",
        ]
        num_part = df[num_cols].fillna(0.0).clip(0.0, 1.0).to_numpy(dtype=float)

        # Bounded counts → scale to [0, 1].
        count_cols = {
            "duration_sec": 30.0,  # videos cap at ~30s in dataset
            "faces_count": 3.0,
            "product_count": 3.0,
            "copy_length_chars": 60.0,
        }
        count_blocks = []
        for col, cap in count_cols.items():
            v = df[col].fillna(0.0).clip(0.0, cap).to_numpy(dtype=float) / cap
            count_blocks.append(v.reshape(-1, 1))
        count_part = np.hstack(count_blocks) if count_blocks else np.zeros((len(df), 0))

        bin_cols = [
            "has_discount_badge",
            "has_ugc_style",
            "has_price",
            "has_gameplay",
        ]
        bin_part = df[bin_cols].fillna(0).to_numpy(dtype=float)

        # Down-weight categorical attributes (they dominate by sheer dimension
        # count otherwise; numerics are 0–1 in [0, 1] across only ~6 cells).
        feature = np.hstack(
            [cat_part.to_numpy(dtype=float) * 1.0, num_part * 1.5, count_part * 1.0, bin_part * 1.5]
        )
        norms = np.linalg.norm(feature, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        feature /= norms

        self.creative_vector_dims = int(feature.shape[1])
        for i, cid in enumerate(df["creative_id"].astype(int)):
            self.creative_vectors[int(cid)] = feature[i]

    def _compute_saturation(self) -> None:
        """Per-creative portfolio-saturation diagnostic.

        Triple key = ``(theme, hook_type, dominant_color)``. For each creative
        we count how many other creatives share the triple within the same
        advertiser, and globally; we expose mean CTR/CVR for the cohort and a
        consolidation recommendation when the cohort is ≥ 5 within the
        advertiser. Falls back to ``(theme, hook_type)`` if the triple cohort
        has < 2 — the dataset's dominant_color column is fairly diverse so
        many creatives end up alone, in which case the broader pair is more
        useful.
        """
        s = self.creative_summary

        # Pull the metadata + advertiser fields we need.
        meta = self.creatives.set_index("creative_id")
        advertiser_id_by_creative: dict[int, int] = {}
        # advertiser_id is on campaigns.csv; join via campaign_id.
        camp_to_adv = self.campaigns.set_index("campaign_id")["advertiser_id"].to_dict()
        for cid, row in meta.iterrows():
            advertiser_id_by_creative[int(cid)] = int(camp_to_adv.get(int(row["campaign_id"]), -1))

        ctr_by_cid = s.set_index("creative_id")["overall_ctr"].to_dict()
        cvr_by_cid = s.set_index("creative_id")["overall_cvr"].to_dict()

        # Build cohort indices.
        triple_global: dict[tuple, list[int]] = {}
        triple_advertiser: dict[tuple, list[int]] = {}
        pair_advertiser: dict[tuple, list[int]] = {}
        for cid_raw, row in meta.iterrows():
            cid = int(cid_raw)
            triple = (row.get("theme"), row.get("hook_type"), row.get("dominant_color"))
            pair = (row.get("theme"), row.get("hook_type"))
            adv_id = advertiser_id_by_creative.get(cid, -1)
            triple_global.setdefault(triple, []).append(cid)
            triple_advertiser.setdefault((adv_id, *triple), []).append(cid)
            pair_advertiser.setdefault((adv_id, *pair), []).append(cid)

        for cid_raw, row in meta.iterrows():
            cid = int(cid_raw)
            triple = (row.get("theme"), row.get("hook_type"), row.get("dominant_color"))
            pair = (row.get("theme"), row.get("hook_type"))
            adv_id = advertiser_id_by_creative.get(cid, -1)

            adv_triple_cohort = triple_advertiser.get((adv_id, *triple), [])
            global_cohort = triple_global.get(triple, [])
            # Fall back to the (theme, hook_type) pair if triple cohort within advertiser is too sparse.
            used_triple = True
            if len(adv_triple_cohort) < 2:
                adv_triple_cohort = pair_advertiser.get((adv_id, *pair), [])
                used_triple = False

            cohort_avg_ctr = (
                sum(_safe_float(ctr_by_cid.get(c)) for c in adv_triple_cohort)
                / len(adv_triple_cohort)
                if adv_triple_cohort
                else 0.0
            )
            cohort_avg_cvr = (
                sum(_safe_float(cvr_by_cid.get(c)) for c in adv_triple_cohort)
                / len(adv_triple_cohort)
                if adv_triple_cohort
                else 0.0
            )
            this_ctr = _safe_float(ctr_by_cid.get(cid))
            this_cvr = _safe_float(cvr_by_cid.get(cid))
            cohort_n = len(adv_triple_cohort)
            recommend_to: int | None = None
            if cohort_n >= 5:
                recommend_to = max(2, -(-cohort_n // 3))  # ceil(cohort_n / 3)

            saturation = {
                "triple": {
                    "theme": row.get("theme"),
                    "hook_type": row.get("hook_type"),
                    "dominant_color": row.get("dominant_color") if used_triple else None,
                },
                "used_triple": used_triple,
                "cohort_advertiser_size": cohort_n,
                "cohort_global_size": len(global_cohort),
                "cohort_avg_ctr": round(cohort_avg_ctr, 6),
                "cohort_avg_cvr": round(cohort_avg_cvr, 6),
                "this_ctr": round(this_ctr, 6),
                "this_cvr": round(this_cvr, 6),
                "recommend_consolidate_to": recommend_to,
            }
            detail = self.creative_detail.get(cid)
            if detail is not None:
                detail["saturation"] = saturation

    def _compute_flat_rows(self) -> None:
        """Flat row per creative for the cockpit table + Explore. Bakes in:

        - **health**: fatigue-adjusted composite ∈ [0, 100]. Formula:
            decay_pct = ctr_decay_pct (negative when fatigued)
            fatigue_penalty = clamp(-decay_pct, 0, 1)
            health = round(perf_score × (1 − fatigue_penalty × 0.7) × 100)
          The 0.7 weight prevents catastrophic fatigue from zeroing the score
          entirely. Drives ``status_band`` (see below) which assigns the tab.
        - **status_band**: bands → tabs.
            ≥ 70 → scale, 40–69 → watch, 20–39 → rescue, < 20 → cut.
        - **status**: pass-through of dataset's ``creative_status`` so the UI
          can show the synthetic label as a *validation* signal alongside our
          band ("agree" / "diverges").
        - **sparkline**: last 30 days of CTR. No zero-padding — frontend
          right-aligns shorter series.
        - **days_active**: from the dataset's ``total_days_active`` column.
        """
        s = self.creative_summary.set_index("creative_id")
        creative_meta = self.creatives.set_index("creative_id")

        def _sparkline(creative_id: int) -> list[float]:
            ts = self.timeseries_by_creative.get(creative_id, [])
            tail = ts[-30:] if len(ts) > 30 else ts
            out: list[float] = []
            for p in tail:
                impressions = p.get("impressions") or 0
                clicks = p.get("clicks") or 0
                out.append(round(clicks / impressions, 6) if impressions > 0 else 0.0)
            return out

        for creative_id_raw, summary_row in s.iterrows():
            creative_id = int(creative_id_raw)
            meta_row = creative_meta.loc[creative_id]
            perf_score = _safe_float(summary_row.get("perf_score"))
            decay = _safe_float(summary_row.get("ctr_decay_pct"))
            status_label = summary_row.get("creative_status")
            health = _compute_health(perf_score, decay, status_label)
            band = _band_from_health(health)
            fatigue_day = summary_row.get("fatigue_day")
            fatigue_day_v: int | None = (
                int(fatigue_day) if fatigue_day is not None and not pd.isna(fatigue_day) else None
            )
            self.flat_row_by_creative[creative_id] = {
                "creative_id": creative_id,
                "campaign_id": int(meta_row["campaign_id"]),
                "advertiser_name": meta_row["advertiser_name"],
                "headline": meta_row.get("headline") or "",
                "vertical": meta_row["vertical"],
                "format": meta_row["format"],
                "status": summary_row.get("creative_status"),
                "status_band": band,
                "ctr": _safe_float(summary_row.get("overall_ctr")),
                "cvr": _safe_float(summary_row.get("overall_cvr")),
                "roas": _safe_float(summary_row.get("overall_roas")),
                "spend_usd": _safe_float(summary_row.get("total_spend_usd")),
                "impressions": _safe_int(summary_row.get("total_impressions")),
                "clicks": _safe_int(summary_row.get("total_clicks")),
                "conversions": _safe_int(summary_row.get("total_conversions")),
                "revenue_usd": _safe_float(summary_row.get("total_revenue_usd")),
                "days_active": int(summary_row.get("total_days_active") or 0),
                "health": health,
                "sparkline": _sparkline(creative_id),
                "fatigue_day": fatigue_day_v,
                "asset_file": meta_row["asset_file"],
            }
            # Mirror band+health onto creative_detail so the detail page can
            # render "Our band: ... · Smadex label: ... ✓ agree" without a second fetch.
            detail = self.creative_detail.get(creative_id)
            if detail is not None:
                detail["health"] = health
                detail["status_band"] = band

    def _compute_portfolio_aggregates(self) -> None:
        """Roll up KPIs + tab counts once at startup (data is static).

        Tab counts come from the dataset's ``creative_status`` (synthetic
        ground-truth label) — that's what assigns each creative to a tab.
        Our computed ``status_band`` is shown alongside as a validation
        signal on the detail page.
        """
        s = self.creative_summary
        total_impressions = int(s["total_impressions"].sum())
        total_clicks = int(s["total_clicks"].sum())
        total_conversions = int(s["total_conversions"].sum())
        total_spend = float(s["total_spend_usd"].sum())
        total_revenue = float(s["total_revenue_usd"].sum())
        attention = int(((s["creative_status"] == "fatigued") | (s["creative_status"] == "underperformer")).sum())

        # Daily aggregates over the full date range for KPI sparklines.
        daily_agg = (
            self.daily.groupby("date", as_index=False)
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
            (float(r) / float(s_)) if s_ else 0.0
            for r, s_ in zip(daily_agg["revenue_usd"], daily_agg["spend_usd"])
        ]

        self.portfolio_kpis = {
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

        status_counts = s["creative_status"].value_counts().to_dict()
        self.tab_counts = {
            "scale": int(status_counts.get("top_performer", 0)),
            "watch": int(status_counts.get("stable", 0)),
            "rescue": int(status_counts.get("fatigued", 0)),
            "cut": int(status_counts.get("underperformer", 0)),
            "explore": int(len(s)),
        }

    def _compute_quadrants(self) -> None:
        """Diagnostic CTR×CVR quadrant per creative, relative to its
        (vertical, format) cohort. Raw percentiles for now — Q1 will replace
        this with Bayesian-shrunk percentiles once it ships.
        """
        s = self.creative_summary
        cohort_keys = ["vertical", "format"]
        ctr_pct = s.groupby(cohort_keys)["overall_ctr"].rank(pct=True)
        cvr_pct = s.groupby(cohort_keys)["overall_cvr"].rank(pct=True)
        cohort_size = s.groupby(cohort_keys).size()

        for idx, row in s.iterrows():
            creative_id = int(row["creative_id"])
            cp = ctr_pct.loc[idx]
            vp = cvr_pct.loc[idx]
            cp_v = None if pd.isna(cp) else float(cp)
            vp_v = None if pd.isna(vp) else float(vp)
            label = _quadrant_label(cp_v, vp_v)
            quadrant = {
                "ctr_percentile": cp_v,
                "cvr_percentile": vp_v,
                "quadrant_label": label,
                "cohort_keys": {
                    "vertical": row["vertical"],
                    "format": row["format"],
                },
                "cohort_size": int(cohort_size.loc[(row["vertical"], row["format"])]),
            }
            detail = self.creative_detail.get(creative_id)
            if detail is not None:
                detail["quadrant"] = quadrant

    def _verify_counts(self) -> None:
        counts = {
            "advertisers": len(self.advertisers),
            "campaigns": len(self.campaigns),
            "creatives": len(self.creatives),
            "daily_rows": len(self.daily),
        }
        log.info(
            "Dataset loaded: advertisers=%(advertisers)d campaigns=%(campaigns)d "
            "creatives=%(creatives)d daily_rows=%(daily_rows)d",
            counts,
        )
        expected = {
            "advertisers": EXPECTED_ADVERTISERS,
            "campaigns": EXPECTED_CAMPAIGNS,
            "creatives": EXPECTED_CREATIVES,
            "daily_rows": EXPECTED_DAILY_ROWS,
        }
        if counts != expected:
            raise RuntimeError(
                f"Dataset row counts do not match expectations. got={counts} expected={expected}"
            )


def _safe_float(v: Any) -> float:
    if v is None:
        return 0.0
    try:
        return float(v) if not pd.isna(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _safe_int(v: Any) -> int:
    if v is None:
        return 0
    try:
        return int(v) if not pd.isna(v) else 0
    except (TypeError, ValueError):
        return 0


def _compute_health(perf_score: float, decay: float, status: str | None) -> int:
    """Visual health score 0–100. Coherent with the cohort tab.

    The dataset's ``perf_score`` reflects lifetime performance; alone it's too
    generous for *fatigued* creatives because they were strong before the
    drop. We weight by recent trajectory using ``ctr_decay_pct``.

      ``trajectory_factor = clamp(1 + decay × decay_weight, floor, 1)``

    Where ``decay_weight`` is heavier for fatigued creatives than for stable
    or top performers (whose decay is normal end-of-flight tail-off rather
    than market saturation). ``floor`` prevents Cut-status creatives from
    rounding to negatives.
    """
    base = perf_score * 100.0
    if status == "fatigued":
        trajectory = max(0.30, min(1.0, 1.0 + decay * 0.75))
    elif status == "underperformer":
        trajectory = max(0.50, min(1.0, 1.0 + decay * 0.30))
    elif status == "top_performer":
        trajectory = max(0.85, min(1.0, 1.0 + decay * 0.15))
    else:  # stable / unknown
        trajectory = max(0.70, min(1.0, 1.0 + decay * 0.30))
    return max(0, min(100, int(round(base * trajectory))))


def _band_from_health(health: int) -> str:
    if health >= 70:
        return "scale"
    if health >= 40:
        return "watch"
    if health >= 20:
        return "rescue"
    return "cut"


def _quadrant_label(ctr_pct: float | None, cvr_pct: float | None) -> str:
    if ctr_pct is None or cvr_pct is None:
        return "unknown"
    high_ctr = ctr_pct >= 0.5
    high_cvr = cvr_pct >= 0.5
    if high_ctr and high_cvr:
        return "top-performer"
    if high_ctr and not high_cvr:
        return "clickbait-risk"
    if not high_ctr and high_cvr:
        return "niche-converter"
    return "below-peers"


_store: Datastore | None = None


def init_store() -> Datastore:
    global _store
    _store = Datastore()
    _store.load()
    return _store


def get_store() -> Datastore:
    if _store is None:
        raise RuntimeError("Datastore not initialised. Call init_store() at startup.")
    return _store
