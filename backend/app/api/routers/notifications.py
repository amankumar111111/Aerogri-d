"""Notification API — SSE stream for real-time in-app notifications."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "/stream",
    summary="Stream real-time notifications",
    description="Server-Sent Events stream for in-app notifications. Connect to receive real-time signal escalation alerts.",
)
async def notification_stream(request: Request):
    async def event_generator():
        event_bus = request.app.state.event_bus
        yield f"data: {json.dumps({'type': 'connected', 'message': 'Notification stream active'})}\n\n"

        async for event in event_bus.subscribe("Notification"):
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "",
    summary="Get recent notifications",
    description="Returns the last 50 notifications.",
)
async def get_notifications(request: Request) -> list[dict]:
    event_bus = request.app.state.event_bus
    if hasattr(event_bus, "get_history"):
        events = await event_bus.get_history("Notification", limit=50)
        return [e.get("payload", e) for e in events]
    return []
