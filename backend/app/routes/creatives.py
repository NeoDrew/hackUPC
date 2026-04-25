from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..datastore import get_store
from ..schemas import (
    CreativeDetail,
    CreativeListResponse,
    CreativeTimeseries,
    TwinSummary,
    VariantBriefResponse,
    WinningPatternsResponse,
)
from ..services import queries

router = APIRouter()


@router.get("/creatives", response_model=CreativeListResponse)
def list_creatives_flat(
    tab: str | None = Query(default=None, description="scale|watch|rescue|cut|explore"),
    status: str | None = Query(default=None),
    vertical: str | None = Query(default=None),
    format: str | None = Query(default=None),
    theme: str | None = Query(default=None),
    hook_type: str | None = Query(default=None),
    country: str | None = Query(default=None, description="ISO country code, e.g. US, GB, DE"),
    os: str | None = Query(default=None, description="Android, iOS, or Both"),
    band: str | None = Query(default=None, description="scale|watch|rescue|cut"),
    sort: str | None = Query(default=None),
    desc: bool = Query(default=True),
    limit: int | None = Query(default=100, ge=1, le=2000),
    start: str | None = Query(default=None, description="ISO date YYYY-MM-DD"),
    end: str | None = Query(default=None, description="ISO date YYYY-MM-DD"),
) -> dict:
    return queries.list_creatives_flat(
        get_store(),
        tab=tab,
        status=status,
        vertical=vertical,
        format=format,
        theme=theme,
        hook_type=hook_type,
        country=country,
        os=os,
        band=band,
        sort=sort,
        desc=desc,
        limit=limit,
        start=start,
        end=end,
    )


@router.get("/creatives/{creative_id}", response_model=CreativeDetail)
def get_creative(
    creative_id: int,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
) -> dict:
    detail = queries.get_creative_detail(get_store(), creative_id, start=start, end=end)
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
async def get_twin(
    creative_id: int,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
) -> dict:
    twin = await queries.get_twin_stub(get_store(), creative_id, start=start, end=end)
    if twin is None:
        raise HTTPException(
            status_code=404, detail="no cohort-leader twin found"
        )
    return twin


@router.get(
    "/creatives/{creative_id}/variant-brief",
    response_model=VariantBriefResponse,
)
async def get_variant_brief(creative_id: int) -> dict:
    brief = await queries.get_variant_brief(get_store(), creative_id)
    if brief is None:
        raise HTTPException(
            status_code=404, detail="no twin available — can't generate variant brief"
        )
    return brief


@router.get(
    "/creatives/{creative_id}/winning-patterns",
    response_model=WinningPatternsResponse,
)
def get_winning_patterns(creative_id: int) -> dict:
    return queries.winning_patterns(get_store(), creative_id)
