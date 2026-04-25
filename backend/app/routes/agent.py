from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agents import orchestrator
from ..datastore import get_store

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: dict[str, Any] | None = None


@router.post("/agent/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    store = get_store()
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    async def event_stream():
        async for chunk in orchestrator.stream_chat(
            store=store, messages=messages, context=req.context
        ):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/agent/status")
def status() -> dict[str, Any]:
    return {"configured": orchestrator.is_configured()}
