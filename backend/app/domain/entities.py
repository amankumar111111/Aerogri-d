"""Domain entities — identity-bearing, mutable state."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.domain.value_objects import (
    ConfidenceScore,
    ContributionEntry,
    Location,
    ObservationFingerprint,
    Severity,
    SignalState,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Observation:
    id: str = field(default_factory=_uuid)
    fingerprint: ObservationFingerprint | None = None
    content: str = ""
    photo_uri: str | None = None
    voice_uri: str | None = None
    location: Location = field(default_factory=lambda: Location(0.0, 0.0))
    category: str = "other"
    language: str = "en"
    device_id: str = ""
    submitter_ref: str | None = None
    status: str = "submitted"  # submitted | interpreted | correlated | archived
    created_at: datetime = field(default_factory=_now)
    interpreted_at: datetime | None = None


@dataclass
class Interpretation:
    id: str = field(default_factory=_uuid)
    observation_id: str = ""
    model: str = "gemini-2.0-flash"
    prompt_version: str = "v3.2"
    schema_version: str = "v2.1"
    categories: list[str] = field(default_factory=list)
    evidence_descriptions: list[str] = field(default_factory=list)
    severity: Severity | None = None
    citizen_category_alignment: bool = False
    confidence_score: float = 0.0
    created_at: datetime = field(default_factory=_now)


@dataclass
class Signal:
    id: str = field(default_factory=_uuid)
    state: SignalState = SignalState.WATCH
    location: Location = field(default_factory=lambda: Location(0.0, 0.0))
    category: str = "other"
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(0.0))
    contributing_observation_ids: list[str] = field(default_factory=list)
    contributions: list[ContributionEntry] = field(default_factory=list)
    environmental_context: dict = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    archived_at: datetime | None = None


@dataclass
class SignalEvent:
    id: str = field(default_factory=_uuid)
    signal_id: str = ""
    sequence_number: int = 0
    event_type: str = ""  # created | escalated | deescalated | archived
    previous_state: SignalState | None = None
    new_state: SignalState | None = None
    composite_score: float = 0.0
    contribution_entries: list[ContributionEntry] = field(default_factory=list)
    policy_version: str = "2.0"
    engine_version: str = "2.1.0"
    trigger: str = ""
    reason: str = ""
    created_at: datetime = field(default_factory=_now)


@dataclass
class ProviderRecord:
    id: str = field(default_factory=_uuid)
    provider_type: str = ""  # weather | cpcb | firms
    raw_data: dict = field(default_factory=dict)
    normalized_data: dict = field(default_factory=dict)
    fetch_timestamp: datetime = field(default_factory=_now)
    freshness: str = ""  # ISO-8601 of data vintage
    status: str = "available"  # available | unavailable | stale
    confidence: float = 0.0
    latency_ms: float = 0.0


@dataclass
class AuditEvent:
    id: str = field(default_factory=_uuid)
    signal_id: str = ""
    event_type: str = ""
    previous_state: str | None = None
    new_state: str | None = None
    composite_score: float | None = None
    observation_count: int | None = None
    policy_version: str = "2.0"
    engine_version: str = "2.1.0"
    interpreter_version: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)


@dataclass
class Notification:
    id: str = field(default_factory=_uuid)
    signal_id: str = ""
    channel: str = ""  # email | inapp | webhook
    recipients: list[str] = field(default_factory=list)
    subject: str = ""
    body: str = ""
    sent_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class Media:
    id: str = field(default_factory=_uuid)
    observation_id: str = ""
    media_type: str = ""  # image | audio
    storage_uri: str = ""
    content_hash: str = ""
    size_bytes: int = 0
    created_at: datetime = field(default_factory=_now)


@dataclass
class PolicyVersion:
    id: str = field(default_factory=_uuid)
    version: str = ""
    config: dict = field(default_factory=dict)
    is_active: bool = False
    created_at: datetime = field(default_factory=_now)
