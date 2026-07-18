"""Tests for the AI layer — Gemini interpreter and interpretation use case."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.application.interpret_observation import (
    InterpretObservationUseCase,
    InterpretRequest,
)
from app.domain.entities import Observation
from app.domain.ports import (
    AuditLog,
    EventBus,
    InterpretationStore,
    ObservationInterpreter,
    ObservationStore,
)
from app.domain.value_objects import Location


class InMemoryObservationStore(ObservationStore):
    def __init__(self) -> None:
        self.observations: dict[str, Observation] = {}

    async def save(self, observation: Observation) -> None:
        self.observations[observation.id] = observation

    async def get(self, observation_id: str) -> Observation | None:
        return self.observations.get(observation_id)

    async def list_(self, *, offset: int = 0, limit: int = 20) -> list[Observation]:
        return list(self.observations.values())[offset : offset + limit]

    async def count(self) -> int:
        return len(self.observations)


class InMemoryInterpretationStore(InterpretationStore):
    def __init__(self) -> None:
        self.interpretations: dict[str, object] = {}

    async def save(self, interpretation) -> None:
        self.interpretations[interpretation.id] = interpretation

    async def get_by_observation(self, observation_id: str):
        for interp in self.interpretations.values():
            if interp.observation_id == observation_id:
                return interp
        return None


class MockInterpreter(ObservationInterpreter):
    def __init__(self, response: dict | None = None) -> None:
        self.response = response or {
            "categories": ["smoke"],
            "evidence_descriptions": ["visible smoke rising from building"],
            "severity": {"level": "high", "indicators": ["thick black smoke"]},
            "citizen_category_alignment": True,
            "confidence": 0.85,
        }
        self.call_count = 0

    async def interpret(self, image_bytes, voice_bytes, text, citizen_category) -> dict:
        self.call_count += 1
        return {**self.response, "_meta": {"model": "gemini-2.0-flash", "prompt_version": "v3.2", "schema_version": "v2.1"}}


class InMemoryAuditLog(AuditLog):
    def __init__(self) -> None:
        self.events: list = []

    async def append(self, event) -> None:
        self.events.append(event)

    async def list_by_signal(self, signal_id: str) -> list:
        return []


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict) -> None:
        self.published.append((event_type, payload))

    async def subscribe(self, event_type: str):
        yield {}


async def _make_uc(
    response: dict | None = None,
) -> tuple[InterpretObservationUseCase, InMemoryObservationStore, MockInterpreter, InMemoryEventBus]:
    obs_store = InMemoryObservationStore()
    interp_store = InMemoryInterpretationStore()
    interpreter = MockInterpreter(response)
    audit_log = InMemoryAuditLog()
    bus = InMemoryEventBus()
    uc = InterpretObservationUseCase(obs_store, interp_store, interpreter, audit_log, bus)
    return uc, obs_store, interpreter, bus


class TestGeminiInterpreter:
    @pytest.mark.asyncio
    async def test_interpretation_returns_structured_data(self) -> None:
        uc, obs_store, interpreter, bus = await _make_uc()

        obs = Observation(
            id="obs-1",
            content="I see heavy smoke coming from the factory",
            category="smoke",
            location=Location(latitude=19.076, longitude=72.878),
            device_id="device-1",
        )
        await obs_store.save(obs)

        result = await uc.execute(InterpretRequest(observation_id="obs-1"))

        assert result.interpretation_id != ""
        assert result.categories == ["smoke"]
        assert result.severity == "high"
        assert result.confidence == 0.85
        assert result.alignment is True
        assert result.prompt_version == "v3.2"
        assert result.schema_version == "v2.1"
        assert interpreter.call_count == 1

    @pytest.mark.asyncio
    async def test_interpretation_publishes_event(self) -> None:
        uc, obs_store, _, bus = await _make_uc()

        obs = Observation(
            id="obs-2",
            content="Chemical smell in the area",
            category="chemical",
            location=Location(latitude=19.076, longitude=72.878),
            device_id="device-1",
        )
        await obs_store.save(obs)

        await uc.execute(InterpretRequest(observation_id="obs-2"))

        assert any(e[0] == "ObservationInterpreted" for e in bus.published)

    @pytest.mark.asyncio
    async def test_missing_observation_raises(self) -> None:
        uc, _, _, _ = await _make_uc()

        with pytest.raises(ValueError, match="not found"):
            await uc.execute(InterpretRequest(observation_id="nonexistent"))

    @pytest.mark.asyncio
    async def test_observation_status_updates_to_interpreted(self) -> None:
        uc, obs_store, _, _ = await _make_uc()

        obs = Observation(
            id="obs-3",
            content="Dust cloud near construction site",
            category="dust",
            location=Location(latitude=19.076, longitude=72.878),
            device_id="device-1",
            status="submitted",
        )
        await obs_store.save(obs)

        await uc.execute(InterpretRequest(observation_id="obs-3"))

        updated = await obs_store.get("obs-3")
        assert updated is not None
        assert updated.status == "interpreted"
        assert updated.interpreted_at is not None
