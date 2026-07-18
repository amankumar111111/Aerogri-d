"""Domain policies — deterministic rules with no external dependencies."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.domain.value_objects import Location, SourceType


# --- Duplicate Detection (S3.5, S3.8) ---

@dataclass(frozen=True)
class DuplicateConfig:
    content_threshold: float = 0.85
    spatial_threshold_meters: float = 200.0
    temporal_threshold_minutes: float = 15.0
    search_radius_meters: float = 500.0
    search_window_minutes: float = 30.0


def is_duplicate(
    *,
    content_similarity: float,
    spatial_distance_meters: float,
    temporal_gap_minutes: float,
    config: DuplicateConfig | None = None,
) -> bool:
    c = config or DuplicateConfig()
    return (
        content_similarity > c.content_threshold
        and spatial_distance_meters < c.spatial_threshold_meters
        and temporal_gap_minutes < c.temporal_threshold_minutes
    )


# --- Similarity Scoring (S3.8.2) ---

@dataclass(frozen=True)
class SimilarityWeights:
    content: float = 0.5
    spatial: float = 0.3
    temporal: float = 0.2


def compute_similarity(
    *,
    content_similarity: float,
    spatial_distance_meters: float,
    max_distance_meters: float,
    temporal_gap_minutes: float,
    max_window_minutes: float,
    weights: SimilarityWeights | None = None,
) -> float:
    w = weights or SimilarityWeights()
    spatial_proximity = max(0.0, 1.0 - (spatial_distance_meters / max_distance_meters))
    temporal_proximity = max(0.0, 1.0 - (temporal_gap_minutes / max_window_minutes))
    return w.content * content_similarity + w.spatial * spatial_proximity + w.temporal * temporal_proximity


# --- Correlation Engine Dimensions (S4) ---

CATEGORY_RELATIONSHIPS: dict[tuple[str, str], float] = {
    ("smoke", "smoke"): 1.0,
    ("smoke", "chemical"): 0.6,
    ("smoke", "fire"): 0.8,
    ("dust", "smoke"): 0.5,
    ("dust", "construction_dust"): 0.7,
    ("water", "chemical"): 0.4,
    ("water", "sewage"): 0.5,
    ("noise", "construction_dust"): 0.3,
    ("fire", "smoke"): 0.8,
    ("fire", "chemical"): 0.4,
    ("gas_leak", "chemical"): 0.6,
    ("gas_leak", "smoke"): 0.3,
}


def semantic_score(category_a: str, category_b: str, evidence_overlap: float) -> float:
    key = (category_a, category_b)
    reverse_key = (category_b, category_a)
    if category_a == category_b:
        category_match = 1.0
    elif key in CATEGORY_RELATIONSHIPS:
        category_match = CATEGORY_RELATIONSHIPS[key]
    elif reverse_key in CATEGORY_RELATIONSHIPS:
        category_match = CATEGORY_RELATIONSHIPS[reverse_key]
    elif category_a == "other" or category_b == "other":
        category_match = 0.1
    else:
        category_match = 0.0
    return 0.6 * category_match + 0.4 * evidence_overlap


def spatial_score(distance_meters: float, radius_meters: float = 500.0) -> float:
    return max(0.0, 1.0 - (distance_meters / radius_meters))


def temporal_score(
    delta_minutes: float,
    window_minutes: float = 30.0,
) -> float:
    return max(0.0, 1.0 - (delta_minutes / window_minutes))


def independence_score(
    *,
    is_duplicate: bool,
    same_device: bool,
    same_session_minutes: float | None = None,
) -> float:
    if is_duplicate:
        return 0.0
    if same_device and same_session_minutes is not None and same_session_minutes < 5.0:
        return 0.2
    return 1.0


def environmental_score(
    *,
    wind_consistent: bool = False,
    low_humidity_high_temp: bool = False,
    recent_precipitation: bool = False,
    firms_fire_detected: bool = False,
    cpcb_elevated: bool = False,
) -> float:
    raw = 0.0
    if wind_consistent:
        raw += 0.15
    if low_humidity_high_temp:
        raw += 0.1
    if recent_precipitation:
        raw -= 0.2
    if firms_fire_detected:
        raw += 0.25
    if cpcb_elevated:
        raw += 0.2
    return max(0.0, raw)


# --- Composite Scoring (S4.6) ---

@dataclass(frozen=True)
class CompositeWeights:
    semantic: float = 0.30
    spatial: float = 0.25
    temporal: float = 0.20
    independence: float = 0.15
    environmental: float = 0.10


@dataclass(frozen=True)
class CorrelationConfig:
    """All thresholds and minimums for signal classification (S4.6, S5.1)."""
    threshold_watch: float = 0.3
    threshold_probable_hotspot: float = 0.5
    threshold_high_confidence: float = 0.7
    min_observations_watch: int = 1
    min_observations_probable_hotspot: int = 3
    min_observations_high_confidence: int = 5
    min_source_types_probable_hotspot: int = 2
    min_source_types_high_confidence: int = 2
    composite_weights: CompositeWeights = CompositeWeights()
    # Spatial gate: observations beyond this distance cannot correlate
    spatial_gate_radius_meters: float = 1000.0


DEFAULT_CONFIG = CorrelationConfig()


def composite_score(
    *,
    semantic: float,
    spatial: float,
    temporal: float,
    independence: float,
    environmental: float,
    weights: CompositeWeights | None = None,
) -> float:
    w = weights or CompositeWeights()
    raw = (
        w.semantic * semantic
        + w.spatial * spatial
        + w.temporal * temporal
        + w.independence * independence
        + w.environmental * environmental
    )
    return max(0.0, min(1.0, raw))
