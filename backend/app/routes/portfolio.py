from __future__ import annotations

from fastapi import APIRouter, Query

from ..datastore import get_store
from ..schemas import PortfolioKPIs, SearchResponse, TabCounts
from ..services import queries

router = APIRouter()


@router.get("/portfolio/kpis", response_model=PortfolioKPIs)
def get_portfolio_kpis(
    start: str | None = Query(default=None, description="ISO date YYYY-MM-DD"),
    end: str | None = Query(default=None, description="ISO date YYYY-MM-DD"),
) -> dict:
    return queries.portfolio_kpis(get_store(), start=start, end=end)


@router.get("/portfolio/tab-counts", response_model=TabCounts)
def get_tab_counts(
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
) -> dict:
    return queries.tab_counts(get_store(), start=start, end=end)


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=8, ge=1, le=20),
) -> dict:
    hits = queries.search_creatives(get_store(), q, limit=limit)
    return {"query": q, "hits": hits}
