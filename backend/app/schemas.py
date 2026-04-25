from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class Advertiser(BaseModel):
    advertiser_id: int
    advertiser_name: str
    vertical: str
    hq_region: str


class Campaign(BaseModel):
    model_config = ConfigDict(extra="ignore")

    campaign_id: int
    advertiser_id: int
    advertiser_name: str
    app_name: str
    vertical: str
    objective: str
    primary_theme: str
    target_age_segment: str
    target_os: str
    countries: str
    country_list: list[str]
    start_date: str
    end_date: str
    daily_budget_usd: float
    kpi_goal: str


QuadrantLabel = str  # "top-performer" | "clickbait-risk" | "niche-converter" | "below-peers" | "unknown"


class CohortKeys(BaseModel):
    vertical: str
    format: str


class Quadrant(BaseModel):
    """Diagnostic position of a creative in CTR×CVR space, relative to its
    cohort. Cohort = (vertical, format). Percentiles are raw; they will be
    Bayesian-shrunk once Q1 ranking ships, so low-sample creatives no longer
    distort the picture.
    """

    ctr_percentile: float | None
    cvr_percentile: float | None
    quadrant_label: QuadrantLabel
    cohort_keys: CohortKeys
    cohort_size: int


class SaturationTriple(BaseModel):
    theme: str | None
    hook_type: str | None
    dominant_color: str | None


class Saturation(BaseModel):
    """Portfolio-saturation signal: how many creatives in the same advertiser
    portfolio share this attribute combo. Triple = (theme, hook_type,
    dominant_color); falls back to (theme, hook_type) if the triple cohort is
    too sparse (see ``used_triple``).
    """

    triple: SaturationTriple
    used_triple: bool
    cohort_advertiser_size: int
    cohort_global_size: int
    cohort_avg_ctr: float
    cohort_avg_cvr: float
    this_ctr: float
    this_cvr: float
    recommend_consolidate_to: int | None = None


class CreativeListItem(BaseModel):
    creative_id: int
    campaign_id: int
    advertiser_name: str
    vertical: str
    format: str
    theme: str
    creative_status: str | None = None
    asset_file: str


class CreativeDetail(BaseModel):
    """Full creative metadata joined with creative_summary on creative_id.

    The shape mirrors every column in creatives.csv plus every column in
    creative_summary.csv that isn't already on creatives.csv. Fields beyond
    the explicitly named ones flow through via `extra="allow"` so the frontend
    can render every metadata column without the schema lagging the data.
    """

    model_config = ConfigDict(extra="allow")

    creative_id: int
    campaign_id: int
    asset_file: str
    quadrant: Quadrant | None = None
    saturation: Saturation | None = None
    health: int | None = None
    status_band: str | None = None


class TimeseriesPoint(BaseModel):
    date: str
    impressions: int
    clicks: int
    conversions: int
    spend_usd: float
    revenue_usd: float


class CreativeTimeseries(BaseModel):
    creative_id: int
    points: list[TimeseriesPoint]


# --- Cockpit / portfolio shapes ---


class PortfolioKPIs(BaseModel):
    total_spend_usd: float
    total_revenue_usd: float
    roas: float
    ctr: float
    cvr: float
    attention_count: int


class TabCounts(BaseModel):
    scale: int
    watch: int
    rescue: int
    cut: int
    explore: int


class CreativeRow(BaseModel):
    creative_id: int
    campaign_id: int
    advertiser_name: str
    headline: str
    vertical: str
    format: str
    status: str | None
    status_band: str | None
    ctr: float
    cvr: float
    roas: float
    spend_usd: float
    impressions: int
    clicks: int
    conversions: int
    revenue_usd: float
    days_active: int
    health: int
    sparkline: list[float]
    fatigue_day: int | None = None
    asset_file: str


class SearchHit(BaseModel):
    creative_id: int
    headline: str | None = None
    advertiser_name: str | None = None
    vertical: str | None = None
    format: str | None = None
    status: str | None = None
    status_band: str | None = None
    health: int | None = None
    asset_file: str | None = None
    theme: str | None = None
    hook_type: str | None = None
    score: float


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


class CreativeListResponse(BaseModel):
    """Paginated wrapper for ``/api/creatives``. Total reflects the count
    *after filters but before limit*, so callers can render a
    "showing X of Y" footer.
    """

    rows: list[CreativeRow]
    total: int
    limit: int | None = None


# --- Twin (stub) ---


class TwinDiff(BaseModel):
    field: str
    source_value: Any
    twin_value: Any
    direction: str  # "pos" | "neg" | "neu"
    impact: str  # "low" | "medium" | "high"


class TwinSegment(BaseModel):
    vertical: str
    format: str


class VisionInsight(BaseModel):
    headline: str
    body: str
    confidence: float


class TwinSummary(BaseModel):
    fatigued_id: int
    winner_id: int
    similarity: float
    segment: TwinSegment
    diffs: list[TwinDiff]
    vision_insight: VisionInsight
    is_stub: bool = True


def to_jsonable(record: dict[str, Any]) -> dict[str, Any]:
    """Pydantic's native serialisation rejects pandas Timestamps; pre-stringify them.

    Keys with ``Timestamp`` values are converted to ISO date strings; everything
    else is left untouched so pydantic can validate it normally.
    """
    out: dict[str, Any] = {}
    for k, v in record.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out
