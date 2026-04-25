from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..datastore import get_store
from ..schemas import Advertiser, Campaign
from ..services import queries

router = APIRouter()


@router.get("/advertisers", response_model=list[Advertiser])
def list_advertisers() -> list[dict]:
    return queries.list_advertisers(get_store())


@router.get("/advertisers/{advertiser_id}", response_model=Advertiser)
def get_advertiser(advertiser_id: int) -> dict:
    advertiser = queries.get_advertiser(get_store(), advertiser_id)
    if advertiser is None:
        raise HTTPException(status_code=404, detail="advertiser not found")
    return advertiser


@router.get(
    "/advertisers/{advertiser_id}/campaigns",
    response_model=list[Campaign],
)
def list_campaigns(advertiser_id: int) -> list[dict]:
    if queries.get_advertiser(get_store(), advertiser_id) is None:
        raise HTTPException(status_code=404, detail="advertiser not found")
    return queries.list_campaigns_for_advertiser(get_store(), advertiser_id)
