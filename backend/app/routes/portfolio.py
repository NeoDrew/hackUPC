from __future__ import annotations

from fastapi import APIRouter, Query

from ..datastore import get_store
from ..schemas import HealthDiagnostics, PortfolioKPIs, SearchResponse, TabCounts
from ..services import queries, windowed

router = APIRouter()


@router.get("/portfolio/kpis", response_model=PortfolioKPIs)
def get_portfolio_kpis(
    start: str | None = Query(default=None, description="ISO date YYYY-MM-DD"),
    end: str | None = Query(default=None, description="ISO date YYYY-MM-DD"),
    advertiser_id: int | None = Query(
        default=None,
        description="Scope KPIs to one advertiser; cohort math elsewhere stays portfolio-wide.",
    ),
    campaign_id: int | None = Query(
        default=None,
        description="Scope KPIs to one campaign. Wins over advertiser_id when both are present.",
    ),
) -> dict:
    return queries.portfolio_kpis(
        get_store(),
        start=start,
        end=end,
        advertiser_id=advertiser_id,
        campaign_id=campaign_id,
    )


@router.get("/portfolio/tab-counts", response_model=TabCounts)
def get_tab_counts(
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    advertiser_id: int | None = Query(default=None),
    campaign_id: int | None = Query(default=None),
) -> dict:
    return queries.tab_counts(
        get_store(),
        start=start,
        end=end,
        advertiser_id=advertiser_id,
        campaign_id=campaign_id,
    )


@router.get("/portfolio/dataset-bounds")
def get_dataset_bounds() -> dict:
    """Returns the dataset's date range so the frontend can map a 'week N'
    selection to a concrete (start, end) window. Total weeks is ceil(days/7).
    """
    start, end = windowed.dataset_bounds(get_store())
    from datetime import date as _d

    s = _d.fromisoformat(start)
    e = _d.fromisoformat(end)
    days = (e - s).days + 1
    weeks = (days + 6) // 7
    return {
        "start": start,
        "end": end,
        "total_days": days,
        "total_weeks": weeks,
    }


@router.get("/portfolio/health-diagnostics", response_model=HealthDiagnostics)
def get_health_diagnostics() -> dict:
    return queries.health_diagnostics(get_store())


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=8, ge=1, le=20),
) -> dict:
    hits = queries.search_creatives(get_store(), q, limit=limit)
    return {"query": q, "hits": hits}
