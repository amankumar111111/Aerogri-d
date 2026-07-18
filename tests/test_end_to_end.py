"""End-to-End Workflow Tests — all use shared fixtures from conftest."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from app.application.submit_observation import SubmitObservationRequest, SubmitObservationUseCase
from app.application.interpret_observation import InterpretRequest, InterpretObservationUseCase
from app.application.correlate_observation import CorrelateRequest, CorrelateObservationUseCase
from app.domain.policies import CorrelationConfig
from app.domain.value_objects import Location, SignalState


# ============================================================
# Scenario 1: Full Citizen Flow
# ============================================================

class TestScenario1_FullFlow:
    @pytest.mark.asyncio
    async def test_photo_voice_gps_gemini_observation_correlation_signal(
        self, obs_store, interp_store, signal_store, signal_event_store, audit_log, event_bus, interpreter
    ):
        config = CorrelationConfig()
        submit_uc = SubmitObservationUseCase(obs_store, audit_log, event_bus)
        interpret_uc = InterpretObservationUseCase(obs_store, interp_store, interpreter, audit_log, event_bus)
        correlate_uc = CorrelateObservationUseCase(signal_store, signal_event_store, event_bus, config)

        sub = await submit_uc.execute(SubmitObservationRequest(
            content="Heavy smoke from factory chimney",
            latitude=19.076, longitude=72.878,
            category="smoke", language="en", device_id="citizen-phone-1",
        ))
        assert sub.observation_id
        assert sub.status == "submitted"

        interp_result = await interpret_uc.execute(InterpretRequest(observation_id=sub.observation_id))
        assert interp_result.categories == ["smoke"]
        assert interp_result.confidence == 0.85

        interp_entity = await interp_store.get_by_observation(sub.observation_id)
        corr = await correlate_uc.execute(CorrelateRequest(
            observation_id=sub.observation_id, fingerprint=sub.fingerprint,
            category="smoke", location=Location(19.076, 72.878),
            timestamp=datetime.now(timezone.utc), device_id="citizen-phone-1",
            evidence_categories=["smoke"], evidence_descriptions=["visible smoke"],
            interpretation_confidence=0.85,
        ))
        assert corr.signal_id

        signal = await signal_store.get(corr.signal_id)
        assert signal is not None
        assert signal.state == SignalState.WATCH
        assert sub.observation_id in signal.contributing_observation_ids

        assert len(audit_log.events) >= 2
        bus_types = [e[0] for e in event_bus.published]
        assert "ObservationSubmitted" in bus_types
        assert "ObservationInterpreted" in bus_types
        assert "SignalCreated" in bus_types


# ============================================================
# Scenario 2: Duplicate Report
# ============================================================

class TestScenario2_DuplicateReport:
    @pytest.mark.asyncio
    async def test_fingerprint_exact_match(self):
        from app.domain.value_objects import ObservationFingerprint
        fp1 = ObservationFingerprint.compute(
            b"same_image", None, Location(19.076, 72.878),
            datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc), "device-1",
        )
        fp2 = ObservationFingerprint.compute(
            b"same_image", None, Location(19.076, 72.878),
            datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc), "device-1",
        )
        assert fp1.hash == fp2.hash


# ============================================================
# Scenario 3: Gemini Unavailable
# ============================================================

class TestScenario3_GeminiUnavailable:
    @pytest.mark.asyncio
    async def test_gemini_timeout_observation_retained(
        self, obs_store, interp_store, event_bus, audit_log, failing_interpreter
    ):
        submit_uc = SubmitObservationUseCase(obs_store, audit_log, bus := event_bus)
        interpret_uc = InterpretObservationUseCase(obs_store, interp_store, failing_interpreter, audit_log, bus)

        sub = await submit_uc.execute(SubmitObservationRequest(
            content="Smoke visible", latitude=19.076, longitude=72.878,
            category="smoke", language="en", device_id="d1",
        ))

        with pytest.raises(Exception, match="Gemini API timeout"):
            await interpret_uc.execute(InterpretRequest(observation_id=sub.observation_id))

        obs = await obs_store.get(sub.observation_id)
        assert obs is not None
        assert obs.status == "submitted"

        assert len(audit_log.events) >= 1

        failing_interpreter.should_fail = False
        interp_result = await interpret_uc.execute(InterpretRequest(observation_id=sub.observation_id))
        assert interp_result.categories == ["smoke"]
        assert failing_interpreter.call_count == 2


# ============================================================
# Scenario 4: Provider Unavailable
# ============================================================

class TestScenario4_ProviderUnavailable:
    @pytest.mark.asyncio
    async def test_cpcb_unavailable_signal_still_computed(self, signal_store, signal_event_store, event_bus):
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signal_store, signal_event_store, event_bus, config)

        result = await uc.execute(CorrelateRequest(
            observation_id="obs-1", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878), timestamp=datetime.now(timezone.utc),
            device_id="d1", evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8, environmental_context={},
        ))
        assert result.signal_id
        signal = await signal_store.get(result.signal_id)
        assert signal.environmental_context == {}

    @pytest.mark.asyncio
    async def test_partial_provider_data(self, signal_store, signal_event_store, event_bus):
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signal_store, signal_event_store, event_bus, config)

        result = await uc.execute(CorrelateRequest(
            observation_id="obs-1", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878), timestamp=datetime.now(timezone.utc),
            device_id="d1", evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
            environmental_context={"temperature": 38, "humidity": 35},
        ))
        signal = await signal_store.get(result.signal_id)
        assert signal.environmental_context.get("temperature") == 38
        assert "fire_detected" not in signal.environmental_context
