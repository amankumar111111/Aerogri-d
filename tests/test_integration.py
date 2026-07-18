"""System Integration Tests — all workflows use shared fixtures from conftest."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.application.submit_observation import SubmitObservationRequest, SubmitObservationUseCase
from app.application.interpret_observation import InterpretRequest, InterpretObservationUseCase
from app.application.correlate_observation import CorrelateRequest, CorrelateObservationUseCase
from app.domain.policies import CorrelationConfig
from app.domain.value_objects import Location, SignalState
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================
# Workflow 1: Citizen Report
# ============================================================

class TestWorkflow1_CitizenReport:
    @pytest.mark.asyncio
    async def test_full_citizen_flow(self, obs_store, interp_store, signal_store, signal_event_store, audit_log, event_bus, interpreter):
        submit_uc = SubmitObservationUseCase(obs_store, audit_log, event_bus)
        interpret_uc = InterpretObservationUseCase(obs_store, interp_store, interpreter, audit_log, event_bus)

        sub = await submit_uc.execute(SubmitObservationRequest(
            content="Heavy smoke from factory",
            latitude=19.076, longitude=72.878,
            category="smoke", language="en", device_id="device-1",
        ))
        assert sub.observation_id
        assert sub.status == "submitted"

        obs = await obs_store.get(sub.observation_id)
        assert obs is not None
        assert obs.content == "Heavy smoke from factory"

        interp_result = await interpret_uc.execute(InterpretRequest(observation_id=sub.observation_id))
        assert interp_result.categories == ["smoke"]
        assert interp_result.severity == "high"

        interp_entity = await interp_store.get_by_observation(sub.observation_id)
        assert interp_entity is not None
        assert interp_entity.model == "gemini-2.0-flash"

        obs = await obs_store.get(sub.observation_id)
        assert obs.status == "interpreted"

        assert len(audit_log.events) >= 2
        event_types = [e.event_type for e in audit_log.events]
        assert "observation_submitted" in event_types
        assert "observation_interpreted" in event_types

    @pytest.mark.asyncio
    async def test_fingerprint_is_deterministic(self):
        from app.domain.value_objects import ObservationFingerprint
        fp1 = ObservationFingerprint.compute(b"img", b"voice", Location(19.076, 72.878), datetime.now(timezone.utc), "d1")
        fp2 = ObservationFingerprint.compute(b"img", b"voice", Location(19.076, 72.878), datetime.now(timezone.utc), "d1")
        assert fp1.hash == fp2.hash

    @pytest.mark.asyncio
    async def test_different_inputs_different_fingerprint(self):
        from app.domain.value_objects import ObservationFingerprint
        fp1 = ObservationFingerprint.compute(b"img", None, Location(19.0, 72.0), datetime.now(timezone.utc), "d1")
        fp2 = ObservationFingerprint.compute(b"img", None, Location(19.0, 72.0), datetime.now(timezone.utc), "d2")
        assert fp1.hash != fp2.hash

    @pytest.mark.asyncio
    async def test_missing_observation_raises(self, obs_store, interp_store, interpreter, event_bus, audit_log):
        uc = InterpretObservationUseCase(obs_store, interp_store, interpreter, audit_log, event_bus)
        with pytest.raises(ValueError, match="not found"):
            await uc.execute(InterpretRequest(observation_id="nonexistent"))


# ============================================================
# Workflow 2: Correlation
# ============================================================

class TestWorkflow2_Correlation:
    @pytest.mark.asyncio
    async def test_first_observation_creates_watch_signal(self, signal_store, signal_event_store, event_bus):
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signal_store, signal_event_store, event_bus, config)

        result = await uc.execute(CorrelateRequest(
            observation_id="obs-1", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878), timestamp=datetime.now(timezone.utc),
            device_id="d1", evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
        ))
        assert result.is_new_signal is True
        assert result.state == SignalState.WATCH

    @pytest.mark.asyncio
    async def test_similar_observations_correlate(self, signal_store, signal_event_store, event_bus):
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

    @pytest.mark.asyncio
    async def test_distant_observations_separate_signals(self, signal_store, signal_event_store, event_bus):
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
    async def test_duplicate_detection_via_fingerprint(self):
        from app.domain.value_objects import ObservationFingerprint
        fp1 = ObservationFingerprint.compute(b"same_image", None, Location(19.076, 72.878), datetime.now(timezone.utc), "device-1")
        fp2 = ObservationFingerprint.compute(b"same_image", None, Location(19.076, 72.878), datetime.now(timezone.utc), "device-1")
        assert fp1.hash == fp2.hash

    @pytest.mark.asyncio
    async def test_correlation_events_are_recorded(self, signal_store, signal_event_store, event_bus):
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


# ============================================================
# Workflow 3: Environmental Providers
# ============================================================

class TestWorkflow3_Providers:
    @pytest.mark.asyncio
    async def test_weather_provider_success(self):
        from app.infrastructure.providers.weather import WeatherProvider
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "current": {"temperature_2m": 25, "relative_humidity_2m": 60,
                        "wind_speed_10m": 10, "wind_direction_180": 90,
                        "precipitation": 0, "time": "2024-01-15T10:30"}
        }
        mock_resp.raise_for_status = lambda: None
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=mock_resp)
        with patch("httpx.AsyncClient", return_value=client):
            result = await WeatherProvider().fetch(latitude=19.076, longitude=72.878)
        assert result.status == "available"

    @pytest.mark.asyncio
    async def test_weather_provider_unavailable(self):
        from app.infrastructure.providers.weather import WeatherProvider
        import httpx
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        with patch("httpx.AsyncClient", return_value=client):
            result = await WeatherProvider().fetch(latitude=19.076, longitude=72.878)
        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_firms_provider_no_api_key(self):
        from app.infrastructure.providers.firms import FIRMSProvider
        result = await FIRMSProvider(api_key="").fetch(latitude=19.076, longitude=72.878)
        assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_cpcb_provider_no_url(self):
        from app.infrastructure.providers.cpcb import CPCBProvider
        result = await CPCBProvider().fetch(latitude=19.076, longitude=72.878)
        assert result.status == "unavailable"

    def test_environmental_score_with_all_factors(self):
        from app.domain.policies import environmental_score
        score = environmental_score(
            wind_consistent=True, low_humidity_high_temp=True,
            firms_fire_detected=True, cpcb_elevated=True,
        )
        assert score == 0.7

    def test_environmental_score_with_rain(self):
        from app.domain.policies import environmental_score
        score = environmental_score(recent_precipitation=True)
        assert score == 0.0

    def test_provider_records_store_confidence_and_latency(self):
        from app.domain.entities import ProviderRecord
        record = ProviderRecord(provider_type="weather", confidence=0.9, latency_ms=340.0, status="available")
        assert record.confidence == 0.9
        assert record.latency_ms == 340.0


# ============================================================
# Workflow 4: Dashboard (API)
# ============================================================

class TestWorkflow4_Dashboard:
    def test_openapi_spec_has_all_endpoints(self):
        from app.main import app
        spec = app.openapi()
        paths = list(spec["paths"].keys())
        assert "/api/v1/observations" in paths
        assert "/api/v1/signals" in paths
        assert "/api/v1/analytics" in paths
        assert "/api/v1/health" in paths
        assert "/api/v1/notifications" in paths

    def test_openapi_has_error_schemas(self):
        from app.main import app
        spec = app.openapi()
        schemas = spec["components"]["schemas"]
        assert "ErrorResponse" in schemas
        assert "ErrorBody" in schemas

    def test_openapi_has_enum_schemas(self):
        from app.main import app
        spec = app.openapi()
        schemas = spec["components"]["schemas"]
        assert "SignalStateEnum" in schemas
        assert "ObservationCategoryEnum" in schemas
        assert schemas["SignalStateEnum"]["enum"] == ["watch", "probable_hotspot", "high_confidence", "archived"]

    def test_signal_response_has_all_required_fields(self):
        from app.main import app
        spec = app.openapi()
        signal_schema = spec["components"]["schemas"]["SignalResponse"]
        required = signal_schema["required"]
        assert "id" in required
        assert "state" in required
        assert "confidence_value" in required
        assert "contributions" in required
        assert "environmental_context" in required


# ============================================================
# Workflow 5: Audit
# ============================================================

class TestWorkflow5_Audit:
    @pytest.mark.asyncio
    async def test_submit_generates_audit_event(self, obs_store, audit_log, event_bus):
        uc = SubmitObservationUseCase(obs_store, audit_log, event_bus)
        await uc.execute(SubmitObservationRequest(
            content="Test", latitude=19.0, longitude=72.0,
            category="smoke", language="en", device_id="d1",
        ))
        assert len(audit_log.events) >= 1
        assert audit_log.events[0].event_type == "observation_submitted"

    @pytest.mark.asyncio
    async def test_interpret_generates_audit_event(self, obs_store, interp_store, interpreter, event_bus, audit_log):
        submit_uc = SubmitObservationUseCase(obs_store, audit_log, event_bus)
        result = await submit_uc.execute(SubmitObservationRequest(
            content="Test", latitude=19.0, longitude=72.0,
            category="smoke", language="en", device_id="d1",
        ))
        interpret_uc = InterpretObservationUseCase(obs_store, interp_store, interpreter, audit_log, event_bus)
        await interpret_uc.execute(InterpretRequest(observation_id=result.observation_id))

        event_types = [e.event_type for e in audit_log.events]
        assert "observation_submitted" in event_types
        assert "observation_interpreted" in event_types

    @pytest.mark.asyncio
    async def test_correlation_generates_signal_events(self, signal_store, signal_event_store, event_bus):
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

    @pytest.mark.asyncio
    async def test_full_audit_trail(self, obs_store, interp_store, signal_store, signal_event_store, audit_log, event_bus, interpreter):
        config = CorrelationConfig()
        submit_uc = SubmitObservationUseCase(obs_store, audit_log, event_bus)
        interpret_uc = InterpretObservationUseCase(obs_store, interp_store, interpreter, audit_log, event_bus)
        correlate_uc = CorrelateObservationUseCase(signal_store, signal_event_store, event_bus, config)

        sub = await submit_uc.execute(SubmitObservationRequest(
            content="Smoke visible", latitude=19.076, longitude=72.878,
            category="smoke", language="en", device_id="d1",
        ))
        interp = await interpret_uc.execute(InterpretRequest(observation_id=sub.observation_id))
        corr = await correlate_uc.execute(CorrelateRequest(
            observation_id=sub.observation_id, fingerprint=sub.fingerprint,
            category="smoke", location=Location(19.076, 72.878),
            timestamp=datetime.now(timezone.utc), device_id="d1",
            evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=interp.confidence,
        ))

        assert len(audit_log.events) >= 2
        signal_events = await signal_event_store.list_by_signal(corr.signal_id)
        assert len(signal_events) >= 1
        bus_types = [e[0] for e in event_bus.published]
        assert "ObservationSubmitted" in bus_types
        assert "ObservationInterpreted" in bus_types
        assert "SignalCreated" in bus_types
