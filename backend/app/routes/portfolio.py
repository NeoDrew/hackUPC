from __future__ import annotations

from fastapi import APIRouter

from ..datastore import get_store
from ..schemas import PortfolioKPIs, TabCounts
from ..services import queries

router = APIRouter()


@router.get("/portfolio/kpis", response_model=PortfolioKPIs)
def get_portfolio_kpis() -> dict:
    return queries.portfolio_kpis(get_store())


@router.get("/portfolio/tab-counts", response_model=TabCounts)
def get_tab_counts() -> dict:
    return queries.tab_counts(get_store())
