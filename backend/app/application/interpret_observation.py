"""Use case: Interpret a submitted observation via Gemini."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.entities import AuditEvent, Interpretation, Observation
from app.domain.ports import (
    AuditLog,
    EventBus,
    InterpretationStore,
    MediaStore,
    ObservationInterpreter,
    ObservationStore,
)
from app.domain.value_objects import Severity, SeverityLevel


@dataclass
class InterpretRequest:
    observation_id: str


@dataclass
class InterpretResponse:
    interpretation_id: str
    categories: list[str]
    severity: str
    confidence: float
    alignment: bool
    prompt_version: str
    schema_version: str


async def _load_media(observation: Observation, media_store: MediaStore | None) -> tuple[bytes | None, bytes | None]:
    """Load image and voice bytes from media storage."""
    image_bytes = None
    voice_bytes = None
    if media_store:
        if observation.photo_uri:
            image_bytes = await media_store.get(observation.photo_uri)
        if observation.voice_uri:
            voice_bytes = await media_store.get(observation.voice_uri)
    return image_bytes, voice_bytes


def _parse_severity(result: dict) -> Severity:
    """Parse severity from Gemini response."""
    severity_data = result.get("severity", {})
    return Severity(
        level=SeverityLevel(severity_data.get("level", "low")),
        indicators=tuple(severity_data.get("indicators", [])),
    )


def _build_interpretation(observation: Observation, result: dict, meta: dict) -> Interpretation:
    """Build an Interpretation entity from Gemini response."""
    return Interpretation(
        observation_id=observation.id,
        model=meta.get("model", "gemini-2.0-flash"),
        prompt_version=meta.get("prompt_version", "v3.2"),
        schema_version=meta.get("schema_version", "v2.1"),
        categories=result.get("categories", []),
        evidence_descriptions=result.get("evidence_descriptions", []),
        severity=_parse_severity(result),
        citizen_category_alignment=result.get("citizen_category_alignment", False),
        confidence_score=result.get("confidence", 0.0),
        created_at=datetime.now(timezone.utc),
    )


class InterpretObservationUseCase:
    def __init__(
        self,
        observation_store: ObservationStore,
        interpretation_store: InterpretationStore,
        interpreter: ObservationInterpreter,
        audit_log: AuditLog,
        event_bus: EventBus,
        media_store: MediaStore | None = None,
    ) -> None:
        self.observation_store = observation_store
        self.interpretation_store = interpretation_store
        self.interpreter = interpreter
        self.audit_log = audit_log
        self.event_bus = event_bus
        self.media_store = media_store

    async def execute(self, request: InterpretRequest) -> InterpretResponse:
        observation = await self.observation_store.get(request.observation_id)
        if not observation:
            raise ValueError(f"Observation {request.observation_id} not found")

        image_bytes, voice_bytes = await _load_media(observation, self.media_store)

        result = await self.interpreter.interpret(
            image_bytes=image_bytes, voice_bytes=voice_bytes,
            text=observation.content, citizen_category=observation.category,
        )

        meta = result.pop("_meta", {})
        interpretation = _build_interpretation(observation, result, meta)

        await self.interpretation_store.save(interpretation)

        observation.status = "interpreted"
        observation.interpreted_at = datetime.now(timezone.utc)
        await self.observation_store.save(observation)

        await self._record_audit(observation, meta)
        await self._publish_event(observation, interpretation)

        return InterpretResponse(
            interpretation_id=interpretation.id,
            categories=interpretation.categories,
            severity=interpretation.severity.level.value if interpretation.severity else "low",
            confidence=interpretation.confidence_score,
            alignment=interpretation.citizen_category_alignment,
            prompt_version=interpretation.prompt_version,
            schema_version=interpretation.schema_version,
        )

    async def _record_audit(self, observation: Observation, meta: dict) -> None:
        await self.audit_log.append(AuditEvent(
            signal_id="", event_type="observation_interpreted", observation_count=1,
            interpreter_version={
                "model": meta.get("model", "gemini-2.0-flash"),
                "prompt_version": meta.get("prompt_version", "v3.2"),
                "schema_version": meta.get("schema_version", "v2.1"),
            },
            created_at=datetime.now(timezone.utc),
        ))

    async def _publish_event(self, observation: Observation, interpretation: Interpretation) -> None:
        await self.event_bus.publish("ObservationInterpreted", {
            "observation_id": observation.id,
            "interpretation_id": interpretation.id,
            "categories": interpretation.categories,
            "severity": interpretation.severity.level.value if interpretation.severity else "low",
            "prompt_version": interpretation.prompt_version,
            "schema_version": interpretation.schema_version,
        })
