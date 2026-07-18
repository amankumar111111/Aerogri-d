"""Analytics API routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request

from app.api.schemas import AnalyticsSummary, ErrorResponse, HeatmapPoint, TimelineEntry

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "",
    response_model=AnalyticsSummary,
    summary="Get analytics summary",
    description="Returns aggregate statistics: total observations, signals by state, average confidence.",
    responses={
        500: {"model": ErrorResponse, "description": "Database query failed"},
    },
)
async def get_analytics(request: Request) -> AnalyticsSummary:
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

    avg_conf = (
        await session.execute(select(func.coalesce(func.avg(SignalRow.confidence_value), 0.0)))
    ).scalar_one()

    return AnalyticsSummary(
        total_observations=obs_count,
        total_signals=signal_count,
        active_signals=signal_count - state_counts.get("archived", 0),
        high_confidence_signals=state_counts.get("high_confidence", 0),
        avg_confidence=float(avg_conf),
        signals_by_state=state_counts,
    )


@router.get(
    "/heatmap",
    response_model=list[HeatmapPoint],
    summary="Get signal heatmap",
    description="Returns signal locations with intensity for map overlay. Max 500 points.",
    responses={
        500: {"model": ErrorResponse, "description": "Database query failed"},
    },
)
async def get_heatmap(request: Request) -> list[HeatmapPoint]:
    from sqlalchemy import func, select

    from app.infrastructure.db import SignalRow

    session = request.app.state.db_session

    result = await session.execute(
        select(
            SignalRow.location_lat,
            SignalRow.location_lng,
            func.count(SignalRow.id).label("count"),
            func.max(SignalRow.state).label("dominant_state"),
        )
        .group_by(SignalRow.location_lat, SignalRow.location_lng)
        .order_by(func.count(SignalRow.id).desc())
        .limit(500)
    )

    return [
        HeatmapPoint(
            latitude=row.location_lat,
            longitude=row.location_lng,
            intensity=min(1.0, row.count / 10.0),
            signal_count=row.count,
            dominant_state=row.dominant_state,
        )
        for row in result.all()
    ]


@router.get(
    "/timeline",
    response_model=list[TimelineEntry],
    summary="Get signal timeline",
    description="Returns the 50 most recent signal state changes.",
    responses={
        500: {"model": ErrorResponse, "description": "Database query failed"},
    },
)
async def get_timeline(request: Request) -> list[TimelineEntry]:
    from sqlalchemy import select

    from app.infrastructure.db import SignalRow

    session = request.app.state.db_session

    result = await session.execute(
        select(SignalRow)
        .order_by(SignalRow.updated_at.desc())
        .limit(50)
    )

    return [
        TimelineEntry(
            signal_id=row.id,
            state=row.state,
            composite_score=row.confidence_value,
            observation_count=len(json.loads(row.contributing_observation_ids)) if row.contributing_observation_ids else 0,
            timestamp=row.updated_at.isoformat(),
        )
        for row in result.scalars().all()
    ]
