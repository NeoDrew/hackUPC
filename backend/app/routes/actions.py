"""Mutation endpoints for the apply-variant flow.

The dataset is read-only, so these endpoints don't *actually* change any
ad. They write to a process-lifetime queue on the Datastore so the UI can
render a "queued for review" banner and the agent can offer an undo. The
queue clears on service restart — acceptable for the demo.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..datastore import get_store
from ..schemas import AppliedVariant, ApplyRequest, ApplyResponse
from ..services import queries

router = APIRouter()


@router.post(
    "/creatives/{creative_id}/apply-variant", response_model=ApplyResponse
)
def apply_variant(creative_id: int, body: ApplyRequest | None = None) -> dict:
    rationale = body.rationale if body else None
    return queries.queue_variant(get_store(), creative_id, rationale)


@router.delete(
    "/creatives/{creative_id}/apply-variant", response_model=ApplyResponse
)
def undo_variant(creative_id: int) -> dict:
    return queries.dequeue_variant(get_store(), creative_id)


@router.get("/applied-variants", response_model=list[AppliedVariant])
def list_applied() -> list[dict]:
    return queries.list_applied_variants(get_store())
