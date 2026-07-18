"""Citizen observation API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.errors import AppError
from app.api.mappers import observation_to_response
from app.api.schemas import ErrorResponse, ObservationResponse, ObservationSubmitRequest, ObservationSubmitResponse
from app.application.submit_observation import SubmitObservationRequest, SubmitObservationUseCase

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post(
    "",
    response_model=ObservationSubmitResponse,
    status_code=201,
    summary="Submit a new observation",
    description="Submit a citizen observation with photo, voice, text, and GPS. Returns a tracking reference and observation ID.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid observation data"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        422: {"description": "Validation error (see HTTPValidationError)"},
    },
)
async def submit_observation(
    body: ObservationSubmitRequest,
    request: Request,
) -> ObservationSubmitResponse:
    use_case: SubmitObservationUseCase = request.app.state.submit_observation_uc

    try:
        result = await use_case.execute(
            SubmitObservationRequest(
                content=body.content,
                latitude=body.latitude,
                longitude=body.longitude,
                category=body.category.value,
                language=body.language.value,
                device_id=body.device_id,
            )
        )
    except ValueError as e:
        raise AppError(code="INVALID_OBSERVATION", message=str(e), status_code=400)

    return ObservationSubmitResponse(
        observation_id=result.observation_id,
        fingerprint=result.fingerprint,
        status=result.status,
        tracking_ref=result.observation_id[:8],
    )


@router.get(
    "/{observation_id}",
    response_model=ObservationResponse,
    summary="Get observation by ID",
    description="Retrieve a previously submitted observation by its UUID.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid observation ID format"},
        404: {"model": ErrorResponse, "description": "Observation not found"},
    },
)
async def get_observation(observation_id: str, request: Request) -> ObservationResponse:
    from app.infrastructure.repositories import SQLAlchemyObservationStore

    session = request.app.state.db_session
    store = SQLAlchemyObservationStore(session)
    obs = await store.get(observation_id)

    if not obs:
        raise AppError(code="NOT_FOUND", message=f"Observation {observation_id} not found", status_code=404)

    return observation_to_response(obs)
