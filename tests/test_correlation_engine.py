"""Integration tests — Correlation engine with shared fixtures."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from app.application.correlate_observation import CorrelateRequest, CorrelateObservationUseCase
from app.domain.policies import CorrelationConfig
from app.domain.value_objects import Location, SignalState


@pytest.mark.asyncio
async def test_first_observation_creates_watch_signal(signal_store, signal_event_store, event_bus):
    config = CorrelationConfig()
    uc = CorrelateObservationUseCase(signal_store, signal_event_store, event_bus, config)

    result = await uc.execute(CorrelateRequest(
        observation_id="obs-1", fingerprint="fp-1", category="smoke",
        location=Location(19.076, 72.878),
        timestamp=datetime.now(timezone.utc), device_id="d1",
        evidence_categories=["smoke"], evidence_descriptions=["smoke"],
        interpretation_confidence=0.8,
    ))
    assert result.is_new_signal is True
    assert result.state == SignalState.WATCH
    assert len(signal_store.items) == 1


@pytest.mark.asyncio
async def test_similar_observations_correlate(signal_store, signal_event_store, event_bus):
    config = CorrelationConfig()
    uc = CorrelateObservationUseCase(signal_store, signal_event_store, event_bus, config)
    now = datetime.now(timezone.utc)

    r1 = await uc.execute(CorrelateRequest(
        observation_id="obs-1", fingerprint="fp-1", category="smoke",
        location=Location(19.076, 72.878), timestamp=now, device_id="d1",
        evidence_categories=["smoke"], evidence_descriptions=["smoke"],
        interpretation_confidence=0.8,
    ))
    r2 = await uc.execute(CorrelateRequest(
        observation_id="obs-2", fingerprint="fp-2", category="smoke",
        location=Location(19.0761, 72.8781), timestamp=now + timedelta(minutes=2),
        device_id="d2", evidence_categories=["smoke"], evidence_descriptions=["heavy smoke"],
        interpretation_confidence=0.85,
    ))
    assert r2.signal_id == r1.signal_id
    assert r2.is_new_signal is False
    signal = await signal_store.get(r1.signal_id)
    assert len(signal.contributing_observation_ids) == 2


@pytest.mark.asyncio
async def test_distant_observations_separate_signals(signal_store, signal_event_store, event_bus):
    config = CorrelationConfig()
    uc = CorrelateObservationUseCase(signal_store, signal_event_store, event_bus, config)
    now = datetime.now(timezone.utc)

    await uc.execute(CorrelateRequest(
        observation_id="obs-1", fingerprint="fp-1", category="smoke",
        location=Location(19.076, 72.878), timestamp=now, device_id="d1",
        evidence_categories=["smoke"], evidence_descriptions=["smoke"],
        interpretation_confidence=0.8,
    ))
    r2 = await uc.execute(CorrelateRequest(
        observation_id="obs-2", fingerprint="fp-2", category="noise",
        location=Location(19.5, 73.0), timestamp=now + timedelta(minutes=30),
        device_id="d2", evidence_categories=["noise"], evidence_descriptions=["noise"],
        interpretation_confidence=0.7,
    ))
    assert r2.is_new_signal is True
    assert len(signal_store.items) == 2


@pytest.mark.asyncio
async def test_correlation_events_are_recorded(signal_store, signal_event_store, event_bus):
    config = CorrelationConfig()
    uc = CorrelateObservationUseCase(signal_store, signal_event_store, event_bus, config)

    result = await uc.execute(CorrelateRequest(
        observation_id="obs-1", fingerprint="fp-1", category="smoke",
        location=Location(19.076, 72.878), timestamp=datetime.now(timezone.utc),
        device_id="d1", evidence_categories=["smoke"], evidence_descriptions=["smoke"],
        interpretation_confidence=0.8,
    ))
    events = await signal_event_store.list_by_signal(result.signal_id)
    assert len(events) >= 1
    assert events[0].event_type == "created"
