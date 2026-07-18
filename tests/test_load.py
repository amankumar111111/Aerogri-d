"""Load Testing — Simulate concurrent submissions.

Run with: python -m pytest tests/test_load.py -v -s

Measures throughput, latency, and correctness under concurrent load.
"""

from __future__ import annotations

import asyncio
import time
import pytest

from app.application.submit_observation import SubmitObservationRequest, SubmitObservationUseCase
from app.application.correlate_observation import CorrelateRequest, CorrelateObservationUseCase
from app.domain.policies import CorrelationConfig
from app.domain.ports import AuditLog, EventBus, SignalEventStore, SignalStore
from app.domain.value_objects import Location

# --- Reuse test doubles from test_end_to_end ---
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


class InMemoryObs:
    def __init__(self):
        self.items = {}
    async def save(self, o):
        self.items[o.id] = o
    async def get(self, id):
        return self.items.get(id)
    async def list_(self, *, offset=0, limit=20):
        return list(self.items.values())[offset:offset+limit]
    async def count(self):
        return len(self.items)


class InMemorySignal:
    def __init__(self):
        self.items = {}
    async def save(self, s):
        self.items[s.id] = s
    async def get(self, id):
        return self.items.get(id)
    async def list_(self, *, state=None, offset=0, limit=20):
        items = list(self.items.values())
        if state:
            items = [s for s in items if s.state.value == state]
        return items[offset:offset+limit]
    async def count(self, *, state=None):
        return len(self.items)


class InMemorySigEvent:
    def __init__(self):
        self.events = []
        self._seq = {}
    async def save(self, e):
        self.events.append(e)
    async def list_by_signal(self, sid):
        return [e for e in self.events if e.signal_id == sid]
    async def next_sequence(self, sid):
        self._seq[sid] = self._seq.get(sid, 0) + 1
        return self._seq[sid]


class InMemoryAudit:
    def __init__(self):
        self.events = []
    async def append(self, e):
        self.events.append(e)
    async def list_by_signal(self, sid):
        return []


class InMemoryBus:
    def __init__(self):
        self.published = []
    async def publish(self, et, p):
        self.published.append((et, p))
    async def subscribe(self, et):
        yield {}


@pytest.mark.asyncio
async def test_100_concurrent_submissions():
    """100 concurrent observation submissions — measure throughput."""
    from datetime import datetime, timezone

    obs_store = InMemoryObs()
    audit = InMemoryAudit()
    bus = InMemoryBus()
    uc = SubmitObservationUseCase(obs_store, audit, bus)

    start = time.monotonic()

    async def submit_one(i: int):
        return await uc.execute(SubmitObservationRequest(
            content=f"Observation {i}",
            latitude=19.0 + (i * 0.001),
            longitude=72.0 + (i * 0.001),
            category="smoke",
            language="en",
            device_id=f"device-{i}",
        ))

    results = await asyncio.gather(*[submit_one(i) for i in range(100)])

    elapsed = time.monotonic() - start
    throughput = len(results) / elapsed

    assert len(results) == 100
    assert len(obs_store.items) == 100
    assert all(r.status == "submitted" for r in results)
    print(f"\n  100 submissions: {elapsed:.3f}s ({throughput:.0f} obs/sec)")


@pytest.mark.asyncio
async def test_100_concurrent_correlations():
    """100 concurrent correlation evaluations — measure signal creation."""
    from datetime import datetime, timezone

    signal_store = InMemorySignal()
    sig_events = InMemorySigEvent()
    bus = InMemoryBus()
    config = CorrelationConfig()
    uc = CorrelateObservationUseCase(signal_store, sig_events, bus, config)

    start = time.monotonic()

    async def correlate_one(i: int):
        return await uc.execute(CorrelateRequest(
            observation_id=f"obs-{i}", fingerprint=f"fp-{i}",
            category="smoke",
            location=Location(19.0 + (i * 0.001), 72.0 + (i * 0.001)),
            timestamp=datetime.now(timezone.utc),
            device_id=f"device-{i}",
            evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
        ))

    results = await asyncio.gather(*[correlate_one(i) for i in range(100)])

    elapsed = time.monotonic() - start
    throughput = len(results) / elapsed

    assert len(results) == 100
    print(f"\n  100 correlations: {elapsed:.3f}s ({throughput:.0f} corr/sec)")
    print(f"  Signals created: {len(signal_store.items)}")


@pytest.mark.asyncio
async def test_mixed_load():
    """Mixed workload: 50 submissions + 50 correlations concurrently."""
    from datetime import datetime, timezone

    obs_store = InMemoryObs()
    signal_store = InMemorySignal()
    sig_events = InMemorySigEvent()
    audit = InMemoryAudit()
    bus = InMemoryBus()
    config = CorrelationConfig()

    submit_uc = SubmitObservationUseCase(obs_store, audit, bus)
    correlate_uc = CorrelateObservationUseCase(signal_store, sig_events, bus, config)

    start = time.monotonic()

    async def submit(i):
        return await submit_uc.execute(SubmitObservationRequest(
            content=f"Obs {i}", latitude=19.0 + i * 0.001, longitude=72.0 + i * 0.001,
            category="smoke", language="en", device_id=f"d{i}",
        ))

    async def correlate(i):
        return await correlate_uc.execute(CorrelateRequest(
            observation_id=f"obs-{i}", fingerprint=f"fp-{i}", category="smoke",
            location=Location(19.0 + i * 0.001, 72.0 + i * 0.001),
            timestamp=datetime.now(timezone.utc), device_id=f"d{i}",
            evidence_categories=["smoke"], evidence_descriptions=["smoke"],
            interpretation_confidence=0.8,
        ))

    results = await asyncio.gather(
        *[submit(i) for i in range(50)],
        *[correlate(i) for i in range(50, 100)],
    )

    elapsed = time.monotonic() - start
    print(f"\n  Mixed load (50 submit + 50 correlate): {elapsed:.3f}s")
    print(f"  Observations: {len(obs_store.items)}, Signals: {len(signal_store.items)}")

    assert len(results) == 100
    assert len(obs_store.items) == 50
    assert len(signal_store.items) > 0
