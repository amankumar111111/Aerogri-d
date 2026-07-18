"""Tests for the correlation engine use case."""

from datetime import datetime, timedelta, timezone

import pytest

from app.application.correlate_observation import (
    CorrelateObservationUseCase,
    CorrelateRequest,
)
from app.domain.entities import Signal
from app.domain.ports import EventBus, SignalEventStore, SignalStore
from app.domain.value_objects import ConfidenceScore, Location, SignalState


class InMemorySignalStore(SignalStore):
    def __init__(self) -> None:
        self.signals: dict[str, Signal] = {}

    async def save(self, signal: Signal) -> None:
        self.signals[signal.id] = signal

    async def get(self, signal_id: str) -> Signal | None:
        return self.signals.get(signal_id)

    async def list_(self, *, state: str | None = None, offset: int = 0, limit: int = 20) -> list[Signal]:
        signals = list(self.signals.values())
        if state:
            signals = [s for s in signals if s.state.value == state]
        return signals[:limit]

    async def count(self, *, state: str | None = None) -> int:
        if state:
            return sum(1 for s in self.signals.values() if s.state.value == state)
        return len(self.signals)


class InMemorySignalEventStore(SignalEventStore):
    def __init__(self) -> None:
        self.events: list = []
        self._seq: dict[str, int] = {}

    async def save(self, event) -> None:
        self.events.append(event)

    async def list_by_signal(self, signal_id: str) -> list:
        return [e for e in self.events if e.signal_id == signal_id]

    async def next_sequence(self, signal_id: str) -> int:
        self._seq[signal_id] = self._seq.get(signal_id, 0) + 1
        return self._seq[signal_id]


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict) -> None:
        self.published.append((event_type, payload))

    async def subscribe(self, event_type: str):
        yield {}


async def _make_uc() -> tuple[CorrelateObservationUseCase, InMemorySignalStore, InMemoryEventBus]:
    store = InMemorySignalStore()
    event_store = InMemorySignalEventStore()
    bus = InMemoryEventBus()
    uc = CorrelateObservationUseCase(store, event_store, bus)
    return uc, store, bus


class TestCorrelationEngine:
    @pytest.mark.asyncio
    async def test_first_observation_creates_watch_signal(self) -> None:
        uc, store, bus = await _make_uc()
        req = CorrelateRequest(
            observation_id="obs-1",
            fingerprint="fp-1",
            category="smoke",
            location=Location(latitude=19.076, longitude=72.878),
            timestamp=datetime.now(timezone.utc),
            device_id="device-1",
            evidence_categories=["smoke"],
            evidence_descriptions=["visible smoke"],
            interpretation_confidence=0.8,
        )
        result = await uc.execute(req)
        assert result.is_new_signal is True
        assert result.state == SignalState.WATCH
        assert len(store.signals) == 1
        assert any(e[0] == "SignalCreated" for e in bus.published)

    @pytest.mark.asyncio
    async def test_similar_observation_joins_existing_signal(self) -> None:
        uc, store, bus = await _make_uc()
        now = datetime.now(timezone.utc)

        req1 = CorrelateRequest(
            observation_id="obs-1",
            fingerprint="fp-1",
            category="smoke",
            location=Location(latitude=19.076, longitude=72.878),
            timestamp=now,
            device_id="device-1",
            evidence_categories=["smoke"],
            evidence_descriptions=["smoke visible"],
            interpretation_confidence=0.8,
        )
        r1 = await uc.execute(req1)

        req2 = CorrelateRequest(
            observation_id="obs-2",
            fingerprint="fp-2",
            category="smoke",
            location=Location(latitude=19.0761, longitude=72.8781),
            timestamp=now + timedelta(minutes=2),
            device_id="device-2",
            evidence_categories=["smoke"],
            evidence_descriptions=["heavy smoke"],
            interpretation_confidence=0.85,
        )
        r2 = await uc.execute(req2)

        assert r2.signal_id == r1.signal_id
        assert r2.is_new_signal is False
        signal = await store.get(r1.signal_id)
        assert signal is not None
        assert len(signal.contributing_observation_ids) == 2

    @pytest.mark.asyncio
    async def test_distant_observation_with_different_category_creates_separate_signal(self) -> None:
        uc, store, bus = await _make_uc()
        now = datetime.now(timezone.utc)

        req1 = CorrelateRequest(
            observation_id="obs-1",
            fingerprint="fp-1",
            category="smoke",
            location=Location(latitude=19.076, longitude=72.878),
            timestamp=now,
            device_id="device-1",
            evidence_categories=["smoke"],
            evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
        )
        await uc.execute(req1)

        req2 = CorrelateRequest(
            observation_id="obs-2",
            fingerprint="fp-2",
            category="noise",
            location=Location(latitude=19.5, longitude=73.0),
            timestamp=now + timedelta(minutes=30),
            device_id="device-2",
            evidence_categories=["noise"],
            evidence_descriptions=["loud construction noise"],
            interpretation_confidence=0.7,
        )
        r2 = await uc.execute(req2)

        assert r2.is_new_signal is True
        assert len(store.signals) == 2
