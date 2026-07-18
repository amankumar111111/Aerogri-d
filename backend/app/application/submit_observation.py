"""Use case: Submit a new observation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.entities import AuditEvent, Observation
from app.domain.ports import AuditLog, EventBus, ObservationStore
from app.domain.value_objects import Location, ObservationFingerprint


@dataclass
class SubmitObservationRequest:
    content: str
    latitude: float
    longitude: float
    category: str
    language: str
    device_id: str
    photo_bytes: bytes | None = None
    voice_bytes: bytes | None = None


@dataclass
class SubmitObservationResponse:
    observation_id: str
    fingerprint: str
    status: str


class SubmitObservationUseCase:
    def __init__(
        self,
        observation_store: ObservationStore,
        audit_log: AuditLog,
        event_bus: EventBus,
    ) -> None:
        self.observation_store = observation_store
        self.audit_log = audit_log
        self.event_bus = event_bus

    async def execute(self, request: SubmitObservationRequest) -> SubmitObservationResponse:
        location = Location(latitude=request.latitude, longitude=request.longitude)
        timestamp = datetime.now(timezone.utc)

        fingerprint = ObservationFingerprint.compute(
            image_bytes=request.photo_bytes,
            voice_bytes=request.voice_bytes,
            location=location,
            timestamp=timestamp,
            device_id=request.device_id,
        )

        observation = Observation(
            content=request.content,
            location=location,
            category=request.category,
            language=request.language,
            device_id=request.device_id,
            fingerprint=fingerprint,
            status="submitted",
            created_at=timestamp,
        )

        await self.observation_store.save(observation)

        audit_event = AuditEvent(
            signal_id="",
            event_type="observation_submitted",
            observation_count=1,
            created_at=timestamp,
        )
        await self.audit_log.append(audit_event)

        await self.event_bus.publish(
            "ObservationSubmitted",
            {
                "observation_id": observation.id,
                "fingerprint": fingerprint.hash,
                "location": {"lat": location.latitude, "lng": location.longitude},
                "category": request.category,
                "timestamp": timestamp.isoformat(),
            },
        )

        return SubmitObservationResponse(
            observation_id=observation.id,
            fingerprint=fingerprint.hash,
            status="submitted",
        )
