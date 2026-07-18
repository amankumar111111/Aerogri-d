"""Integration tests — AI layer with shared fixtures."""

from __future__ import annotations

import pytest

from app.application.interpret_observation import InterpretRequest, InterpretObservationUseCase
from app.domain.entities import Observation
from app.domain.value_objects import Location


@pytest.mark.asyncio
async def test_interpretation_returns_structured_data(obs_store, interp_store, interpreter, event_bus, audit_log):
    uc = InterpretObservationUseCase(obs_store, interp_store, interpreter, audit_log, event_bus)

    obs = Observation(
        id="obs-1",
        content="I see heavy smoke coming from the factory",
        category="smoke",
        location=Location(latitude=19.076, longitude=72.878),
        device_id="device-1",
    )
    await obs_store.save(obs)

    result = await uc.execute(InterpretRequest(observation_id="obs-1"))
    assert result.categories == ["smoke"]
    assert result.severity == "high"
    assert result.confidence == 0.85
    assert result.prompt_version == "v3.2"
    assert result.schema_version == "v2.1"


@pytest.mark.asyncio
async def test_interpretation_publishes_event(obs_store, interp_store, interpreter, event_bus, audit_log):
    uc = InterpretObservationUseCase(obs_store, interp_store, interpreter, audit_log, event_bus)

    obs = Observation(
        id="obs-2",
        content="Chemical smell in the area",
        category="chemical",
        location=Location(latitude=19.076, longitude=72.878),
        device_id="device-1",
    )
    await obs_store.save(obs)
    await uc.execute(InterpretRequest(observation_id="obs-2"))

    event_types = [e[0] for e in event_bus.published]
    assert "ObservationInterpreted" in event_types


@pytest.mark.asyncio
async def test_missing_observation_raises(obs_store, interp_store, interpreter, event_bus, audit_log):
    uc = InterpretObservationUseCase(obs_store, interp_store, interpreter, audit_log, event_bus)
    with pytest.raises(ValueError, match="not found"):
        await uc.execute(InterpretRequest(observation_id="nonexistent"))


@pytest.mark.asyncio
async def test_observation_status_updates_to_interpreted(obs_store, interp_store, interpreter, event_bus, audit_log):
    uc = InterpretObservationUseCase(obs_store, interp_store, interpreter, audit_log, event_bus)

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
