from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class Advertiser(BaseModel):
    advertiser_id: int
    advertiser_name: str
    vertical: str
    hq_region: str


class CampaignHealthComponents(BaseModel):
    pct_fatigued: float
    mean_drop_ratio: float
    agg_ctr_cv: float
    cohort_rank_pct: float
    creative_count: int
    fatigued_count: int


class CampaignMetrics(BaseModel):
    """Per-campaign rollup attached to ``Campaign`` when ``with_metrics=true``.
    Reuses the advertiser-scope aggregator so totals always reconcile.
    """

    model_config = ConfigDict(extra="ignore")

    total_spend_usd: float
    total_revenue_usd: float
    roas: float
    ctr: float
    cvr: float
    attention_count: int
    creative_count: int
    scale: int
    watch: int
    rescue: int
    cut: int
    health: int
    health_components: CampaignHealthComponents
    health_weights: dict[str, float] | None = None


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
    metrics: CampaignMetrics | None = None


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


class HealthComponents(BaseModel):
    """Q1 evidence-based health metric components, each clamped to [0, 1].

    S = posterior strength, C = confidence, T = trend, R = cohort rank,
    E = efficiency, B = reliability bonus.
    """

    S: float
    C: float
    T: float
    R: float
    E: float
    B: float


class HealthBreakdown(BaseModel):
    """Transparent payload behind the 0-100 Q1 health score.

    ``components`` contains the six normalized inputs; ``weights`` and
    ``contributions`` make the frontend explanation deterministic.
    """

    model_config = ConfigDict(extra="allow")

    health: int
    status_band: str
    objective_mode: str
    kpi_goal: str | None = None
    components: HealthComponents
    weights: dict[str, float]
    contributions: dict[str, float]
    cohort: dict[str, Any]
    raw: dict[str, Any]


class HealthDiagnostics(BaseModel):
    """Startup validation checks for Q1 before UI rollout."""

    model_config = ConfigDict(extra="allow")

    ablation: dict[str, Any]
    distribution: dict[str, Any]
    sanity: dict[str, Any]


class CreativeListItem(BaseModel):
    creative_id: int
    campaign_id: int
    advertiser_name: str
    vertical: str
    format: str
    theme: str
    creative_status: str | None = None
    asset_file: str


class PredictedFatigue(BaseModel):
    """Our own fatigue verdict for a creative, computed from the daily
    impressions / clicks time series — isotonic regression + Ruptures
    changepoint detection + Beta-binomial significance test.

    The dataset's ``creative_status`` and ``fatigue_day`` columns are NOT
    inputs here; they remain reserved as ground-truth labels for
    validation. This is the prediction we surface in the UI.
    """

    is_fatigued: bool
    predicted_fatigue_day: int | None = None
    predicted_fatigue_date: str | None = None
    fatigue_ctr_drop: float | None = None
    p_value: float | None = None
    is_significant: bool = False
    pre_ctr: float | None = None
    post_ctr: float | None = None
    cohort_first_median: float | None = None
    cohort_last_p25: float | None = None
    model_score: float | None = None


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
    health_components: HealthComponents | None = None
    health_breakdown: HealthBreakdown | None = None
    predicted_fatigue: PredictedFatigue | None = None


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
    # Daily series spanning the active window (or full dataset if no window).
    # Used to render the sparkline at the bottom of each KPI tile. Empty list
    # is acceptable (UI degrades gracefully).
    spend_series: list[float] = []
    ctr_series: list[float] = []
    cvr_series: list[float] = []
    roas_series: list[float] = []


class TabCounts(BaseModel):
    scale: int
    watch: int
    rescue: int
    cut: int
    explore: int


class CreativeRow(BaseModel):
    creative_id: int
    campaign_id: int
    advertiser_id: int | None = None
    advertiser_name: str
    headline: str
    vertical: str
    format: str
    theme: str | None = None
    hook_type: str | None = None
    countries: list[str] = []
    target_os: str | None = None
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
    health_components: HealthComponents | None = None
    health_breakdown: HealthBreakdown | None = None
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


# --- Apply-variant queue ---


class ApplyRequest(BaseModel):
    rationale: str | None = None


class AppliedVariant(BaseModel):
    """A queued variant application. The dataset is read-only, so this is a
    process-lifetime queue — the entry stays until the user undoes it or the
    service restarts. Carried purely so the UI can render a "queued" banner
    and let the user undo without losing what they applied.
    """

    creative_id: int
    rationale: str | None = None
    queued_at: str  # ISO 8601
    eta_hours: int = 24


class ApplyResponse(BaseModel):
    creative_id: int
    queued: bool
    entry: AppliedVariant | None = None


# --- Variant brief (Gemma-generated) ---


class WinningPattern(BaseModel):
    """One row in the cohort attribute prevalence table — a real,
    deterministic count over the (vertical, format) cohort. No LLM."""

    trait: str
    what: str
    lift_pct: float
    prevalence_pct: float
    winner_count: int


class WinningPatternsResponse(BaseModel):
    creative_id: int
    segment: dict[str, str]
    cohort_size: int = 0
    winner_count: int = 0
    patterns: list[WinningPattern]


class VariantBriefResponse(BaseModel):
    """Brief for the next ad creative — generated by Gemma 4 from the
    source/winner/diff context. Falls back to a deterministic template
    keyed on the winner's metadata when the LLM is unavailable; in that
    case ``is_stub`` is True and the UI keeps a [preview] chip.
    """

    creative_id: int
    winner_id: int
    segment: dict[str, str]
    headline: str
    subhead: str
    cta: str
    dominant_color: str
    emotional_tone: str
    rationale: list[str]
    is_stub: bool = False


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
