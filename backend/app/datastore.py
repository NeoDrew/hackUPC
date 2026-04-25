from __future__ import annotations

import logging
import math
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
    timeseries_by_creative: dict[int, list[dict[str, Any]]] = field(
        default_factory=dict
    )
    # Joined creatives + creative_summary keyed by creative_id for O(1) detail lookup.
    creative_detail: dict[int, dict[str, Any]] = field(default_factory=dict)
    # Flat per-creative row payload used by /api/creatives — includes health, sparkline, days_active.
    flat_row_by_creative: dict[int, dict[str, Any]] = field(default_factory=dict)
    # Cached portfolio aggregates computed at startup.
    portfolio_kpis: dict[str, Any] = field(default_factory=dict)
    tab_counts: dict[str, int] = field(default_factory=dict)
    # Evidence-based Q1 health score and transparent component payload by creative_id.
    health_by_creative: dict[int, dict[str, Any]] = field(default_factory=dict)
    # Startup checks for score stability, distribution, and synthetic-label sanity.
    health_diagnostics: dict[str, Any] = field(default_factory=dict)
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
        self.campaigns["country_list"] = (
            self.campaigns["countries"].fillna("").str.split("|")
        )
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
        summary_only_cols = [
            c for c in summary.columns if c not in creative_meta.columns
        ]
        joined = creative_meta.join(summary[summary_only_cols], how="left")

        # Convert datetimes to ISO strings for JSON serialisation.
        for col in joined.columns:
            if pd.api.types.is_datetime64_any_dtype(joined[col]):
                joined[col] = joined[col].dt.strftime("%Y-%m-%d")

        # NaN → None so pydantic produces null in JSON. pd.NA / NaN round-trips via object dtype.
        joined_nullable = joined.astype(object).where(joined.notna(), None)
        joined_records = joined_nullable.reset_index().to_dict("records")
        self.creative_detail = {int(r["creative_id"]): r for r in joined_records}

        self._compute_health_scores()
        self._compute_quadrants()
        self._compute_flat_rows()
        self._compute_saturation()
        self._compute_creative_vectors()
        self._compute_portfolio_aggregates()
        self._verify_counts()

    def _compute_health_scores(self) -> None:
        """Evidence-based Q1 creative health score.

        The score is a transparent 0–100 weighted report card over:
        S = posterior objective strength, C = confidence, T = recent trend,
        R = cohort rank, E = business efficiency, B = reliability bonus.

        It deliberately does **not** consume ``perf_score`` or
        ``creative_status`` as inputs. Those fields are only used in
        ``health_diagnostics`` for validation against the synthetic labels.
        """
        s = self.creative_summary.copy()
        campaign_kpi = self.campaigns.set_index("campaign_id")["kpi_goal"].to_dict()
        s["kpi_goal"] = s["campaign_id"].map(campaign_kpi).fillna("CTR")
        s["objective_mode"] = s["kpi_goal"].map(_objective_mode)

        cohort_keys = ["vertical", "format"]
        cohort = s.groupby(cohort_keys, as_index=False).agg(
            cohort_impressions=("total_impressions", "sum"),
            cohort_clicks=("total_clicks", "sum"),
            cohort_conversions=("total_conversions", "sum"),
            cohort_spend=("total_spend_usd", "sum"),
            cohort_revenue=("total_revenue_usd", "sum"),
        )
        s = s.merge(cohort, on=cohort_keys, how="left")

        median_impressions = _safe_float(s["total_impressions"].median())
        median_clicks = _safe_float(s["total_clicks"].median())
        median_spend = _safe_float(s["total_spend_usd"].median())
        ctr_prior_n = max(1000.0, min(10000.0, median_impressions * 0.05))
        cvr_prior_n = max(50.0, min(500.0, median_clicks * 0.10))
        spend_prior_n = max(100.0, min(1000.0, median_spend * 0.10))

        s["ctr_prior"] = (
            s["cohort_clicks"]
            / s["cohort_impressions"].where(s["cohort_impressions"] > 0)
        ).fillna(0.0)
        s["cvr_prior"] = (
            s["cohort_conversions"] / s["cohort_clicks"].where(s["cohort_clicks"] > 0)
        ).fillna(0.0)
        s["roas_prior"] = (
            s["cohort_revenue"] / s["cohort_spend"].where(s["cohort_spend"] > 0)
        ).fillna(0.0)
        s["cpa_inv_prior"] = (
            s["cohort_conversions"] / s["cohort_spend"].where(s["cohort_spend"] > 0)
        ).fillna(0.0)

        s["ctr_post"] = (
            (s["total_clicks"] + s["ctr_prior"] * ctr_prior_n)
            / (s["total_impressions"] + ctr_prior_n)
        ).fillna(0.0)
        s["cvr_post"] = (
            (s["total_conversions"] + s["cvr_prior"] * cvr_prior_n)
            / (s["total_clicks"] + cvr_prior_n)
        ).fillna(0.0)
        s["roas_post"] = (
            (s["total_revenue_usd"] + s["roas_prior"] * spend_prior_n)
            / (s["total_spend_usd"] + spend_prior_n)
        ).fillna(0.0)
        s["cpa_inv_post"] = (
            (s["total_conversions"] + s["cpa_inv_prior"] * spend_prior_n)
            / (s["total_spend_usd"] + spend_prior_n)
        ).fillna(0.0)

        ctr_p = s["ctr_post"].clip(0.0, 1.0)
        cvr_p = s["cvr_post"].clip(0.0, 1.0)
        s["ctr_width"] = (
            3.92
            * (
                (ctr_p * (1.0 - ctr_p)) / (s["total_impressions"] + ctr_prior_n + 1.0)
            ).pow(0.5)
        ).fillna(0.0)
        s["cvr_width"] = (
            3.92
            * ((cvr_p * (1.0 - cvr_p)) / (s["total_clicks"] + cvr_prior_n + 1.0)).pow(
                0.5
            )
        ).fillna(0.0)
        s["roas_width"] = (
            1.0 / (s["total_spend_usd"] + spend_prior_n + 1.0).pow(0.5)
        ).fillna(0.0)
        s["cpa_width"] = s["roas_width"]

        s["selected_value"] = s.apply(
            lambda row: _selected_by_objective(row, _OBJECTIVE_METRIC_COLUMNS), axis=1
        )
        s["selected_width"] = s.apply(
            lambda row: _selected_by_objective(row, _OBJECTIVE_WIDTH_COLUMNS), axis=1
        )
        s["effective_sample_size"] = s.apply(_effective_sample_size, axis=1)
        s["efficiency_value"] = s.apply(_efficiency_value, axis=1)

        s["S"] = 0.0
        s["C"] = 0.0
        s["E"] = 0.0
        s["B"] = 0.0
        for mode in _OBJECTIVE_METRIC_COLUMNS:
            mask = s["objective_mode"] == mode
            s.loc[mask, "S"] = _robust_normalize(s.loc[mask, "selected_value"])
            s.loc[mask, "C"] = _normalise_inverse_width(s.loc[mask, "selected_width"])
            s.loc[mask, "E"] = _robust_normalize(s.loc[mask, "efficiency_value"])
            s.loc[mask, "B"] = _reliability_bonus(s.loc[mask, "effective_sample_size"])

        s["T"] = s.apply(
            lambda row: _trend_component(
                self.timeseries_by_creative.get(int(row["creative_id"]), []),
                str(row["objective_mode"]),
                int(row.get("total_days_active") or 0),
            ),
            axis=1,
        )

        fallback_rank = pd.Series(0.5, index=s.index, dtype="float64")
        fallback_size = s.groupby(cohort_keys)["creative_id"].transform("count")
        for mode, metric_col in _OBJECTIVE_METRIC_COLUMNS.items():
            mode_ranks = s.groupby(cohort_keys)[metric_col].rank(pct=True)
            mask = s["objective_mode"] == mode
            fallback_rank.loc[mask] = mode_ranks.loc[mask].fillna(0.5)

        primary_rank, primary_meta = _primary_cohort_ranks(
            self.daily, self.creatives, s
        )
        s["R"] = s.apply(
            lambda row: (
                _safe_float(
                    primary_rank.get(
                        int(row["creative_id"]),
                        fallback_rank.loc[row.name],
                    )
                )
                or 0.5
            ),
            axis=1,
        )

        weights = {
            "w1": 0.30,
            "w2": 0.15,
            "w3": 0.15,
            "w4": 0.20,
            "w5": 0.10,
            "w6": 0.10,
        }
        s["health"] = (
            100.0
            * (
                weights["w1"] * s["S"]
                + weights["w2"] * s["C"]
                + weights["w3"] * s["T"]
                + weights["w4"] * s["R"]
                + weights["w5"] * s["E"]
                + weights["w6"] * s["B"]
            )
        ).clip(0.0, 100.0)
        s["status_band"] = s["health"].round().astype(int).map(_band_from_health)

        self.health_by_creative = {}
        for idx, row in s.iterrows():
            creative_id = int(row["creative_id"])
            components = {
                "S": _clamp01(_safe_float(row.get("S"))),
                "C": _clamp01(_safe_float(row.get("C"))),
                "T": _clamp01(_safe_float(row.get("T"))),
                "R": _clamp01(_safe_float(row.get("R"))),
                "E": _clamp01(_safe_float(row.get("E"))),
                "B": _clamp01(_safe_float(row.get("B"))),
            }
            contributions = {
                "S": round(100.0 * weights["w1"] * components["S"], 2),
                "C": round(100.0 * weights["w2"] * components["C"], 2),
                "T": round(100.0 * weights["w3"] * components["T"], 2),
                "R": round(100.0 * weights["w4"] * components["R"], 2),
                "E": round(100.0 * weights["w5"] * components["E"], 2),
                "B": round(100.0 * weights["w6"] * components["B"], 2),
            }
            cohort_meta = primary_meta.get(
                creative_id,
                {
                    "level": "fallback",
                    "keys": {
                        "vertical": row.get("vertical"),
                        "format": row.get("format"),
                    },
                    "size": int(fallback_size.loc[idx])
                    if idx in fallback_size.index
                    else 0,
                },
            )
            health = max(0, min(100, int(round(_safe_float(row.get("health"))))))
            payload = {
                "health": health,
                "status_band": _band_from_health(health),
                "objective_mode": row.get("objective_mode"),
                "kpi_goal": row.get("kpi_goal"),
                "components": components,
                "weights": weights,
                "contributions": contributions,
                "cohort": cohort_meta,
                "raw": {
                    "selected_objective_value": round(
                        _safe_float(row.get("selected_value")), 8
                    ),
                    "credible_interval_width": round(
                        _safe_float(row.get("selected_width")), 8
                    ),
                    "effective_sample_size": round(
                        _safe_float(row.get("effective_sample_size")), 2
                    ),
                    "efficiency_value": round(
                        _safe_float(row.get("efficiency_value")), 8
                    ),
                },
            }
            self.health_by_creative[creative_id] = payload

            detail = self.creative_detail.get(creative_id)
            if detail is not None:
                detail["health"] = health
                detail["status_band"] = payload["status_band"]
                detail["health_components"] = components
                detail["health_breakdown"] = payload

        self.health_diagnostics = _health_diagnostics(s)

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

        num_cols = [
            "text_density",
            "clutter_score",
            "novelty_score",
            "brand_visibility_score",
            "motion_score",
            "readability_score",
        ]
        num_part = df[num_cols].fillna(0.0).clip(0.0, 1.0).to_numpy(dtype=float)

        count_cols = {
            "duration_sec": 30.0,
            "faces_count": 3.0,
            "product_count": 3.0,
            "copy_length_chars": 60.0,
        }
        count_blocks = []
        for col, cap in count_cols.items():
            v = df[col].fillna(0.0).clip(0.0, cap).to_numpy(dtype=float) / cap
            count_blocks.append(v.reshape(-1, 1))
        count_part = (
            np.hstack(count_blocks) if count_blocks else np.zeros((len(df), 0))
        )

        bin_cols = [
            "has_discount_badge",
            "has_ugc_style",
            "has_price",
            "has_gameplay",
        ]
        bin_part = df[bin_cols].fillna(0).to_numpy(dtype=float)

        # Down-weight categoricals (they dominate by sheer dimension count
        # otherwise; numerics are 0–1 across only ~6 cells).
        feature = np.hstack(
            [
                cat_part.to_numpy(dtype=float) * 1.0,
                num_part * 1.5,
                count_part * 1.0,
                bin_part * 1.5,
            ]
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
            advertiser_id_by_creative[int(cid)] = int(
                camp_to_adv.get(int(row["campaign_id"]), -1)
            )

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
                    "dominant_color": row.get("dominant_color")
                    if used_triple
                    else None,
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

        - **health**: evidence-based Q1 composite ∈ [0, 100] from
          components S/C/T/R/E/B.
        - **status_band**: existing bands are preserved:
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
            health_record = self.health_by_creative.get(creative_id, {})
            health = max(0, min(100, int(health_record.get("health") or 0)))
            band = str(health_record.get("status_band") or _band_from_health(health))
            fatigue_day = summary_row.get("fatigue_day")
            fatigue_day_v: int | None = (
                int(fatigue_day)
                if fatigue_day is not None and not pd.isna(fatigue_day)
                else None
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
                "health_components": health_record.get("components"),
                "health_breakdown": health_record,
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
                detail["health_components"] = health_record.get("components")
                detail["health_breakdown"] = health_record

    def _compute_portfolio_aggregates(self) -> None:
        """Roll up KPIs + tab counts once at startup (data is static).

        Tab counts and attention totals come from our Q1 evidence-based
        ``status_band`` assignments. The dataset's ``creative_status`` remains
        a synthetic validation label shown on detail pages and diagnostics, not
        the source of portfolio routing.
        """
        s = self.creative_summary
        total_impressions = int(s["total_impressions"].sum())
        total_clicks = int(s["total_clicks"].sum())
        total_conversions = int(s["total_conversions"].sum())
        total_spend = float(s["total_spend_usd"].sum())
        total_revenue = float(s["total_revenue_usd"].sum())
        band_counts = {"scale": 0, "watch": 0, "rescue": 0, "cut": 0}
        for record in self.health_by_creative.values():
            band = str(record.get("status_band") or "")
            if band in band_counts:
                band_counts[band] += 1
        attention = int(band_counts["rescue"] + band_counts["cut"])

        self.portfolio_kpis = {
            "total_spend_usd": total_spend,
            "total_revenue_usd": total_revenue,
            "roas": (total_revenue / total_spend) if total_spend else 0.0,
            "ctr": (total_clicks / total_impressions) if total_impressions else 0.0,
            "cvr": (total_conversions / total_clicks) if total_clicks else 0.0,
            "attention_count": attention,
        }

        self.tab_counts = {
            "scale": int(band_counts["scale"]),
            "watch": int(band_counts["watch"]),
            "rescue": int(band_counts["rescue"]),
            "cut": int(band_counts["cut"]),
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


_OBJECTIVE_METRIC_COLUMNS = {
    "ctr": "ctr_post",
    "cvr": "cvr_post",
    "roas": "roas_post",
    "cpa": "cpa_inv_post",
}

_OBJECTIVE_WIDTH_COLUMNS = {
    "ctr": "ctr_width",
    "cvr": "cvr_width",
    "roas": "roas_width",
    "cpa": "cpa_width",
}


def _objective_mode(kpi_goal: Any) -> str:
    goal = str(kpi_goal or "").strip().upper()
    if goal == "CTR":
        return "ctr"
    if goal == "ROAS":
        return "roas"
    if goal == "CPA":
        return "cpa"
    # IPM / install / signup style goals are conversion-quality goals in the
    # Q1 four-mode contract, so they use posterior CVR.
    return "cvr"


def _selected_by_objective(row: pd.Series, mapping: dict[str, str]) -> float:
    mode = str(row.get("objective_mode") or "ctr")
    return _safe_float(row.get(mapping.get(mode, mapping["ctr"])))


def _effective_sample_size(row: pd.Series) -> float:
    mode = str(row.get("objective_mode") or "ctr")
    if mode == "ctr":
        return _safe_float(row.get("total_impressions"))
    if mode == "cvr":
        return _safe_float(row.get("total_clicks"))
    if mode == "roas":
        return _safe_float(row.get("total_spend_usd"))
    if mode == "cpa":
        return _safe_float(row.get("total_conversions"))
    return 0.0


def _efficiency_value(row: pd.Series) -> float:
    mode = str(row.get("objective_mode") or "ctr")
    if mode == "cpa":
        return _safe_float(row.get("cpa_inv_post"))
    return _safe_float(row.get("roas_post"))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _robust_normalize(values: pd.Series) -> pd.Series:
    values = values.astype(float).fillna(0.0)
    if values.empty:
        return values
    lo = _safe_float(values.quantile(0.05))
    hi = _safe_float(values.quantile(0.95))
    if hi <= lo:
        return pd.Series(0.5, index=values.index, dtype="float64")
    return ((values - lo) / (hi - lo)).clip(0.0, 1.0).fillna(0.0)


def _normalise_inverse_width(widths: pd.Series) -> pd.Series:
    widths = widths.astype(float).fillna(0.0)
    if widths.empty:
        return widths
    hi = _safe_float(widths.quantile(0.95))
    if hi <= 0.0:
        return pd.Series(1.0, index=widths.index, dtype="float64")
    return (1.0 - (widths / hi)).clip(0.0, 1.0).fillna(0.0)


def _reliability_bonus(effective_n: pd.Series) -> pd.Series:
    effective_n = effective_n.astype(float).clip(lower=0.0).fillna(0.0)
    if effective_n.empty:
        return effective_n
    hi = _safe_float(effective_n.quantile(0.95))
    if hi <= 0.0:
        return pd.Series(0.0, index=effective_n.index, dtype="float64")
    return effective_n.map(lambda v: math.log1p(v) / math.log1p(hi)).clip(0.0, 1.0)


def _trend_component(points: list[dict[str, Any]], mode: str, age_days: int) -> float:
    if age_days < 7 or len(points) < 2:
        return 0.0

    tail = points[-14:] if len(points) >= 14 else points
    midpoint = max(1, len(tail) // 2)
    prior = tail[:midpoint]
    recent = tail[midpoint:]
    if not prior or not recent:
        return 0.0

    prior_v = _window_metric(prior, mode)
    recent_v = _window_metric(recent, mode)
    if prior_v <= 0.0:
        if recent_v <= 0.0:
            return 0.5
        return 1.0

    signed_change = (recent_v - prior_v) / abs(prior_v)
    return _clamp01(0.5 + 0.5 * signed_change)


def _window_metric(points: list[dict[str, Any]], mode: str) -> float:
    impressions = sum(_safe_float(p.get("impressions")) for p in points)
    clicks = sum(_safe_float(p.get("clicks")) for p in points)
    conversions = sum(_safe_float(p.get("conversions")) for p in points)
    spend = sum(_safe_float(p.get("spend_usd")) for p in points)
    revenue = sum(_safe_float(p.get("revenue_usd")) for p in points)

    if mode == "ctr":
        return clicks / impressions if impressions > 0 else 0.0
    if mode == "cvr":
        return conversions / clicks if clicks > 0 else 0.0
    if mode == "roas":
        return revenue / spend if spend > 0 else 0.0
    if mode == "cpa":
        return conversions / spend if spend > 0 else 0.0
    return 0.0


def _primary_cohort_ranks(
    daily: pd.DataFrame,
    creatives: pd.DataFrame,
    summary: pd.DataFrame,
) -> tuple[dict[int, float], dict[int, dict[str, Any]]]:
    seg = daily.groupby(["creative_id", "country", "os"], as_index=False).agg(
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        conversions=("conversions", "sum"),
        spend_usd=("spend_usd", "sum"),
        revenue_usd=("revenue_usd", "sum"),
    )
    meta = creatives[["creative_id", "vertical", "format"]].drop_duplicates()
    seg = seg.merge(meta, on="creative_id", how="left")

    mode_by_creative = summary.set_index("creative_id")["objective_mode"].to_dict()
    seg["objective_mode"] = seg["creative_id"].map(mode_by_creative).fillna("ctr")

    seg["ctr_metric"] = (
        seg["clicks"] / seg["impressions"].where(seg["impressions"] > 0)
    ).fillna(0.0)
    seg["cvr_metric"] = (
        seg["conversions"] / seg["clicks"].where(seg["clicks"] > 0)
    ).fillna(0.0)
    seg["roas_metric"] = (
        seg["revenue_usd"] / seg["spend_usd"].where(seg["spend_usd"] > 0)
    ).fillna(0.0)
    seg["cpa_metric"] = (
        seg["conversions"] / seg["spend_usd"].where(seg["spend_usd"] > 0)
    ).fillna(0.0)

    keys = ["vertical", "format", "country", "os"]
    seg["cohort_size"] = seg.groupby(keys)["creative_id"].transform("nunique")
    seg["rank"] = 0.5
    metric_by_mode = {
        "ctr": "ctr_metric",
        "cvr": "cvr_metric",
        "roas": "roas_metric",
        "cpa": "cpa_metric",
    }
    for mode, metric_col in metric_by_mode.items():
        ranks = seg.groupby(keys)[metric_col].rank(pct=True)
        mask = seg["objective_mode"] == mode
        seg.loc[mask, "rank"] = ranks.loc[mask].fillna(0.5)

    seg["rank_weight"] = seg.apply(_segment_rank_weight, axis=1)
    eligible = seg[seg["cohort_size"] >= 5]

    ranks_out: dict[int, float] = {}
    meta_out: dict[int, dict[str, Any]] = {}
    for creative_id_raw, group in eligible.groupby("creative_id"):
        creative_id = int(creative_id_raw)
        weight_sum = _safe_float(group["rank_weight"].sum())
        if weight_sum > 0:
            rank = _safe_float(
                (group["rank"] * group["rank_weight"]).sum() / weight_sum
            )
        else:
            rank = _safe_float(group["rank"].mean())
        ranks_out[creative_id] = _clamp01(rank)

        first = group.iloc[0]
        meta_out[creative_id] = {
            "level": "primary",
            "keys": {
                "vertical": first.get("vertical"),
                "format": first.get("format"),
                "country": first.get("country"),
                "os": first.get("os"),
            },
            "size": int(group["cohort_size"].max()),
        }

    return ranks_out, meta_out


def _segment_rank_weight(row: pd.Series) -> float:
    mode = str(row.get("objective_mode") or "ctr")
    if mode == "ctr":
        return _safe_float(row.get("impressions"))
    if mode == "cvr":
        return _safe_float(row.get("clicks"))
    if mode == "roas":
        return _safe_float(row.get("spend_usd"))
    if mode == "cpa":
        return _safe_float(row.get("conversions"))
    return 0.0


def _health_diagnostics(summary: pd.DataFrame) -> dict[str, Any]:
    mature = summary[summary["total_days_active"] > 30]
    spearman = 0.0
    top_overlap = 0.0
    if len(mature) >= 2:
        spearman = _safe_float(
            mature["health"].rank().corr(mature["perf_score"].rank())
        )
        top_n = min(50, len(mature))
        health_top = set(mature.nlargest(top_n, "health")["creative_id"].astype(int))
        raw_top = set(mature.nlargest(top_n, "perf_score")["creative_id"].astype(int))
        top_overlap = len(health_top & raw_top) / top_n if top_n else 0.0

    health_values = summary["health"].astype(float).fillna(0.0)
    buckets = {
        "0_20": int(((health_values >= 0) & (health_values < 20)).sum()),
        "20_40": int(((health_values >= 20) & (health_values < 40)).sum()),
        "40_60": int(((health_values >= 40) & (health_values < 60)).sum()),
        "60_80": int(((health_values >= 60) & (health_values < 80)).sum()),
        "80_100": int(((health_values >= 80) & (health_values <= 100)).sum()),
    }

    matrix: dict[str, dict[str, int]] = {}
    for _, row in summary.iterrows():
        predicted = str(row.get("status_band") or "unknown")
        actual = str(row.get("creative_status") or "unknown")
        matrix.setdefault(predicted, {})
        matrix[predicted][actual] = matrix[predicted].get(actual, 0) + 1

    return {
        "ablation": {
            "age_gt_30_count": int(len(mature)),
            "spearman_health_vs_perf_score": round(spearman, 4),
            "top_50_overlap_vs_perf_score": round(top_overlap, 4),
        },
        "distribution": {
            "min": round(_safe_float(health_values.min()), 2),
            "p10": round(_safe_float(health_values.quantile(0.10)), 2),
            "median": round(_safe_float(health_values.median()), 2),
            "p90": round(_safe_float(health_values.quantile(0.90)), 2),
            "max": round(_safe_float(health_values.max()), 2),
            "buckets": buckets,
        },
        "sanity": {
            "confusion_matrix_predicted_band_vs_creative_status": matrix,
        },
    }


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
