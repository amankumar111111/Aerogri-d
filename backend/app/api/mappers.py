"""Domain entity → Response DTO mappers. Never expose database models."""

from __future__ import annotations

from app.api.schemas import (
    ContributionResponse,
    InterpretationResponse,
    ObservationResponse,
    SignalResponse,
)
from app.domain.entities import Interpretation, Observation, Signal
from app.domain.value_objects import SignalState


def observation_to_response(obs: Observation) -> ObservationResponse:
    return ObservationResponse(
        id=obs.id,
        fingerprint=obs.fingerprint.hash if obs.fingerprint else None,
        content=obs.content,
        category=obs.category,
        language=obs.language,
        latitude=obs.location.latitude,
        longitude=obs.location.longitude,
        status=obs.status,
        created_at=obs.created_at.isoformat(),
        interpreted_at=obs.interpreted_at.isoformat() if obs.interpreted_at else None,
    )


def interpretation_to_response(interp: Interpretation) -> InterpretationResponse:
    return InterpretationResponse(
        id=interp.id,
        observation_id=interp.observation_id,
        model=interp.model,
        prompt_version=interp.prompt_version,
        schema_version=interp.schema_version,
        categories=interp.categories,
        evidence_descriptions=interp.evidence_descriptions,
        severity_level=interp.severity.level.value if interp.severity else None,
        citizen_category_alignment=interp.citizen_category_alignment,
        confidence_score=interp.confidence_score,
        created_at=interp.created_at.isoformat(),
    )


def signal_to_response(signal: Signal) -> SignalResponse:
    contributions = [
        ContributionResponse(
            observation_id=c.observation_id,
            fingerprint=c.fingerprint,
            dimension_scores=c.dimension_scores,
            contribution_score=c.contribution_score,
            weighted_contribution=c.weighted_contribution,
            evaluation_timestamp=c.evaluation_timestamp.isoformat(),
        )
        for c in signal.contributions
    ]

    return SignalResponse(
        id=signal.id,
        state=signal.state.value,
        latitude=signal.location.latitude,
        longitude=signal.location.longitude,
        category=signal.category,
        confidence_value=signal.confidence.value,
        contributing_observation_ids=signal.contributing_observation_ids,
        contributions=contributions,
        environmental_context=signal.environmental_context,
        version=signal.version,
        created_at=signal.created_at.isoformat(),
        updated_at=signal.updated_at.isoformat(),
        archived_at=signal.archived_at.isoformat() if signal.archived_at else None,
    )
