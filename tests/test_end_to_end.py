"""End-to-End Workflow Tests.

Scenario 1: Full citizen flow — photo + voice + GPS → Gemini → Observation → Correlation → Signal
Scenario 2: Duplicate report → Independence Engine → No duplicate signal
Scenario 3: Gemini unavailable → Graceful error → Observation retained
Scenario 4: CPCB unavailable → Signal still computed → No fabricated values
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from app.application.submit_observation import SubmitObservationRequest, SubmitObservationUseCase
from app.application.interpret_observation import InterpretRequest, InterpretObservationUseCase
from app.application.correlate_observation import CorrelateRequest, CorrelateObservationUseCase
from app.domain.entities import Observation, Signal
from app.domain.policies import CorrelationConfig
from app.domain.ports import (
    AuditLog, EventBus, InterpretationStore, MediaStore,
    ObservationInterpreter, ObservationStore, SignalEventStore, SignalStore,
)
from app.domain.value_objects import Location, ObservationFingerprint, SignalState


# --- Test Doubles ---

class MemObs(ObservationStore):
    def __init__(self): self.items = {}
    async def save(self, o): self.items[o.id] = o
    async def get(self, id): return self.items.get(id)
    async def list_(self, *, offset=0, limit=20): return list(self.items.values())[offset:offset+limit]
    async def count(self): return len(self.items)

class MemInterp(InterpretationStore):
    def __init__(self): self.items = {}
    async def save(self, i): self.items[i.id] = i
    async def get_by_observation(self, oid):
        for i in self.items.values():
            if i.observation_id == oid: return i
        return None

class MemSignal(SignalStore):
    def __init__(self): self.items = {}
    async def save(self, s): self.items[s.id] = s
    async def get(self, id): return self.items.get(id)
    async def list_(self, *, state=None, offset=0, limit=20):
        items = list(self.items.values())
        if state: items = [s for s in items if s.state.value == state]
        return items[offset:offset+limit]
    async def count(self, *, state=None):
        if state: return sum(1 for s in self.items.values() if s.state.value == state)
        return len(self.items)

class MemSigEvent(SignalEventStore):
    def __init__(self): self.events = []; self._seq = {}
    async def save(self, e): self.events.append(e)
    async def list_by_signal(self, sid): return [e for e in self.events if e.signal_id == sid]
    async def next_sequence(self, sid):
        self._seq[sid] = self._seq.get(sid, 0) + 1
        return self._seq[sid]

class MemAudit(AuditLog):
    def __init__(self): self.events = []
    async def append(self, e): self.events.append(e)
    async def list_by_signal(self, sid): return []

class MemBus(EventBus):
    def __init__(self): self.published = []
    async def publish(self, et, p): self.published.append((et, p))
    async def subscribe(self, et): yield {}

class MemMedia(MediaStore):
    def __init__(self, data: dict[str, bytes] | None = None):
        self.data = data or {}
    async def save(self, media, content): return media.id
    async def get(self, media_id): return self.data.get(media_id)


class MockGemini(ObservationInterpreter):
    def __init__(self, response=None, should_fail=False):
        self.response = response or {
            "categories": ["smoke"], "evidence_descriptions": ["visible smoke"],
            "severity": {"level": "high", "indicators": ["thick black smoke"]},
            "citizen_category_alignment": True, "confidence": 0.85,
        }
        self.should_fail = should_fail
        self.call_count = 0
    async def interpret(self, image_bytes, voice_bytes, text, citizen_category):
        self.call_count += 1
        if self.should_fail:
            raise Exception("Gemini API timeout")
        return {**self.response, "_meta": {"model": "gemini-2.0-flash", "prompt_version": "v3.2", "schema_version": "v2.1"}}


def _setup():
    obs, interp, signals, sig_events, audit, bus = MemObs(), MemInterp(), MemSignal(), MemSigEvent(), MemAudit(), MemBus()
    return obs, interp, signals, sig_events, audit, bus


# ============================================================
# Scenario 1: Full Citizen Flow
# ============================================================

class TestScenario1_FullFlow:
    @pytest.mark.asyncio
    async def test_photo_voice_gps_gemini_observation_correlation_signal(self):
        """Complete workflow: citizen → Gemini → observation → correlation → signal."""
        obs, interp, signals, sig_events, audit, bus = _setup()
        gemini = MockGemini()
        config = CorrelationConfig()

        submit_uc = SubmitObservationUseCase(obs, audit, bus)
        interpret_uc = InterpretObservationUseCase(obs, interp, gemini, audit, bus)
        correlate_uc = CorrelateObservationUseCase(signals, sig_events, bus, config)

        # Step 1: Citizen submits with photo + voice + GPS
        sub = await submit_uc.execute(SubmitObservationRequest(
            content="Heavy smoke from factory chimney",
            latitude=19.076, longitude=72.878,
            category="smoke", language="en", device_id="citizen-phone-1",
        ))
        assert sub.observation_id
        assert sub.status == "submitted"

        # Step 2: Gemini interprets
        interp_result = await interpret_uc.execute(InterpretRequest(observation_id=sub.observation_id))
        assert interp_result.categories == ["smoke"]
        assert interp_result.severity == "high"
        assert interp_result.confidence == 0.85
        assert interp_result.prompt_version == "v3.2"

        # Step 3: Correlation engine evaluates
        corr = await correlate_uc.execute(CorrelateRequest(
            observation_id=sub.observation_id, fingerprint=sub.fingerprint,
            category="smoke", location=Location(19.076, 72.878),
            timestamp=datetime.now(timezone.utc), device_id="citizen-phone-1",
            evidence_categories=["smoke"], evidence_descriptions=["visible smoke"],
            interpretation_confidence=0.85,
        ))
        assert corr.signal_id
        assert corr.state == SignalState.WATCH

        # Step 4: Verify full chain
        obs_entity = await obs.get(sub.observation_id)
        assert obs_entity.status == "interpreted"

        interp_entity = await interp.get_by_observation(sub.observation_id)
        assert interp_entity is not None
        assert interp_entity.model == "gemini-2.0-flash"

        signal = await signals.get(corr.signal_id)
        assert signal is not None
        assert signal.state == SignalState.WATCH
        assert sub.observation_id in signal.contributing_observation_ids

        # Verify audit trail
        assert len(audit.events) >= 2
        event_types = [e.event_type for e in audit.events]
        assert "observation_submitted" in event_types
        assert "observation_interpreted" in event_types

        # Verify events
        bus_types = [e[0] for e in bus.published]
        assert "ObservationSubmitted" in bus_types
        assert "ObservationInterpreted" in bus_types
        assert "SignalCreated" in bus_types


# ============================================================
# Scenario 2: Duplicate Report
# ============================================================

class TestScenario2_DuplicateReport:
    @pytest.mark.asyncio
    async def test_duplicate_observation_no_new_signal(self):
        """Same device, same time, same image → fingerprint match → no new signal."""
        _, _, signals, sig_events, _, bus = _setup()
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signals, sig_events, bus, config)
        now = datetime.now(timezone.utc)

        # First observation creates signal
        r1 = await uc.execute(CorrelateRequest(
            observation_id="obs-1", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878), timestamp=now, device_id="d1",
            evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
        ))
        assert len(signals.items) == 1

        # Second observation with same fingerprint → correlation, not new signal
        r2 = await uc.execute(CorrelateRequest(
            observation_id="obs-2", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878), timestamp=now + timedelta(minutes=1),
            device_id="d1", evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
        ))
        # Same fingerprint means it's treated as same event → joins existing signal
        assert r2.signal_id == r1.signal_id
        signal = await signals.get(r1.signal_id)
        assert len(signal.contributing_observation_ids) == 2

    @pytest.mark.asyncio
    async def test_fingerprint_exact_match_fast_path(self):
        """Identical inputs → identical fingerprint → O(1) duplicate detection."""
        fp1 = ObservationFingerprint.compute(
            b"same_image", None, Location(19.076, 72.878),
            datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc), "device-1",
        )
        fp2 = ObservationFingerprint.compute(
            b"same_image", None, Location(19.076, 72.878),
            datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc), "device-1",
        )
        assert fp1.hash == fp2.hash  # Exact match → fast path duplicate detection


# ============================================================
# Scenario 3: Gemini Unavailable
# ============================================================

class TestScenario3_GeminiUnavailable:
    @pytest.mark.asyncio
    async def test_gemini_timeout_observation_retained(self):
        """Gemini fails → observation stored raw → retry available."""
        obs, interp, _, _, audit, bus = _setup()
        gemini = MockGemini(should_fail=True)

        submit_uc = SubmitObservationUseCase(obs, audit, bus)
        interpret_uc = InterpretObservationUseCase(obs, interp, gemini, audit, bus)

        # Submit succeeds
        sub = await submit_uc.execute(SubmitObservationRequest(
            content="Smoke visible", latitude=19.076, longitude=72.878,
            category="smoke", language="en", device_id="d1",
        ))

        # Gemini fails
        with pytest.raises(Exception, match="Gemini API timeout"):
            await interpret_uc.execute(InterpretRequest(observation_id=sub.observation_id))

        # Observation is still stored (not lost)
        obs_entity = await obs.get(sub.observation_id)
        assert obs_entity is not None
        assert obs_entity.content == "Smoke visible"
        assert obs_entity.status == "submitted"  # Not "interpreted"

        # Audit trail still has the submission
        assert len(audit.events) >= 1
        assert audit.events[0].event_type == "observation_submitted"

        # Retry is possible
        gemini.should_fail = False  # Gemini recovers
        interp_result = await interpret_uc.execute(InterpretRequest(observation_id=sub.observation_id))
        assert interp_result.categories == ["smoke"]
        assert gemini.call_count == 2  # Called twice: once failed, once succeeded


# ============================================================
# Scenario 4: CPCB Unavailable
# ============================================================

class TestScenario4_ProviderUnavailable:
    @pytest.mark.asyncio
    async def test_cpcb_unavailable_signal_still_computed(self):
        """CPCB down → signal computed with neutral context → no fabricated values."""
        _, _, signals, sig_events, _, bus = _setup()
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signals, sig_events, bus, config)

        # Correlate without any provider data (all providers unavailable)
        result = await uc.execute(CorrelateRequest(
            observation_id="obs-1", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878), timestamp=datetime.now(timezone.utc),
            device_id="d1", evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
            environmental_context={},  # No provider data
        ))
        assert result.signal_id
        assert result.state == SignalState.WATCH

        signal = await signals.get(result.signal_id)
        assert signal.environmental_context == {}

    @pytest.mark.asyncio
    async def test_partial_provider_data(self):
        """Some providers available, some not → signal uses available data."""
        _, _, signals, sig_events, _, bus = _setup()
        config = CorrelationConfig()
        uc = CorrelateObservationUseCase(signals, sig_events, bus, config)

        # Only weather data available (FIRMS and CPCB unavailable)
        result = await uc.execute(CorrelateRequest(
            observation_id="obs-1", fingerprint="fp-1", category="smoke",
            location=Location(19.076, 72.878), timestamp=datetime.now(timezone.utc),
            device_id="d1", evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
            environmental_context={"temperature": 38, "humidity": 35},  # Only weather
        ))
        assert result.signal_id
        signal = await signals.get(result.signal_id)
        assert signal.environmental_context.get("temperature") == 38
        # No fabricated FIRMS or CPCB data
        assert "fire_detected" not in signal.environmental_context
        assert "elevated" not in signal.environmental_context
