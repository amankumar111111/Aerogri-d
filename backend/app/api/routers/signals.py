"""Signal management API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.errors import AppError
from app.api.mappers import signal_to_response
from app.api.schemas import ErrorResponse, SignalActionResponse, SignalResponse, SignalStateEnum
from app.domain.value_objects import SignalState

router = APIRouter(prefix="/signals", tags=["signals"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid signal ID format"},
    404: {"model": ErrorResponse, "description": "Signal not found"},
}


@router.get(
    "",
    response_model=list[SignalResponse],
    summary="List signals",
    description="List signals with optional state filter, paginated.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
    },
)
async def list_signals(
    request: Request,
    state: SignalStateEnum | None = Query(None, description="Filter by state: watch, probable_hotspot, high_confidence, archived"),
    offset: int = Query(0, ge=0, description="Pagination offset (number of signals to skip)"),
    limit: int = Query(20, ge=1, le=100, description="Page size (1–100, default 20)"),
) -> list[SignalResponse]:
    from app.infrastructure.repositories import SQLAlchemySignalStore

    session = request.app.state.db_session
    store = SQLAlchemySignalStore(session)
    signals = await store.list_(state=state.value if state else None, offset=offset, limit=limit)
    return [signal_to_response(s) for s in signals]


@router.get(
    "/{signal_id}",
    response_model=SignalResponse,
    summary="Get signal detail",
    description="Retrieve a signal with full detail including contributions and environmental context.",
    responses=_ERROR_RESPONSES,
)
async def get_signal(signal_id: str, request: Request) -> SignalResponse:
    from app.infrastructure.repositories import SQLAlchemySignalStore

    session = request.app.state.db_session
    store = SQLAlchemySignalStore(session)
    signal = await store.get(signal_id)

    if not signal:
        raise AppError(code="NOT_FOUND", message=f"Signal {signal_id} not found", status_code=404)

    return signal_to_response(signal)


@router.post(
    "/{signal_id}/verify",
    response_model=SignalActionResponse,
    summary="Verify signal (field verified)",
    description="Mark a signal as field-verified. Transitions to Archived state. Returns the updated signal state.",
    responses=_ERROR_RESPONSES,
)
async def verify_signal(signal_id: str, request: Request) -> SignalActionResponse:
    from app.infrastructure.repositories import SQLAlchemySignalStore

    session = request.app.state.db_session
    store = SQLAlchemySignalStore(session)
    signal = await store.get(signal_id)

    if not signal:
        raise AppError(code="NOT_FOUND", message=f"Signal {signal_id} not found", status_code=404)

    signal.state = SignalState.ARCHIVED
    await store.save(signal)

    return SignalActionResponse(
        signal_id=signal_id,
        state=signal.state.value,
        message="Signal verified and archived",
    )


@router.post(
    "/{signal_id}/archive",
    response_model=SignalActionResponse,
    summary="Archive signal",
    description="Manually archive a signal. Returns the updated signal state.",
    responses=_ERROR_RESPONSES,
)
async def archive_signal(signal_id: str, request: Request) -> SignalActionResponse:
    from app.infrastructure.repositories import SQLAlchemySignalStore

    session = request.app.state.db_session
    store = SQLAlchemySignalStore(session)
    signal = await store.get(signal_id)

    if not signal:
        raise AppError(code="NOT_FOUND", message=f"Signal {signal_id} not found", status_code=404)

    signal.state = SignalState.ARCHIVED
    await store.save(signal)

    return SignalActionResponse(
        signal_id=signal_id,
        state=signal.state.value,
        message="Signal archived",
    )
