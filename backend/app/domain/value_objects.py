"""Domain value objects — immutable, equality by value."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import ClassVar, Self


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    accuracy_meters: float | None = None

    def __post_init__(self) -> None:
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"latitude must be in [-90, 90], got {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"longitude must be in [-180, 180], got {self.longitude}")

    def distance_to(self, other: Self) -> float:
        """Haversine distance in meters."""
        R = 6371000
        lat1, lat2 = math.radians(self.latitude), math.radians(other.latitude)
        dlat = lat2 - lat1
        dlon = math.radians(other.longitude - self.longitude)
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def is_within(self, other: Self, radius_meters: float) -> bool:
        return self.distance_to(other) <= radius_meters

    def grid_bucket(self, precision: int = 3) -> str:
        """GPS coordinates truncated to `precision` decimal places (≈ 111m grid)."""
        return f"{self.latitude:.{precision}f},{self.longitude:.{precision}f}"


class SeverityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Severity:
    level: SeverityLevel
    indicators: tuple[str, ...] = ()

    def exceeds(self, other: Self) -> bool:
        order = [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        return order.index(self.level) > order.index(other.level)


class SourceType(Enum):
    CITIZEN = "citizen"
    SATELLITE = "satellite"
    GOVERNMENT = "government"
    WEATHER = "weather"


@dataclass(frozen=True)
class EvidenceWeight:
    source_type: SourceType
    reliability: float
    freshness_hours: float

    BASE_WEIGHTS: ClassVar[dict[SourceType, float]] = {
        SourceType.GOVERNMENT: 0.9,
        SourceType.SATELLITE: 0.85,
        SourceType.WEATHER: 0.8,
        SourceType.CITIZEN: 0.7,
    }

    def adjusted_weight(self, decay_lambda: float = 0.05) -> float:
        base = self.BASE_WEIGHTS.get(self.source_type, 0.5)
        return base * math.exp(-decay_lambda * self.freshness_hours)


class SignalState(Enum):
    WATCH = "watch"
    PROBABLE_HOTSPOT = "probable_hotspot"
    HIGH_CONFIDENCE = "high_confidence"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class ConfidenceScore:
    value: float
    dimensions: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.value}")

    def meets_threshold(self, threshold: float) -> bool:
        return self.value >= threshold

    def classification(self, thresholds: dict[str, float] | None = None) -> SignalState:
        t = thresholds or {"watch": 0.3, "probable_hotspot": 0.5, "high_confidence": 0.7}
        if self.value >= t["high_confidence"]:
            return SignalState.HIGH_CONFIDENCE
        if self.value >= t["probable_hotspot"]:
            return SignalState.PROBABLE_HOTSPOT
        if self.value >= t["watch"]:
            return SignalState.WATCH
        return SignalState.ARCHIVED


@dataclass(frozen=True)
class ObservationFingerprint:
    hash: str

    @classmethod
    def compute(
        cls,
        image_bytes: bytes | None,
        voice_bytes: bytes | None,
        location: Location,
        timestamp: datetime,
        device_id: str,
    ) -> Self:
        parts = [
            hashlib.sha256(image_bytes).hexdigest() if image_bytes else "",
            hashlib.sha256(voice_bytes).hexdigest() if voice_bytes else "",
            location.grid_bucket(),
            timestamp.strftime("%Y%m%d%H%M"),
            device_id,
        ]
        combined = "|".join(parts)
        return cls(hash=hashlib.sha256(combined.encode()).hexdigest())


@dataclass(frozen=True)
class ContributionEntry:
    observation_id: str
    fingerprint: str
    dimension_scores: dict[str, float]
    contribution_score: float
    weighted_contribution: float
    evaluation_timestamp: datetime
