from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

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
        self._compute_portfolio_aggregates()
        self._verify_counts()

    def _compute_flat_rows(self) -> None:
        """Flat row per creative for the cockpit table + Explore. Bakes in
        health = round(perf_score * 100), 30-day CTR sparkline (no zero
        padding — front-end right-aligns shorter series), and days_active.
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
            perf_score = summary_row.get("perf_score")
            health = (
                int(round(float(perf_score) * 100))
                if perf_score is not None and not pd.isna(perf_score)
                else 0
            )
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

    def _compute_portfolio_aggregates(self) -> None:
        """Roll up KPIs + tab counts once at startup (data is static)."""
        s = self.creative_summary
        total_impressions = int(s["total_impressions"].sum())
        total_clicks = int(s["total_clicks"].sum())
        total_conversions = int(s["total_conversions"].sum())
        total_spend = float(s["total_spend_usd"].sum())
        total_revenue = float(s["total_revenue_usd"].sum())
        attention = int(((s["creative_status"] == "fatigued") | (s["creative_status"] == "underperformer")).sum())

        self.portfolio_kpis = {
            "total_spend_usd": total_spend,
            "total_revenue_usd": total_revenue,
            "roas": (total_revenue / total_spend) if total_spend else 0.0,
            "ctr": (total_clicks / total_impressions) if total_impressions else 0.0,
            "cvr": (total_conversions / total_clicks) if total_clicks else 0.0,
            "attention_count": attention,
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
