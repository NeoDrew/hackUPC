from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..datastore import get_store
from ..schemas import CreativeDetail, CreativeRow, CreativeTimeseries, TwinSummary
from ..services import queries

router = APIRouter()


@router.get("/creatives", response_model=list[CreativeRow])
def list_creatives_flat(
    tab: str | None = Query(default=None, description="scale|watch|rescue|cut|explore"),
    status: str | None = Query(default=None),
    vertical: str | None = Query(default=None),
    format: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    desc: bool = Query(default=True),
    limit: int | None = Query(default=None, ge=1, le=2000),
) -> list[dict]:
    return queries.list_creatives_flat(
        get_store(),
        tab=tab,
        status=status,
        vertical=vertical,
        format=format,
        sort=sort,
        desc=desc,
        limit=limit,
    )


@router.get("/creatives/{creative_id}", response_model=CreativeDetail)
def get_creative(creative_id: int) -> dict:
    detail = queries.get_creative_detail(get_store(), creative_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="creative not found")
    return detail


@router.get(
    "/creatives/{creative_id}/timeseries",
    response_model=CreativeTimeseries,
)
def get_timeseries(creative_id: int) -> dict:
    timeseries = queries.get_creative_timeseries(get_store(), creative_id)
    if timeseries is None:
        raise HTTPException(status_code=404, detail="creative not found")
    return timeseries


@router.get(
    "/creatives/{creative_id}/twin",
    response_model=TwinSummary,
)
def get_twin(creative_id: int) -> dict:
    twin = queries.get_twin_stub(get_store(), creative_id)
    if twin is None:
        raise HTTPException(
            status_code=404, detail="no cohort-leader twin found"
        )
    return twin
