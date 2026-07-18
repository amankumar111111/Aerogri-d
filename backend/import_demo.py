"""Import demo data through the actual system pipeline.

Run: python -m import_demo

Feeds observations through: Submit → Gemini (mocked) → Correlate → Signal
Demonstrates the full workflow with realistic data.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.application.submit_observation import SubmitObservationRequest, SubmitObservationUseCase
from app.application.interpret_observation import InterpretRequest, InterpretObservationUseCase
from app.application.correlate_observation import CorrelateRequest, CorrelateObservationUseCase
from app.domain.policies import CorrelationConfig
from app.domain.ports import (
    AuditLog, EventBus, InterpretationStore, ObservationInterpreter,
    ObservationStore, SignalEventStore, SignalStore,
)
from app.domain.value_objects import Location, SignalState
from app.domain.entities import Observation, Interpretation


# --- In-memory stores (for demo without database) ---

class MemObs:
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

class MemInterp:
    def __init__(self):
        self.items = {}
    async def save(self, i):
        self.items[i.id] = i
    async def get_by_observation(self, oid):
        for i in self.items.values():
            if i.observation_id == oid:
                return i
        return None

class MemSignal:
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
        if state:
            return sum(1 for s in self.items.values() if s.state.value == state)
        return len(self.items)

class MemSigEvent:
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

class MemAudit:
    def __init__(self):
        self.events = []
    async def append(self, e):
        self.events.append(e)
    async def list_by_signal(self, sid):
        return []

class MemBus:
    def __init__(self):
        self.published = []
    async def publish(self, et, p):
        self.published.append((et, p))
    async def subscribe(self, et):
        yield {}


# --- Mock Gemini (interprets based on category) ---

CATEGORY_INTERPRETATIONS = {
    "smoke": {
        "categories": ["smoke"],
        "evidence_descriptions": ["visible smoke plume", "combustion odor detected"],
        "severity": {"level": "high", "indicators": ["thick smoke", "strong odor"]},
        "citizen_category_alignment": True,
        "confidence": 0.85,
    },
    "dust": {
        "categories": ["dust"],
        "evidence_descriptions": ["particulate matter visible", "reduced visibility"],
        "severity": {"level": "medium", "indicators": ["dust cloud", "visibility reduction"]},
        "citizen_category_alignment": True,
        "confidence": 0.80,
    },
    "construction_dust": {
        "categories": ["construction_dust", "dust"],
        "evidence_descriptions": ["construction-related dust", "particulate from building site"],
        "severity": {"level": "medium", "indicators": ["construction activity", "dust cloud"]},
        "citizen_category_alignment": True,
        "confidence": 0.82,
    },
    "chemical": {
        "categories": ["chemical"],
        "evidence_descriptions": ["chemical odor detected", "possible chemical release"],
        "severity": {"level": "high", "indicators": ["strong chemical odor", "potential hazard"]},
        "citizen_category_alignment": True,
        "confidence": 0.78,
    },
}

class MockGemini(ObservationInterpreter):
    async def interpret(self, image_bytes, voice_bytes, text, citizen_category):
        response = CATEGORY_INTERPRETATIONS.get(citizen_category, {
            "categories": [citizen_category],
            "evidence_descriptions": [f"citizen reported {citizen_category}"],
            "severity": {"level": "low", "indicators": ["citizen report"]},
            "citizen_category_alignment": True,
            "confidence": 0.6,
        })
        return {
            **response,
            "_meta": {"model": "gemini-2.0-flash", "prompt_version": "v3.2", "schema_version": "v2.1"},
        }


STATE_COLORS = {
    "watch": "\033[94m",           # Blue
    "probable_hotspot": "\033[93m", # Amber
    "high_confidence": "\033[91m",  # Red
    "archived": "\033[90m",         # Gray
}
RESET = "\033[0m"


async def main():
    print("=" * 70)
    print("AEROGRID Demo — Full Pipeline Import")
    print("=" * 70)

    # Setup stores
    obs_store = MemObs()
    interp_store = MemInterp()
    signal_store = MemSignal()
    sig_events = MemSigEvent()
    audit = MemAudit()
    bus = MemBus()
    gemini = MockGemini()
    config = CorrelationConfig()

    # Create use cases
    submit_uc = SubmitObservationUseCase(obs_store, audit, bus)
    interpret_uc = InterpretObservationUseCase(obs_store, interp_store, gemini, audit, bus)
    correlate_uc = CorrelateObservationUseCase(signal_store, sig_events, bus, config)

    # Load demo data
    data_file = Path(__file__).parent / "demo_data.json"
    with open(data_file, encoding="utf-8") as f:
        observations = json.load(f)

    print(f"\nProcessing {len(observations)} observations...\n")

    results = []

    for i, obs_data in enumerate(observations):
        obs_time = datetime.now(timezone.utc) - timedelta(minutes=obs_data["minutes_ago"])

        # Step 1: Submit
        sub = await submit_uc.execute(SubmitObservationRequest(
            content=obs_data["content"],
            latitude=obs_data["latitude"],
            longitude=obs_data["longitude"],
            category=obs_data["category"],
            language=obs_data["language"],
            device_id=obs_data["device_id"],
        ))

        # Step 2: Interpret
        interp = await interpret_uc.execute(InterpretRequest(observation_id=sub.observation_id))

        # Get full interpretation for evidence descriptions
        interp_entity = await interp_store.get_by_observation(sub.observation_id)
        evidence_descs = interp_entity.evidence_descriptions if interp_entity else []

        # Step 3: Correlate
        corr = await correlate_uc.execute(CorrelateRequest(
            observation_id=sub.observation_id,
            fingerprint=sub.fingerprint,
            category=obs_data["category"],
            location=Location(obs_data["latitude"], obs_data["longitude"]),
            timestamp=obs_time,
            device_id=obs_data["device_id"],
            evidence_categories=interp.categories,
            evidence_descriptions=evidence_descs,
            interpretation_confidence=interp.confidence,
        ))

        signal = await signal_store.get(corr.signal_id)
        color = STATE_COLORS.get(signal.state.value, "")
        results.append({
            "device": obs_data["device_id"],
            "category": obs_data["category"],
            "signal_id": corr.signal_id[:8],
            "state": signal.state.value,
            "confidence": f"{signal.confidence.value:.0%}",
            "observations": len(signal.contributing_observation_ids),
        })

        print(f"  [{i+1:>2}/{len(observations)}] {obs_data['category']:20s} → "
              f"Signal {corr.signal_id[:8]}... {color}{signal.state.value}{RESET} "
              f"({signal.confidence.value:.0%}, {len(signal.contributing_observation_ids)} obs)")

    # Summary
    print(f"\n{'=' * 70}")
    print("DEMO RESULTS")
    print(f"{'=' * 70}\n")

    signals = await signal_store.list_(limit=100)
    for sig in signals:
        color = STATE_COLORS.get(sig.state.value, "")
        print(f"  {color}●{RESET} {sig.state.value:20s} | {sig.category:20s} | "
              f"{sig.confidence.value:.0%} confidence | {len(sig.contributing_observation_ids)} observations")

    print(f"\n{'=' * 70}")
    print(f"Total: {len(signals)} signals from {len(observations)} observations")
    print(f"  Watch:              {await signal_store.count(state='watch')}")
    print(f"  Probable Hotspot:   {await signal_store.count(state='probable_hotspot')}")
    print(f"  High Confidence:    {await signal_store.count(state='high_confidence')}")
    print(f"  Archived:           {await signal_store.count(state='archived')}")
    print(f"  Audit events:       {len(audit.events)}")
    print(f"  Bus events:         {len(bus.published)}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
