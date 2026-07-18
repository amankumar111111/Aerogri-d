"""SQLAlchemy repository adapters implementing domain ports."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import (
    AuditEvent,
    Interpretation,
    Observation,
    ProviderRecord,
    Signal,
    SignalEvent,
)
from app.domain.ports import (
    AuditLog,
    EventBus,
    InterpretationStore,
    ObservationStore,
    ProviderRecordStore,
    SignalEventStore,
    SignalStore,
)
from app.domain.value_objects import (
    ConfidenceScore,
    ContributionEntry,
    Location,
    SignalState,
)
from app.infrastructure.db import (
    AuditEventRow,
    InterpretationRow,
    ObservationRow,
    ProviderRecordRow,
    SignalEventRow,
    SignalRow,
)


def _parse_contributions(raw: str) -> list[ContributionEntry]:
    if not raw or raw == "[]":
        return []
    items = json.loads(raw)
    return [
        ContributionEntry(
            observation_id=c["observation_id"],
            fingerprint=c["fingerprint"],
            dimension_scores=c["dimension_scores"],
            contribution_score=c["contribution_score"],
            weighted_contribution=c["weighted_contribution"],
            evaluation_timestamp=datetime.fromisoformat(c["evaluation_timestamp"]),
        )
        for c in items
    ]


def _serialize_contributions(entries: list[ContributionEntry]) -> str:
    return json.dumps(
        [
            {
                "observation_id": e.observation_id,
                "fingerprint": e.fingerprint,
                "dimension_scores": e.dimension_scores,
                "contribution_score": e.contribution_score,
                "weighted_contribution": e.weighted_contribution,
                "evaluation_timestamp": e.evaluation_timestamp.isoformat(),
            }
            for e in entries
        ]
    )


class SQLAlchemyObservationStore(ObservationStore):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, observation: Observation) -> None:
        row = ObservationRow(
            id=observation.id,
            fingerprint=observation.fingerprint.hash if observation.fingerprint else None,
            content=observation.content,
            photo_uri=observation.photo_uri,
            voice_uri=observation.voice_uri,
            location_lat=observation.location.latitude,
            location_lng=observation.location.longitude,
            category=observation.category,
            language=observation.language,
            device_id=observation.device_id,
            submitter_ref=observation.submitter_ref,
            status=observation.status,
            created_at=observation.created_at,
            interpreted_at=observation.interpreted_at,
        )
        self.session.add(row)
        await self.session.flush()

    async def get(self, observation_id: str) -> Observation | None:
        result = await self.session.execute(
            select(ObservationRow).where(ObservationRow.id == observation_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return self._to_entity(row)

    async def list_(self, *, offset: int = 0, limit: int = 20) -> list[Observation]:
        result = await self.session.execute(
            select(ObservationRow).order_by(ObservationRow.created_at.desc()).offset(offset).limit(limit)
        )
        return [self._to_entity(r) for r in result.scalars().all()]

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(ObservationRow.id)))
        return result.scalar_one()

    def _to_entity(self, row: ObservationRow) -> Observation:
        from app.domain.value_objects import ObservationFingerprint
        return Observation(
            id=row.id,
            fingerprint=ObservationFingerprint(hash=row.fingerprint) if row.fingerprint else None,
            content=row.content,
            photo_uri=row.photo_uri,
            voice_uri=row.voice_uri,
            location=Location(latitude=row.location_lat, longitude=row.location_lng),
            category=row.category,
            language=row.language,
            device_id=row.device_id,
            submitter_ref=row.submitter_ref,
            status=row.status,
            created_at=row.created_at,
            interpreted_at=row.interpreted_at,
        )


class SQLAlchemyInterpretationStore(InterpretationStore):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, interpretation: Interpretation) -> None:
        row = InterpretationRow(
            id=interpretation.id,
            observation_id=interpretation.observation_id,
            model=interpretation.model,
            prompt_version=interpretation.prompt_version,
            schema_version=interpretation.schema_version,
            categories=json.dumps(interpretation.categories),
            evidence_descriptions=json.dumps(interpretation.evidence_descriptions),
            severity_level=interpretation.severity.level.value if interpretation.severity else None,
            citizen_category_alignment=interpretation.citizen_category_alignment,
            confidence_score=interpretation.confidence_score,
            created_at=interpretation.created_at,
        )
        self.session.add(row)
        await self.session.flush()

    async def get_by_observation(self, observation_id: str) -> Interpretation | None:
        result = await self.session.execute(
            select(InterpretationRow).where(InterpretationRow.observation_id == observation_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return Interpretation(
            id=row.id,
            observation_id=row.observation_id,
            model=row.model,
            prompt_version=row.prompt_version,
            schema_version=row.schema_version,
            categories=json.loads(row.categories),
            evidence_descriptions=json.loads(row.evidence_descriptions),
            severity_level=row.severity_level,
            citizen_category_alignment=row.citizen_category_alignment,
            confidence_score=row.confidence_score,
            created_at=row.created_at,
        )


class SQLAlchemySignalStore(SignalStore):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, signal: Signal) -> None:
        row = SignalRow(
            id=signal.id,
            state=signal.state.value,
            location_lat=signal.location.latitude,
            location_lng=signal.location.longitude,
            category=signal.category,
            confidence_value=signal.confidence.value,
            contributing_observation_ids=json.dumps(signal.contributing_observation_ids),
            contributions=_serialize_contributions(signal.contributions),
            environmental_context=json.dumps(signal.environmental_context),
            version=signal.version,
            created_at=signal.created_at,
            updated_at=signal.updated_at,
            archived_at=signal.archived_at,
        )
        self.session.add(row)
        await self.session.flush()

    async def get(self, signal_id: str) -> Signal | None:
        result = await self.session.execute(
            select(SignalRow).where(SignalRow.id == signal_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return self._to_entity(row)

    async def list_(
        self, *, state: str | None = None, offset: int = 0, limit: int = 20
    ) -> list[Signal]:
        stmt = select(SignalRow)
        if state:
            stmt = stmt.where(SignalRow.state == state)
        stmt = stmt.order_by(SignalRow.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def count(self, *, state: str | None = None) -> int:
        stmt = select(func.count(SignalRow.id))
        if state:
            stmt = stmt.where(SignalRow.state == state)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    def _to_entity(self, row: SignalRow) -> Signal:
        return Signal(
            id=row.id,
            state=SignalState(row.state),
            location=Location(latitude=row.location_lat, longitude=row.location_lng),
            category=row.category,
            confidence=ConfidenceScore(value=row.confidence_value),
            contributing_observation_ids=json.loads(row.contributing_observation_ids),
            contributions=_parse_contributions(row.contributions),
            environmental_context=json.loads(row.environmental_context),
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
            archived_at=row.archived_at,
        )


class SQLAlchemySignalEventStore(SignalEventStore):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, event: SignalEvent) -> None:
        row = SignalEventRow(
            id=event.id,
            signal_id=event.signal_id,
            sequence_number=event.sequence_number,
            event_type=event.event_type,
            previous_state=event.previous_state.value if event.previous_state else None,
            new_state=event.new_state.value if event.new_state else None,
            composite_score=event.composite_score,
            contribution_entries=_serialize_contributions(event.contribution_entries),
            policy_version=event.policy_version,
            engine_version=event.engine_version,
            trigger=event.trigger,
            reason=event.reason,
            created_at=event.created_at,
        )
        self.session.add(row)
        await self.session.flush()

    async def list_by_signal(self, signal_id: str) -> list[SignalEvent]:
        result = await self.session.execute(
            select(SignalEventRow)
            .where(SignalEventRow.signal_id == signal_id)
            .order_by(SignalEventRow.sequence_number)
        )
        return [
            SignalEvent(
                id=r.id,
                signal_id=r.signal_id,
                sequence_number=r.sequence_number,
                event_type=r.event_type,
                previous_state=SignalState(r.previous_state) if r.previous_state else None,
                new_state=SignalState(r.new_state) if r.new_state else None,
                composite_score=r.composite_score,
                contribution_entries=_parse_contributions(r.contribution_entries),
                policy_version=r.policy_version,
                engine_version=r.engine_version,
                trigger=r.trigger,
                reason=r.reason,
                created_at=r.created_at,
            )
            for r in result.scalars().all()
        ]

    async def next_sequence(self, signal_id: str) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(SignalEventRow.sequence_number), 0)).where(
                SignalEventRow.signal_id == signal_id
            )
        )
        return result.scalar_one() + 1


class SQLAlchemyAuditLog(AuditLog):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, event: AuditEvent) -> None:
        row = AuditEventRow(
            id=event.id,
            signal_id=event.signal_id,
            event_type=event.event_type,
            previous_state=event.previous_state,
            new_state=event.new_state,
            composite_score=event.composite_score,
            observation_count=event.observation_count,
            policy_version=event.policy_version,
            engine_version=event.engine_version,
            interpreter_version=json.dumps(event.interpreter_version),
            created_at=event.created_at,
        )
        self.session.add(row)
        await self.session.flush()

    async def list_by_signal(self, signal_id: str) -> list[AuditEvent]:
        result = await self.session.execute(
            select(AuditEventRow)
            .where(AuditEventRow.signal_id == signal_id)
            .order_by(AuditEventRow.created_at)
        )
        return [
            AuditEvent(
                id=r.id,
                signal_id=r.signal_id,
                event_type=r.event_type,
                previous_state=r.previous_state,
                new_state=r.new_state,
                composite_score=r.composite_score,
                observation_count=r.observation_count,
                policy_version=r.policy_version,
                engine_version=r.engine_version,
                interpreter_version=json.loads(r.interpreter_version),
                created_at=r.created_at,
            )
            for r in result.scalars().all()
        ]


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict) -> None:
        self.published.append((event_type, payload))

    async def subscribe(self, event_type: str):
        yield {}
