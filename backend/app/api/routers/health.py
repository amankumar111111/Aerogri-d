"""Health and readiness API routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from app.api.schemas import HealthResponse, MetricsResponse, ReadinessResponse

_start_time = time.monotonic()

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service health status.",
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="Returns service readiness including dependency health.",
)
async def ready(request: Request) -> ReadinessResponse:
    db_status = "ok"
    redis_status = "ok"

    try:
        from sqlalchemy import text

        session = request.app.state.db_session
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"

    return ReadinessResponse(
        status="ready" if db_status == "ok" else "degraded",
        database=db_status,
        redis=redis_status,
    )


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Service metrics",
    description="Returns basic operational metrics.",
)
async def metrics(request: Request) -> MetricsResponse:
    from sqlalchemy import func, select

    from app.infrastructure.db import ObservationRow, SignalRow

    session = request.app.state.db_session

    obs_count = (await session.execute(select(func.count(ObservationRow.id)))).scalar_one()
    signal_count = (await session.execute(select(func.count(SignalRow.id)))).scalar_one()

    state_counts: dict[str, int] = {}
    for state_val in ["watch", "probable_hotspot", "high_confidence", "archived"]:
        count = (
            await session.execute(
                select(func.count(SignalRow.id)).where(SignalRow.state == state_val)
            )
        ).scalar_one()
        state_counts[state_val] = count

    return MetricsResponse(
        observations_total=obs_count,
        signals_total=signal_count,
        signals_by_state=state_counts,
        uptime_seconds=time.monotonic() - _start_time,
    )
