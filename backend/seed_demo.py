"""Seed realistic demo data for AEROGRID.

Run: python -m seed_demo

Observations are placed within 500m of each other (the correlation radius)
to demonstrate the engine's behavior correctly.

Scenarios:
- A: Smoke event (4 observations within 300m → High Confidence)
- B: Dust event (3 observations within 400m → Probable Hotspot)
- C: False positive (1 observation, 2km away → stays Watch)
- D: Duplicate (same device, same time, same coords → detected)
- E: Multi-category (chemical + smoke within 200m → correlated)
"""

from __future__ import annotations

import asyncio
import json
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))


def jitter(base: float, meters: float = 100) -> float:
    return base + (random.uniform(-1, 1) * meters / 111000)


# --- Scenario A: Smoke in Kharadi (all within 300m) ---
SCENARIO_A = [
    {"content": "Thick black smoke rising from behind the factory near Kharadi bridge.",
     "latitude": jitter(18.6820, 80), "longitude": jitter(73.9480, 80),
     "category": "smoke", "language": "en", "device_id": "demo-001", "minutes_ago": 25},
    {"content": "कारखान्याजवळ मोठा धूर दिसत आहे. काल्या धूराचा गुळा उठत आहे.",
     "latitude": jitter(18.6822, 60), "longitude": jitter(73.9482, 60),
     "category": "smoke", "language": "mr", "device_id": "demo-002", "minutes_ago": 20},
    {"content": "Heavy smoke from Kharadi industrial area. Smells like burning plastic.",
     "latitude": jitter(18.6818, 120), "longitude": jitter(73.9485, 120),
     "category": "smoke", "language": "en", "device_id": "demo-003", "minutes_ago": 15},
    {"content": "फॅक्टरीच्या मागे मोठा धूर आहे. वास येत आहे बर्निंग प्लास्टिकचा.",
     "latitude": jitter(18.6824, 90), "longitude": jitter(73.9478, 90),
     "category": "smoke", "language": "hi", "device_id": "demo-004", "minutes_ago": 10},
]

# --- Scenario B: Dust in Baner (all within 400m, different area) ---
SCENARIO_B = [
    {"content": "Dusty conditions near the construction site on Baner Road. Visibility poor.",
     "latitude": jitter(18.5590, 70), "longitude": jitter(73.7868, 70),
     "category": "dust", "language": "en", "device_id": "demo-005", "minutes_ago": 40},
    {"content": "Construction dust covering the entire street. Cars with headlights on.",
     "latitude": jitter(18.5593, 50), "longitude": jitter(73.7870, 50),
     "category": "construction_dust", "language": "en", "device_id": "demo-006", "minutes_ago": 30},
    {"content": "बानेर रोडवर धुळीचा गाढा ढग आहे. बिल्डिंग साईटवरून धूर येत आहे.",
     "latitude": jitter(18.5588, 100), "longitude": jitter(73.7865, 100),
     "category": "dust", "language": "mr", "device_id": "demo-007", "minutes_ago": 25},
]

# --- Scenario C: False positive in Kothrud (2km+ away from everything) ---
SCENARIO_C = [
    {"content": "Slight smoky smell near the vegetable market. Might be someone burning waste.",
     "latitude": 18.5074, "longitude": 73.8077,
     "category": "smoke", "language": "en", "device_id": "demo-008", "minutes_ago": 35},
]

# --- Scenario D: Duplicate detection (same device, same time, same coords) ---
SCENARIO_D = [
    {"content": "Chemical smell near the industrial estate in Kharadi.",
     "latitude": 18.6830, "longitude": 73.9470,
     "category": "chemical", "language": "en", "device_id": "demo-dup", "minutes_ago": 18},
    {"content": "Chemical smell near the industrial estate in Kharadi.",
     "latitude": 18.6830, "longitude": 73.9470,
     "category": "chemical", "language": "en", "device_id": "demo-dup", "minutes_ago": 18},
]

# --- Scenario E: Multi-category in Hadapsar (chemical + smoke within 200m) ---
SCENARIO_E = [
    {"content": "Chemical odor near the water treatment plant in Hadapsar.",
     "latitude": jitter(18.5020, 80), "longitude": jitter(73.9430, 80),
     "category": "chemical", "language": "en", "device_id": "demo-009", "minutes_ago": 22},
    {"content": "Smoke visible near Hadapsar water treatment. Strong chemical smell.",
     "latitude": jitter(18.5023, 60), "longitude": jitter(73.9433, 60),
     "category": "smoke", "language": "en", "device_id": "demo-010", "minutes_ago": 18},
]

ALL_SCENARIOS = [
    ("Scenario A: Smoke Event (Kharadi)", SCENARIO_A),
    ("Scenario B: Dust Event (Baner)", SCENARIO_B),
    ("Scenario C: False Positive (Kothrud)", SCENARIO_C),
    ("Scenario D: Duplicate Detection", SCENARIO_D),
    ("Scenario E: Multi-Category (Hadapsar)", SCENARIO_E),
]


def main():
    print("=" * 60)
    print("AEROGRID Demo Data Seeder")
    print("=" * 60)

    all_observations = []
    for name, scenarios in ALL_SCENARIOS:
        print(f"\n{name}:")
        for obs in scenarios:
            all_observations.append(obs)
            print(f"  {obs['category']:20s} | {obs['language']} | {obs['device_id']} | {obs['minutes_ago']:>3} min ago")

    output_file = Path(__file__).parent / "demo_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_observations, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"Generated {len(all_observations)} observations → {output_file}")
    print(f"\nExpected after import:")
    print(f"  Scenario A: 4 smoke obs → High Confidence signal")
    print(f"  Scenario B: 3 dust obs → Probable Hotspot signal")
    print(f"  Scenario C: 1 smoke obs → Watch signal (isolated)")
    print(f"  Scenario D: 2 identical obs → Duplicate detected")
    print(f"  Scenario E: 2 multi-category obs → Correlated signal")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
