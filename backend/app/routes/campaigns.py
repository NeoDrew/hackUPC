from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..datastore import get_store
from ..schemas import Campaign, CreativeListItem
from ..services import queries

router = APIRouter()


@router.get("/campaigns/{campaign_id}", response_model=Campaign)
def get_campaign(campaign_id: int) -> dict:
    campaign = queries.get_campaign(get_store(), campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="campaign not found")
    return campaign


@router.get(
    "/campaigns/{campaign_id}/creatives",
    response_model=list[CreativeListItem],
)
def list_creatives(campaign_id: int) -> list[dict]:
    if queries.get_campaign(get_store(), campaign_id) is None:
        raise HTTPException(status_code=404, detail="campaign not found")
    return queries.list_creatives_for_campaign(get_store(), campaign_id)
