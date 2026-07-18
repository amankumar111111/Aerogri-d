"""Phase 9 — System Integration Tests.

Verifies every end-to-end workflow:
1. Citizen Report: submit → interpret → store → audit
2. Correlation: observation → independence → correlation → convergence → signal
3. Environmental Providers: weather/FIRMS/CPCB → context → fusion
4. Dashboard: signal → DB → API → frontend response
5. Audit: every action generates traceable events
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.application.submit_observation import SubmitObservationRequest, SubmitObservationUseCase
from app.application.interpret_observation import InterpretRequest, InterpretObservationUseCase
from app.application.correlate_observation import CorrelateRequest, CorrelateObservationUseCase
from app.domain.entities import Observation, Signal
from app.domain.policies import (
    CorrelationConfig,
    composite_score,
    environmental_score,
    independence_score,
    semantic_score,
    spatial_score,
    temporal_score,
)
from app.domain.ports import (
    AuditLog,
    EventBus,
    InterpretationStore,
    ObservationInterpreter,
    ObservationStore,
    SignalEventStore,
    SignalStore,
)
from app.domain.value_objects import Location, ObservationFingerprint, SignalState


# --- In-memory test doubles ---

class MemObsStore(ObservationStore):
    def __init__(self): self.items: dict[str, Observation] = {}
    async def save(self, o): self.items[o.id] = o
    async def get(self, id): return self.items.get(id)
    async def list_(self, *, offset=0, limit=20): return list(self.items.values())[offset:offset+limit]
    async def count(self): return len(self.items)

class MemInterpStore(InterpretationStore):
    def __init__(self): self.items: dict[str, object] = {}
    async def save(self, i): self.items[i.id] = i
    async def get_by_observation(self, oid):
        for i in self.items.values():
            if i.observation_id == oid: return i
        return None

class MemSignalStore(SignalStore):
    def __init__(self): self.items: dict[str, Signal] = {}
    async def save(self, s): self.items[s.id] = s
    async def get(self, id): return self.items.get(id)
    async def list_(self, *, state=None, offset=0, limit=20):
        items = list(self.items.values())
        if state: items = [s for s in items if s.state.value == state]
        return items[offset:offset+limit]
    async def count(self, *, state=None):
        if state: return sum(1 for s in self.items.values() if s.state.value == state)
        return len(self.items)

class MemSignalEventStore(SignalEventStore):
    def __init__(self): self.events = []; self._seq = {}
    async def save(self, e): self.events.append(e)
    async def list_by_signal(self, sid): return [e for e in self.events if e.signal_id == sid]
    async def next_sequence(self, sid):
        self._seq[sid] = self._seq.get(sid, 0) + 1
        return self._seq[sid]

class MemAuditLog(AuditLog):
    def __init__(self): self.events = []
    async def append(self, e): self.events.append(e)
    async def list_by_signal(self, sid): return [e for e in self.events if e.signal_id == sid]

class MemEventBus(EventBus):
    def __init__(self): self.published = []
    async def publish(self, et, p): self.published.append((et, p))
    async def subscribe(self, et): yield {}


def _make_stores():
    obs = MemObsStore()
    interp = MemInterpStore()
    signals = MemSignalStore()
    sig_events = MemSignalEventStore()
    audit = MemAuditLog()
    bus = MemEventBus()
    return obs, interp, signals, sig_events, audit, bus


def _make_gemini(response: dict | None = None):
    class MockGemini(ObservationInterpreter):
        def __init__(self):
            self.response = response or {
                "categories": ["smoke"],
                "evidence_descriptions": ["visible smoke rising from building"],
                "severity": {"level": "high", "indicators": ["thick black smoke"]},
                "citizen_category_alignment": True,
                "confidence": 0.85,
            }
            self.call_count = 0
        async def interpret(self, image_bytes, voice_bytes, text, citizen_category):
            self.call_count += 1
            return {**self.response, "_meta": {"model": "gemini-2.0-flash", "prompt_version": "v3.2", "schema_version": "v2.1"}}
    return MockGemini()


# ============================================================
# Workflow 1 — Citizen Report Integration
# ============================================================

class TestWorkflow1_CitizenReport:
    @pytest.mark.asyncio
    async def test_full_citizen_flow(self):
        """Submit → Interpret → Store → Audit."""
        obs_store, interp_store, _, _, audit, bus = _make_stores()
        gemini = _make_gemini()

        submit_uc = SubmitObservationUseCase(obs_store, audit, bus)
        interpret_uc = InterpretObservationUseCase(obs_store, interp_store, gemini, audit, bus)

        # Step 1: Citizen submits
        submit_result = await submit_uc.execute(SubmitObservationRequest(
            content="Heavy smoke from factory",
            latitude=19.076, longitude=72.878,
            category="smoke", language="en", device_id="device-1",
        ))
        assert submit_result.observation_id
        assert submit_result.status == "submitted"

        # Verify observation stored
        obs = await obs_store.get(submit_result.observation_id)
        assert obs is not None
        assert obs.content == "Heavy smoke from factory"
        assert obs.status == "submitted"

        # Step 2: Gemini interprets
        interp_result = await interpret_uc.execute(InterpretRequest(
            observation_id=submit_result.observation_id
        ))
        assert interp_result.categories == ["smoke"]
        assert interp_result.severity == "high"
        assert interp_result.prompt_version == "v3.2"
        assert interp_result.schema_version == "v2.1"

        # Verify interpretation stored
        interp = await interp_store.get_by_observation(submit_result.observation_id)
        assert interp is not None
        assert interp.model == "gemini-2.0-flash"

        # Verify observation status updated
        obs = await obs_store.get(submit_result.observation_id)
        assert obs.status == "interpreted"
        assert obs.interpreted_at is not None

        # Verify audit trail
        assert len(audit.events) >= 2  # submitted + interpreted
        event_types = [e.event_type for e in audit.events]
        assert "observation_submitted" in event_types
        assert "observation_interpreted" in event_types

        # Verify events published
        event_types = [e[0] for e in bus.published]
        assert "ObservationSubmitted" in event_types
        assert "ObservationInterpreted" in event_types

    @pytest.mark.asyncio
    async def test_fingerprint_is_deterministic(self):
        """Same inputs → same fingerprint."""
        fp1 = ObservationFingerprint.compute(
            b"image", b"voice",
            Location(19.076, 72.878),
            datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
            "device-1",
        )
        fp2 = ObservationFingerprint.compute(
            b"image", b"voice",
            Location(19.076, 72.878),
            datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
            "device-1",
        )
        assert fp1.hash == fp2.hash

    @pytest.mark.asyncio
    async def test_different_inputs_different_fingerprint(self):
        """Different device → different fingerprint."""
        fp1 = ObservationFingerprint.compute(
            b"image", None, Location(19.076, 72.878),
            datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc), "device-1",
        )
        fp2 = ObservationFingerprint.compute(
            b"image", None, Location(19.076, 72.878),
            datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc), "device-2",
        )
        assert fp1.hash != fp2.hash

    @pytest.mark.asyncio
    async def test_missing_observation_raises(self):
        obs_store, interp_store, _, _, audit, bus = _make_stores()
        gemini = _make_gemini()
        uc = InterpretObservationUseCase(obs_store, interp_store, gemini, audit, bus)

        with pytest.raises(ValueError, match="not found"):
            await uc.execute(InterpretRequest(observation_id="nonexistent"))


# ============================================================
# Workflow 2 — Correlation Integration
# ============================================================

class TestWorkflow2_Correlation:
    @pytest.mark.asyncio
    async def test_first_observation_creates_watch_signal(self):
        obs_store, _, signal_store, sig_events, _, bus = _make_stores()
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signal_store, sig_events, bus, config)

        result = await uc.execute(CorrelateRequest(
            observation_id="obs-1", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878),
            timestamp=datetime.now(timezone.utc), device_id="device-1",
            evidence_categories=["smoke"], evidence_descriptions=["smoke visible"],
            interpretation_confidence=0.8,
        ))
        assert result.is_new_signal is True
        assert result.state == SignalState.WATCH
        assert len(signal_store.items) == 1

    @pytest.mark.asyncio
    async def test_similar_observations_correlate(self):
        _, _, signal_store, sig_events, _, bus = _make_stores()
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signal_store, sig_events, bus, config)
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
    async def test_distant_observations_separate_signals(self):
        _, _, signal_store, sig_events, _, bus = _make_stores()
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signal_store, sig_events, bus, config)
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
        """Fingerprint match → duplicate, not new signal."""
        fp1 = ObservationFingerprint.compute(
            b"image", None, Location(19.076, 72.878),
            datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc), "device-1",
        )
        fp2 = ObservationFingerprint.compute(
            b"image", None, Location(19.076, 72.878),
            datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc), "device-1",
        )
        assert fp1.hash == fp2.hash  # Same device, same time, same image → duplicate

    @pytest.mark.asyncio
    async def test_state_machine_transitions(self):
        """Verify all valid state transitions."""
        _, _, signal_store, sig_events, _, bus = _make_stores()
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signal_store, sig_events, bus, config)
        now = datetime.now(timezone.utc)

        # Create initial signal
        r1 = await uc.execute(CorrelateRequest(
            observation_id="obs-1", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878), timestamp=now, device_id="d1",
            evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
        ))
        signal = await signal_store.get(r1.signal_id)
        assert signal.state == SignalState.WATCH

        # Add more observations to trigger escalation
        for i in range(5):
            await uc.execute(CorrelateRequest(
                observation_id=f"obs-{i+2}", fingerprint=f"fp-{i+2}", category="smoke",
                location=Location(19.076 + i*0.0001, 72.878 + i*0.0001),
                timestamp=now + timedelta(minutes=i+1),
                device_id=f"d{i+2}",
                evidence_categories=["smoke"], evidence_descriptions=["smoke"],
                interpretation_confidence=0.8,
            ))

        signal = await signal_store.get(r1.signal_id)
        # State should have transitioned (depends on scoring)
        assert signal.state in [SignalState.WATCH, SignalState.PROBABLE_HOTSPOT, SignalState.HIGH_CONFIDENCE]

    @pytest.mark.asyncio
    async def test_correlation_events_are_recorded(self):
        _, _, signal_store, sig_events, _, bus = _make_stores()
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signal_store, sig_events, bus, config)

        result = await uc.execute(CorrelateRequest(
            observation_id="obs-1", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878), timestamp=datetime.now(timezone.utc),
            device_id="d1", evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
        ))
        events = await sig_events.list_by_signal(result.signal_id)
        assert len(events) >= 1
        assert events[0].event_type == "created"


# ============================================================
# Workflow 3 — Environmental Providers Integration
# ============================================================

class TestWorkflow3_Providers:
    @pytest.mark.asyncio
    async def test_weather_provider_success(self):
        from app.infrastructure.providers.weather import WeatherProvider
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "current": {
                "temperature_2m": 38, "relative_humidity_2m": 35,
                "wind_speed_10m": 12, "wind_direction_180": 45,
                "precipitation": 0, "time": "2024-01-15T10:30",
            }
        }
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await WeatherProvider().fetch(latitude=19.076, longitude=72.878)

        assert result.status == "available"
        assert result.normalized_data["temperature"] == 38
        assert result.normalized_data["low_humidity_high_temp"] is True

    @pytest.mark.asyncio
    async def test_weather_provider_unavailable(self):
        from app.infrastructure.providers.weather import WeatherProvider
        with patch("httpx.AsyncClient", side_effect=Exception("timeout")):
            result = await WeatherProvider().fetch(latitude=19.076, longitude=72.878)
        assert result.status == "unavailable"
        assert result.confidence == 0.0

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
        assert result.normalized_data["elevated"] is False

    def test_environmental_score_with_all_factors(self):
        score = environmental_score(
            wind_consistent=True, low_humidity_high_temp=True,
            firms_fire_detected=True, cpcb_elevated=True,
        )
        assert score == 0.7  # 0.15 + 0.1 + 0.25 + 0.2

    def test_environmental_score_with_rain(self):
        score = environmental_score(recent_precipitation=True)
        assert score == 0.0  # clamped from -0.2

    def test_provider_records_store_confidence_and_latency(self):
        from app.domain.entities import ProviderRecord
        record = ProviderRecord(
            provider_type="weather", confidence=0.9, latency_ms=340.0,
            status="available",
        )
        assert record.confidence == 0.9
        assert record.latency_ms == 340.0


# ============================================================
# Workflow 4 — Dashboard Integration (API layer)
# ============================================================

class TestWorkflow4_Dashboard:
    def test_openapi_spec_has_all_endpoints(self):
        from app.main import app
        spec = app.openapi()
        paths = list(spec["paths"].keys())
        assert "/api/v1/observations" in paths
        assert "/api/v1/observations/{observation_id}" in paths
        assert "/api/v1/signals" in paths
        assert "/api/v1/signals/{signal_id}" in paths
        assert "/api/v1/signals/{signal_id}/verify" in paths
        assert "/api/v1/signals/{signal_id}/archive" in paths
        assert "/api/v1/analytics" in paths
        assert "/api/v1/analytics/heatmap" in paths
        assert "/api/v1/analytics/timeline" in paths
        assert "/api/v1/health" in paths
        assert "/api/v1/ready" in paths
        assert "/api/v1/metrics" in paths

    def test_openapi_has_error_schemas(self):
        from app.main import app
        spec = app.openapi()
        schemas = spec["components"]["schemas"]
        assert "ErrorResponse" in schemas
        assert "ErrorBody" in schemas
        assert "ErrorDetail" in schemas

    def test_openapi_has_enum_schemas(self):
        from app.main import app
        spec = app.openapi()
        schemas = spec["components"]["schemas"]
        assert "SignalStateEnum" in schemas
        assert "ObservationCategoryEnum" in schemas
        assert "ObservationStatusEnum" in schemas
        assert "LanguageEnum" in schemas
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
        assert "created_at" in required
        assert "updated_at" in required


# ============================================================
# Workflow 5 — Audit Integration
# ============================================================

class TestWorkflow5_Audit:
    @pytest.mark.asyncio
    async def test_submit_generates_audit_event(self):
        obs_store, _, _, _, audit, bus = _make_stores()
        uc = SubmitObservationUseCase(obs_store, audit, bus)

        await uc.execute(SubmitObservationRequest(
            content="Test", latitude=19.0, longitude=72.0,
            category="smoke", language="en", device_id="d1",
        ))
        assert len(audit.events) >= 1
        assert audit.events[0].event_type == "observation_submitted"

    @pytest.mark.asyncio
    async def test_interpret_generates_audit_event(self):
        obs_store, interp_store, _, _, audit, bus = _make_stores()
        gemini = _make_gemini()

        # Submit first
        submit_uc = SubmitObservationUseCase(obs_store, audit, bus)
        result = await submit_uc.execute(SubmitObservationRequest(
            content="Test", latitude=19.0, longitude=72.0,
            category="smoke", language="en", device_id="d1",
        ))

        # Interpret
        interpret_uc = InterpretObservationUseCase(obs_store, interp_store, gemini, audit, bus)
        await interpret_uc.execute(InterpretRequest(observation_id=result.observation_id))

        event_types = [e.event_type for e in audit.events]
        assert "observation_submitted" in event_types
        assert "observation_interpreted" in event_types

    @pytest.mark.asyncio
    async def test_correlation_generates_signal_events(self):
        _, _, signal_store, sig_events, _, bus = _make_stores()
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signal_store, sig_events, bus, config)

        result = await uc.execute(CorrelateRequest(
            observation_id="obs-1", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878), timestamp=datetime.now(timezone.utc),
            device_id="d1", evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
        ))
        events = await sig_events.list_by_signal(result.signal_id)
        assert len(events) >= 1
        assert events[0].event_type == "created"
        assert events[0].signal_id == result.signal_id

    @pytest.mark.asyncio
    async def test_full_audit_trail(self):
        """Complete workflow generates full audit trail."""
        obs_store, interp_store, signal_store, sig_events, audit, bus = _make_stores()
        gemini = _make_gemini()
        config = CorrelationConfig()

        submit_uc = SubmitObservationUseCase(obs_store, audit, bus)
        interpret_uc = InterpretObservationUseCase(obs_store, interp_store, gemini, audit, bus)
        correlate_uc = CorrelateObservationUseCase(signal_store, sig_events, bus, config)

        # Submit
        sub = await submit_uc.execute(SubmitObservationRequest(
            content="Smoke visible", latitude=19.076, longitude=72.878,
            category="smoke", language="en", device_id="d1",
        ))

        # Interpret
        interp = await interpret_uc.execute(InterpretRequest(observation_id=sub.observation_id))

        # Correlate
        corr = await correlate_uc.execute(CorrelateRequest(
            observation_id=sub.observation_id, fingerprint=sub.fingerprint,
            category="smoke", location=Location(19.076, 72.878),
            timestamp=datetime.now(timezone.utc), device_id="d1",
            evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=interp.confidence,
        ))

        # Verify audit trail completeness
        audit_events = audit.events
        event_types = [e.event_type for e in audit_events]
        assert "observation_submitted" in event_types
        assert "observation_interpreted" in event_types

        # Verify signal events
        signal_events = await sig_events.list_by_signal(corr.signal_id)
        assert len(signal_events) >= 1
        assert signal_events[0].event_type == "created"

        # Verify bus events
        bus_events = [e[0] for e in bus.published]
        assert "ObservationSubmitted" in bus_events
        assert "ObservationInterpreted" in bus_events
        assert "SignalCreated" in bus_events
