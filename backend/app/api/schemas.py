"""API response DTOs — never expose database models.

Frontend contract: every field, enum, and format is explicit.
No untyped strings. No mystery objects. No leaked implementation details.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Enums (single source of truth for frontend) ---

class SignalStateEnum(str, Enum):
    WATCH = "watch"
    PROBABLE_HOTSPOT = "probable_hotspot"
    HIGH_CONFIDENCE = "high_confidence"
    ARCHIVED = "archived"


class ObservationCategoryEnum(str, Enum):
    SMOKE = "smoke"
    DUST = "dust"
    CHEMICAL = "chemical"
    WATER = "water"
    NOISE = "noise"
    FIRE = "fire"
    GAS_LEAK = "gas_leak"
    CONSTRUCTION_DUST = "construction_dust"
    SEWAGE = "sewage"
    OTHER = "other"


class ObservationStatusEnum(str, Enum):
    SUBMITTED = "submitted"
    INTERPRETED = "interpreted"
    CORRELATED = "correlated"
    ARCHIVED = "archived"


class LanguageEnum(str, Enum):
    EN = "en"
    HI = "hi"
    MR = "mr"


class SeverityLevelEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# --- Error ---

class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str
    received: Any = None


class ErrorBody(BaseModel):
    code: str = Field(..., description="Machine-readable error code, e.g. NOT_FOUND, INVALID_OBSERVATION")
    message: str = Field(..., description="Human-readable error description")
    details: list[ErrorDetail] = Field(default=[], description="Field-level validation errors (for 422)")
    correlation_id: str = Field(..., description="Unique request ID for debugging")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of the error")


class ErrorResponse(BaseModel):
    """Standard error envelope. All error responses (400, 404, 429, 500) use this format."""
    error: ErrorBody


# --- Observation ---

class ObservationResponse(BaseModel):
    """A citizen observation. ID is a UUID v4 string."""
    id: str = Field(..., description="UUID v4 observation identifier")
    fingerprint: str | None = Field(None, description="SHA-256 content fingerprint for duplicate detection")
    content: str = Field(..., description="Citizen text description of the observation")
    category: ObservationCategoryEnum = Field(..., description="Environmental event category")
    language: LanguageEnum = Field(..., description="Language of the submission")
    latitude: float = Field(..., ge=-90, le=90, description="GPS latitude")
    longitude: float = Field(..., ge=-180, le=180, description="GPS longitude")
    status: ObservationStatusEnum = Field(..., description="Processing status")
    created_at: str = Field(..., description="ISO-8601 UTC timestamp of submission")
    interpreted_at: str | None = Field(None, description="ISO-8601 UTC timestamp of Gemini interpretation, null if pending")


class ObservationSubmitRequest(BaseModel):
    """Request body for submitting a new observation."""
    content: str = Field(..., min_length=1, max_length=5000, description="Text description of what you observed")
    latitude: float = Field(..., ge=-90, le=90, description="GPS latitude of the observation")
    longitude: float = Field(..., ge=-180, le=180, description="GPS longitude of the observation")
    category: ObservationCategoryEnum = Field(..., description="Type of environmental event")
    language: LanguageEnum = Field(LanguageEnum.EN, description="Language of the submission")
    device_id: str = Field(..., min_length=1, max_length=128, description="Unique device identifier for deduplication")


class ObservationSubmitResponse(BaseModel):
    """Response after successfully submitting an observation."""
    observation_id: str = Field(..., description="UUID v4 — use this to track status")
    fingerprint: str = Field(..., description="SHA-256 content fingerprint")
    status: ObservationStatusEnum = Field(..., description="Always 'submitted' on success")
    tracking_ref: str = Field(..., description="Short reference (first 8 chars of observation_id) for citizen display")


# --- Interpretation ---

class InterpretationResponse(BaseModel):
    """Gemini's structured interpretation of a citizen observation."""
    id: str = Field(..., description="UUID v4 interpretation identifier")
    observation_id: str = Field(..., description="UUID v4 of the parent observation")
    model: str = Field(..., description="AI model used, e.g. 'gemini-2.0-flash'")
    prompt_version: str = Field(..., description="Prompt version used for this interpretation")
    schema_version: str = Field(..., description="Output schema version for this interpretation")
    categories: list[str] = Field(..., description="AI-detected environmental categories")
    evidence_descriptions: list[str] = Field(..., description="What the AI sees/hears in the media")
    severity_level: SeverityLevelEnum | None = Field(None, description="AI-assessed severity")
    citizen_category_alignment: bool = Field(..., description="True if AI agrees with citizen's selected category")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence in its interpretation (0.0–1.0)")
    created_at: str = Field(..., description="ISO-8601 UTC timestamp")


# --- Signal ---

