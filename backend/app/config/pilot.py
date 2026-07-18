"""Pilot Configuration — Ward-level deployment settings.

Each pilot ward gets its own configuration profile.
Thresholds are tuned per-ward based on historical data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class PilotStatus(Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    REVIEW = "review"
    EXPANDED = "expanded"
    CLOSED = "closed"


@dataclass
class WardProfile:
    """Configuration for a single pilot ward."""
    ward_id: str
    ward_name: str
    municipality: str
    status: PilotStatus = PilotStatus.PLANNING

    # Geographic bounds
    center_lat: float = 0.0
    center_lng: float = 0.0
    radius_km: float = 2.0

    # Correlation thresholds (tunable per ward)
    threshold_watch: float = 0.3
    threshold_probable_hotspot: float = 0.5
    threshold_high_confidence: float = 0.7
    min_observations: int = 3
    min_source_types: int = 2

    # Spatial/temporal windows
    spatial_radius_meters: float = 500.0
    temporal_window_minutes: float = 30.0

    # Evidence weights
    weight_semantic: float = 0.30
    weight_spatial: float = 0.25
    weight_temporal: float = 0.20
    weight_independence: float = 0.15
    weight_environmental: float = 0.10

    # Pilot metadata
    start_date: str = ""
    target_observations: int = 100
    target_signals: int = 20


@dataclass
class PilotMetrics:
    """Operational metrics collected during pilot."""
    ward_id: str
    period_start: str = ""
    period_end: str = ""

    # Submission metrics
    total_observations: int = 0
    unique_submitters: int = 0
    avg_observations_per_day: float = 0.0

    # Signal metrics
    total_signals: int = 0
    signals_by_state: dict = field(default_factory=dict)
    avg_confidence: float = 0.0
    avg_observations_per_signal: float = 0.0

    # Quality metrics
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0

    # Operational metrics
    avg_verification_time_minutes: float = 0.0
    provider_availability_pct: float = 0.0
    avg_gemini_latency_ms: float = 0.0
    avg_correlation_latency_ms: float = 0.0

    # User metrics
    submission_success_rate: float = 0.0
    avg_submission_time_seconds: float = 0.0
    language_distribution: dict = field(default_factory=dict)


@dataclass
class PolicyVersion:
    """Tracks every policy change for model governance."""
    version: str
    ward_id: str
    created_at: str = ""
    created_by: str = "system"
    change_summary: str = ""

    # Snapshot of all thresholds at this version
    threshold_watch: float = 0.3
    threshold_probable_hotspot: float = 0.5
    threshold_high_confidence: float = 0.7
    min_observations: int = 3
    min_source_types: int = 2
    spatial_radius_meters: float = 500.0
    temporal_window_minutes: float = 30.0
    weight_semantic: float = 0.30
    weight_spatial: float = 0.25
    weight_temporal: float = 0.20
    weight_independence: float = 0.15
    weight_environmental: float = 0.10

    # Model governance
    gemini_model: str = "gemini-2.0-flash"
    prompt_version: str = "v3.2"
    schema_version: str = "v2.1"
    engine_version: str = "2.1.0"


# --- Default Pilot Ward ---

DEFAULT_WARD = WardProfile(
    ward_id="ward-001",
    ward_name="Pilot Ward",
    municipality="Pune",
    status=PilotStatus.PLANNING,
    center_lat=18.5204,
    center_lng=73.8567,
    radius_km=2.0,
    start_date="2026-08-01",
    target_observations=100,
    target_signals=20,
)

DEFAULT_POLICY_VERSION = PolicyVersion(
    version="2.1",
    ward_id="ward-001",
    created_at=datetime.now(timezone.utc).isoformat(),
    created_by="system",
    change_summary="Initial pilot configuration",
)
