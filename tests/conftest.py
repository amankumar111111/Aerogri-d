"""Shared test fixtures and doubles — single source of truth.

All test doubles live here. Individual test files import from conftest,
not define their own copies.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from datetime import datetime, timezone

from app.domain.entities import (
    AuditEvent,
    Interpretation,
    Observation,
    Signal,
    SignalEvent,
)
from app.domain.policies import CorrelationConfig
from app.domain.ports import (
    AuditLog,
    EventBus,
    InterpretationStore,
    ObservationInterpreter,
    ObservationStore,
    SignalEventStore,
    SignalStore,
)
from app.domain.value_objects import ConfidenceScore, Location, SignalState


# ============================================================
# In-Memory Test Doubles
# ============================================================

class MemObsStore(ObservationStore):
    def __init__(self):
        self.items: dict[str, Observation] = {}

    async def save(self, o: Observation) -> None:
        self.items[o.id] = o

    async def get(self, observation_id: str) -> Observation | None:
        return self.items.get(observation_id)

    async def list_(self, *, offset: int = 0, limit: int = 20) -> list[Observation]:
        return list(self.items.values())[offset : offset + limit]

    async def count(self) -> int:
        return len(self.items)


class MemInterpStore(InterpretationStore):
    def __init__(self):
        self.items: dict[str, Interpretation] = {}

    async def save(self, i: Interpretation) -> None:
        self.items[i.id] = i

    async def get_by_observation(self, observation_id: str) -> Interpretation | None:
        for i in self.items.values():
            if i.observation_id == observation_id:
                return i
        return None


class MemSignalStore(SignalStore):
    def __init__(self):
        self.items: dict[str, Signal] = {}

    async def save(self, s: Signal) -> None:
        self.items[s.id] = s

    async def get(self, signal_id: str) -> Signal | None:
        return self.items.get(signal_id)

    async def list_(self, *, state: str | None = None, offset: int = 0, limit: int = 20) -> list[Signal]:
        items = list(self.items.values())
        if state:
            items = [s for s in items if s.state.value == state]
        return items[offset : offset + limit]

    async def count(self, *, state: str | None = None) -> int:
        if state:
            return sum(1 for s in self.items.values() if s.state.value == state)
        return len(self.items)


class MemSignalEventStore(SignalEventStore):
    def __init__(self):
        self.events: list[SignalEvent] = []
        self._seq: dict[str, int] = {}

    async def save(self, event: SignalEvent) -> None:
        self.events.append(event)

    async def list_by_signal(self, signal_id: str) -> list[SignalEvent]:
        return [e for e in self.events if e.signal_id == signal_id]

    async def next_sequence(self, signal_id: str) -> int:
        self._seq[signal_id] = self._seq.get(signal_id, 0) + 1
        return self._seq[signal_id]


class MemAuditLog(AuditLog):
    def __init__(self):
        self.events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        self.events.append(event)

    async def list_by_signal(self, signal_id: str) -> list[AuditEvent]:
        return []


class MemEventBus(EventBus):
    def __init__(self):
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict) -> None:
        self.published.append((event_type, payload))

    async def subscribe(self, event_type: str):
        yield {}


class MockInterpreter(ObservationInterpreter):
    def __init__(self, response: dict | None = None, should_fail: bool = False):
        self.response = response or {
            "categories": ["smoke"],
            "evidence_descriptions": ["visible smoke rising from building"],
            "severity": {"level": "high", "indicators": ["thick black smoke"]},
            "citizen_category_alignment": True,
            "confidence": 0.85,
        }
        self.should_fail = should_fail
        self.call_count = 0

    async def interpret(self, image_bytes, voice_bytes, text, citizen_category):
        self.call_count += 1
        if self.should_fail:
            raise Exception("Gemini API timeout")
        return {
            **self.response,
            "_meta": {
                "model": "gemini-2.0-flash",
                "prompt_version": "v3.2",
                "schema_version": "v2.1",
            },
        }


# ============================================================
# Pytest Fixtures
# ============================================================

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def obs_store():
    return MemObsStore()


@pytest.fixture
def interp_store():
    return MemInterpStore()


@pytest.fixture
def signal_store():
    return MemSignalStore()


@pytest.fixture
def signal_event_store():
    return MemSignalEventStore()


@pytest.fixture
def audit_log():
    return MemAuditLog()


@pytest.fixture
def event_bus():
    return MemEventBus()


@pytest.fixture
def interpreter():
    return MockInterpreter()


@pytest.fixture
def failing_interpreter():
    return MockInterpreter(should_fail=True)


@pytest.fixture
def correlation_config():
    return CorrelationConfig()
