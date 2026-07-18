"""SQLAlchemy models and database engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import settings


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ObservationRow(Base):
    __tablename__ = "observations"

    id = Column(String(36), primary_key=True)
    fingerprint = Column(String(64), index=True)
    content = Column(Text, default="")
    photo_uri = Column(String(512), nullable=True)
    voice_uri = Column(String(512), nullable=True)
    location_lat = Column(Float, default=0.0)
    location_lng = Column(Float, default=0.0)
    category = Column(String(50), default="other")
    language = Column(String(10), default="en")
    device_id = Column(String(128), default="")
    submitter_ref = Column(String(128), nullable=True)
    status = Column(String(20), default="submitted", index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    interpreted_at = Column(DateTime(timezone=True), nullable=True)


class InterpretationRow(Base):
    __tablename__ = "interpretations"

    id = Column(String(36), primary_key=True)
    observation_id = Column(String(36), index=True)
    model = Column(String(100), default="gemini-2.0-flash")
    prompt_version = Column(String(20), default="v3.2")
    schema_version = Column(String(20), default="v2.1")
    categories = Column(Text, default="[]")  # JSON array
    evidence_descriptions = Column(Text, default="[]")  # JSON array
    severity_level = Column(String(20), nullable=True)
    citizen_category_alignment = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class SignalRow(Base):
    __tablename__ = "signals"

    id = Column(String(36), primary_key=True)
    state = Column(String(30), default="watch", index=True)
    location_lat = Column(Float, default=0.0)
    location_lng = Column(Float, default=0.0)
    category = Column(String(50), default="other")
    confidence_value = Column(Float, default=0.0)
    contributing_observation_ids = Column(Text, default="[]")  # JSON array
    contributions = Column(Text, default="[]")  # JSON array of ContributionEntry
    environmental_context = Column(Text, default="{}")  # JSON object
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    archived_at = Column(DateTime(timezone=True), nullable=True)


class SignalEventRow(Base):
    __tablename__ = "signal_events"

    id = Column(String(36), primary_key=True)
    signal_id = Column(String(36), index=True)
    sequence_number = Column(Integer, default=0)
    event_type = Column(String(30), default="")
    previous_state = Column(String(30), nullable=True)
    new_state = Column(String(30), nullable=True)
    composite_score = Column(Float, default=0.0)
    contribution_entries = Column(Text, default="[]")  # JSON array
    policy_version = Column(String(20), default="2.0")
    engine_version = Column(String(20), default="2.1.0")
    trigger = Column(String(100), default="")
    reason = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class ProviderRecordRow(Base):
    __tablename__ = "provider_records"

    id = Column(String(36), primary_key=True)
    provider_type = Column(String(50), index=True)
    raw_data = Column(Text, default="{}")  # JSON
    normalized_data = Column(Text, default="{}")  # JSON
    fetch_timestamp = Column(DateTime(timezone=True), default=_utcnow)
    freshness = Column(String(50), default="")
    status = Column(String(20), default="available")
    confidence = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True)
    signal_id = Column(String(36), index=True)
    event_type = Column(String(50), default="")
    previous_state = Column(String(30), nullable=True)
    new_state = Column(String(30), nullable=True)
    composite_score = Column(Float, nullable=True)
    observation_count = Column(Integer, nullable=True)
    policy_version = Column(String(20), default="2.0")
    engine_version = Column(String(20), default="2.1.0")
    interpreter_version = Column(Text, default="{}")  # JSON
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class NotificationRow(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True)
    signal_id = Column(String(36), index=True)
    channel = Column(String(20), default="")
    recipients = Column(Text, default="[]")  # JSON array
    subject = Column(String(500), default="")
    body = Column(Text, default="")
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class MediaRow(Base):
    __tablename__ = "media"

    id = Column(String(36), primary_key=True)
    observation_id = Column(String(36), index=True)
    media_type = Column(String(20), default="")
    storage_uri = Column(String(512), default="")
    content_hash = Column(String(64), default="")
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class PolicyVersionRow(Base):
    __tablename__ = "policy_versions"

    id = Column(String(36), primary_key=True)
    version = Column(String(20), index=True)
    config = Column(Text, default="{}")  # JSON
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# --- Engine & Session ---

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