class ContributionResponse(BaseModel):
    """How one observation contributed to a signal's score."""
    observation_id: str = Field(..., description="UUID v4 of the contributing observation")
    fingerprint: str = Field(..., description="Content fingerprint of the observation")
    dimension_scores: dict[str, float] = Field(
        ...,
        description="Per-dimension scores: semantic, spatial, temporal, independence, environmental (each 0.0–1.0)",
        examples=[{"semantic": 0.82, "spatial": 0.91, "temporal": 0.77, "independence": 1.0, "environmental": 0.42}],
    )
    contribution_score: float = Field(..., ge=0.0, le=1.0, description="Raw contribution before provenance weighting")
    weighted_contribution: float = Field(..., ge=0.0, le=1.0, description="Contribution after provenance weighting")
    evaluation_timestamp: str = Field(..., description="ISO-8601 UTC timestamp of evaluation")


class SignalResponse(BaseModel):
    """A correlated environmental signal."""
    id: str = Field(..., description="UUID v4 signal identifier")
    state: SignalStateEnum = Field(..., description="Current lifecycle state")
    latitude: float = Field(..., ge=-90, le=90, description="Centroid latitude of contributing observations")
    longitude: float = Field(..., ge=-180, le=180, description="Centroid longitude of contributing observations")
    category: ObservationCategoryEnum = Field(..., description="Dominant environmental category")
    confidence_value: float = Field(..., ge=0.0, le=1.0, description="Composite confidence score (0.0–1.0)")
    contributing_observation_ids: list[str] = Field(..., description="UUIDs of observations that contributed to this signal")
    contributions: list[ContributionResponse] = Field(..., description="Per-observation contribution breakdown")
    environmental_context: dict[str, Any] = Field(
        ...,
        description="Environmental data snapshot: temperature, humidity, wind, precipitation, fire_detected, etc.",
        examples=[{"temperature": 38, "humidity": 35, "fire_detected": True, "recent_precipitation": False}],
    )
    version: int = Field(..., description="Version number, incremented on every state change")
    created_at: str = Field(..., description="ISO-8601 UTC timestamp of signal creation")
    updated_at: str = Field(..., description="ISO-8601 UTC timestamp of last update")
    archived_at: str | None = Field(None, description="ISO-8601 UTC timestamp of archival, null if active")


class SignalActionResponse(BaseModel):
    """Response after a signal state transition (verify, archive)."""
    signal_id: str = Field(..., description="UUID v4 of the affected signal")
    state: SignalStateEnum = Field(..., description="New state after the action")
    message: str = Field(..., description="Human-readable confirmation")


# --- Analytics ---

class AnalyticsSummary(BaseModel):
    """Aggregate statistics for the dashboard overview."""
    total_observations: int = Field(..., description="Total observations ever submitted")
    total_signals: int = Field(..., description="Total signals ever created")
    active_signals: int = Field(..., description="Signals not yet archived")
    high_confidence_signals: int = Field(..., description="Signals in High Confidence state")
    avg_confidence: float = Field(..., ge=0.0, le=1.0, description="Average confidence across all signals")
    signals_by_state: dict[str, int] = Field(
        ...,
        description="Count of signals per state: {watch: N, probable_hotspot: N, high_confidence: N, archived: N}",
    )


class HeatmapPoint(BaseModel):
    """A cluster of signals at a location for map overlay."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    intensity: float = Field(..., ge=0.0, le=1.0, description="Normalized intensity (signal_count / 10, capped at 1.0)")
    signal_count: int = Field(..., description="Number of signals at this location")
    dominant_state: SignalStateEnum = Field(..., description="Most common state among signals at this location")


class TimelineEntry(BaseModel):
    """A recent signal state change for the timeline view."""
    signal_id: str = Field(..., description="UUID v4 of the signal")
    state: SignalStateEnum = Field(..., description="Current state")
    composite_score: float = Field(..., ge=0.0, le=1.0, description="Composite confidence score")
    observation_count: int = Field(..., description="Number of contributing observations")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of the state change")


# --- Health ---

class HealthResponse(BaseModel):
    """Service health status."""
    status: str = Field(..., description="Always 'ok' if the service is running")
    version: str = Field(..., description="Service version, e.g. '0.1.0'")


class ReadinessResponse(BaseModel):
    """Service readiness with dependency health."""
    status: str = Field(..., description="'ready' if all dependencies healthy, 'degraded' otherwise")
    database: str = Field(..., description="'ok' or 'unavailable'")
    redis: str = Field(..., description="'ok' or 'unavailable'")


class MetricsResponse(BaseModel):
    """Operational metrics for monitoring."""
    observations_total: int = Field(..., description="Total observations in database")
    signals_total: int = Field(..., description="Total signals in database")
    signals_by_state: dict[str, int] = Field(..., description="Count per state")
    uptime_seconds: float = Field(..., description="Seconds since service start")
