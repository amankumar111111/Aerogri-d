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

        image_bytes = None
        voice_bytes = None

        # C6 FIX: Load media from storage if available
        if self.media_store:
            if observation.photo_uri:
                image_bytes = await self.media_store.get(observation.photo_uri)
            if observation.voice_uri:
                voice_bytes = await self.media_store.get(observation.voice_uri)

        result = await self.interpreter.interpret(
            image_bytes=image_bytes,
            voice_bytes=voice_bytes,
            text=observation.content,
            citizen_category=observation.category,
        )

        meta = result.pop("_meta", {})

        severity_data = result.get("severity", {})
        severity_level = SeverityLevel(severity_data.get("level", "low"))
        severity = Severity(
            level=severity_level,
            indicators=tuple(severity_data.get("indicators", [])),
        )

        interpretation = Interpretation(
            observation_id=observation.id,
            model=meta.get("model", "gemini-2.0-flash"),
            prompt_version=meta.get("prompt_version", "v3.2"),
            schema_version=meta.get("schema_version", "v2.1"),
            categories=result.get("categories", []),
            evidence_descriptions=result.get("evidence_descriptions", []),
            severity=severity,
            citizen_category_alignment=result.get("citizen_category_alignment", False),
            confidence_score=result.get("confidence", 0.0),
            created_at=datetime.now(timezone.utc),
        )

        await self.interpretation_store.save(interpretation)

        observation.status = "interpreted"
        observation.interpreted_at = datetime.now(timezone.utc)
        await self.observation_store.save(observation)

        audit_event = AuditEvent(
            signal_id="",
            event_type="observation_interpreted",
            observation_count=1,
            interpreter_version={
                "model": meta.get("model", "gemini-2.0-flash"),
                "prompt_version": meta.get("prompt_version", "v3.2"),
                "schema_version": meta.get("schema_version", "v2.1"),
            },
            created_at=datetime.now(timezone.utc),
        )
        await self.audit_log.append(audit_event)

        await self.event_bus.publish(
            "ObservationInterpreted",
            {
                "observation_id": observation.id,
                "interpretation_id": interpretation.id,
                "categories": interpretation.categories,
                "severity": interpretation.severity.level.value if interpretation.severity else "low",
                "prompt_version": interpretation.prompt_version,
                "schema_version": interpretation.schema_version,
            },
        )

        return InterpretResponse(
            interpretation_id=interpretation.id,
            categories=interpretation.categories,
            severity=interpretation.severity.level.value if interpretation.severity else "low",
            confidence=interpretation.confidence_score,
            alignment=interpretation.citizen_category_alignment,
            prompt_version=interpretation.prompt_version,
            schema_version=interpretation.schema_version,
        )
