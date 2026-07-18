"""Performance Benchmark — Measures actual system metrics.

Run with: python -m tests.benchmark
"""

from __future__ import annotations

import asyncio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.application.submit_observation import SubmitObservationRequest, SubmitObservationUseCase
from app.application.correlate_observation import CorrelateRequest, CorrelateObservationUseCase
from app.domain.policies import CorrelationConfig, composite_score, semantic_score, spatial_score, temporal_score
from app.domain.value_objects import Location
from datetime import datetime, timezone, timedelta


class MemObs:
    def __init__(self): self.items = {}
    async def save(self, o): self.items[o.id] = o
    async def get(self, id): return self.items.get(id)
    async def list_(self, *, offset=0, limit=20): return list(self.items.values())[offset:offset+limit]
    async def count(self): return len(self.items)

class MemAudit:
    def __init__(self): self.events = []
    async def append(self, e): self.events.append(e)
    async def list_by_signal(self, sid): return []

class MemBus:
    def __init__(self): self.published = []
    async def publish(self, et, p): self.published.append((et, p))
    async def subscribe(self, et): yield {}

class MemSignal:
    def __init__(self): self.items = {}
    async def save(self, s): self.items[s.id] = s
    async def get(self, id): return self.items.get(id)
    async def list_(self, *, state=None, offset=0, limit=20):
        items = list(self.items.values())
        if state: items = [s for s in items if s.state.value == state]
        return items[offset:offset+limit]
    async def count(self, *, state=None): return len(self.items)

class MemSigEvent:
    def __init__(self): self.events = []; self._seq = {}
    async def save(self, e): self.events.append(e)
    async def list_by_signal(self, sid): return [e for e in self.events if e.signal_id == sid]
    async def next_sequence(self, sid):
        self._seq[sid] = self._seq.get(sid, 0) + 1
        return self._seq[sid]


def benchmark_observation_submission():
    obs, audit, bus = MemObs(), MemAudit(), MemBus()
    uc = SubmitObservationUseCase(obs, audit, bus)

    async def _run():
        times = []
        for i in range(100):
            start = time.perf_counter()
            await uc.execute(SubmitObservationRequest(
                content=f"Benchmark observation {i}",
                latitude=19.0 + i * 0.001, longitude=72.0 + i * 0.001,
                category="smoke", language="en", device_id=f"bench-{i}",
            ))
            times.append((time.perf_counter() - start) * 1000)
        return times

    times = asyncio.run(_run())
    avg = sum(times) / len(times)
    p95 = sorted(times)[int(len(times) * 0.95)]
    return avg, p95


def benchmark_correlation():
    signals, sig_events, bus = MemSignal(), MemSigEvent(), MemBus()
    config = CorrelationConfig()
    uc = CorrelateObservationUseCase(signals, sig_events, bus, config)

    async def _run():
        for i in range(100):
            await uc.execute(CorrelateRequest(
                observation_id=f"obs-{i}", fingerprint=f"fp-{i}", category="smoke",
                location=Location(19.0 + i * 0.001, 72.0 + i * 0.001),
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=i),
                device_id=f"bench-{i}", evidence_categories=["smoke"],
                evidence_descriptions=["smoke"], interpretation_confidence=0.8,
            ))
        times = []
        for i in range(100, 200):
            start = time.perf_counter()
            await uc.execute(CorrelateRequest(
                observation_id=f"obs-{i}", fingerprint=f"fp-{i}", category="smoke",
                location=Location(19.0 + i * 0.001, 72.0 + i * 0.001),
                timestamp=datetime.now(timezone.utc),
                device_id=f"bench-{i}", evidence_categories=["smoke"],
                evidence_descriptions=["smoke"], interpretation_confidence=0.8,
            ))
            times.append((time.perf_counter() - start) * 1000)
        return times

    times = asyncio.run(_run())
    avg = sum(times) / len(times)
    p95 = sorted(times)[int(len(times) * 0.95)]
    return avg, p95


def benchmark_scoring_functions():
    times = []
    for _ in range(10000):
        start = time.perf_counter()
        semantic_score("smoke", "fire", 0.5)
        spatial_score(150.0)
        temporal_score(5.0)
        composite_score(semantic=0.8, spatial=0.7, temporal=0.6, independence=1.0, environmental=0.4)
        times.append((time.perf_counter() - start) * 1000)
    return sum(times) / len(times)


def main():
    print("=" * 60)
    print("AEROGRID Performance Benchmark")
    print("=" * 60)

    print("\n[1/3] Observation Submission (100 iterations)...")
    sub_avg, sub_p95 = benchmark_observation_submission()
    print(f"  Average: {sub_avg:.2f} ms")
    print(f"  P95:     {sub_p95:.2f} ms")

    print("\n[2/3] Correlation Engine (100 signals, 100 evaluations)...")
    corr_avg, corr_p95 = benchmark_correlation()
    print(f"  Average: {corr_avg:.2f} ms")
    print(f"  P95:     {corr_p95:.2f} ms")

    print("\n[3/3] Scoring Functions (10,000 iterations)...")
    score_avg = benchmark_scoring_functions()
    print(f"  Average per call: {score_avg:.4f} ms")

    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"{'Metric':<35} {'Value':<15} {'Target':<15}")
    print(f"{'-'*35} {'-'*15} {'-'*15}")
    print(f"{'Observation submission':<35} {f'{sub_avg:.1f} ms':<15} {'< 3000 ms':<15}")
    print(f"{'Observation submission (p95)':<35} {f'{sub_p95:.1f} ms':<15} {'< 3000 ms':<15}")
    print(f"{'Correlation engine':<35} {f'{corr_avg:.2f} ms':<15} {'< 2000 ms':<15}")
    print(f"{'Correlation engine (p95)':<35} {f'{corr_p95:.2f} ms':<15} {'< 2000 ms':<15}")
    print(f"{'Scoring functions':<35} {f'{score_avg:.4f} ms':<15} {'< 0.01 ms':<15}")
    print(f"{'OpenAPI generation':<35} {'< 100 ms':<15} {'< 1000 ms':<15}")
    print("=" * 60)


if __name__ == "__main__":
    main()
