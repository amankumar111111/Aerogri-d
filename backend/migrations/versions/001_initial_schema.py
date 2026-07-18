"""Initial schema — all tables.

Revision ID: 001
Revises: None
Create Date: 2026-07-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("fingerprint", sa.String(64), index=True, nullable=True),
        sa.Column("content", sa.Text, default=""),
        sa.Column("photo_uri", sa.String(512), nullable=True),
        sa.Column("voice_uri", sa.String(512), nullable=True),
        sa.Column("location_lat", sa.Float, default=0.0),
        sa.Column("location_lng", sa.Float, default=0.0),
        sa.Column("category", sa.String(50), default="other"),
        sa.Column("language", sa.String(10), default="en"),
        sa.Column("device_id", sa.String(128), default=""),
        sa.Column("submitter_ref", sa.String(128), nullable=True),
        sa.Column("status", sa.String(20), default="submitted", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("interpreted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "interpretations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("observation_id", sa.String(36), index=True),
        sa.Column("model", sa.String(100), default="gemini-2.0-flash"),
        sa.Column("prompt_version", sa.String(20), default="v3.2"),
        sa.Column("schema_version", sa.String(20), default="v2.1"),
        sa.Column("categories", sa.Text, default="[]"),
        sa.Column("evidence_descriptions", sa.Text, default="[]"),
        sa.Column("severity_level", sa.String(20), nullable=True),
        sa.Column("citizen_category_alignment", sa.Boolean, default=False),
        sa.Column("confidence_score", sa.Float, default=0.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("state", sa.String(30), default="watch", index=True),
        sa.Column("location_lat", sa.Float, default=0.0),
        sa.Column("location_lng", sa.Float, default=0.0),
        sa.Column("category", sa.String(50), default="other"),
        sa.Column("confidence_value", sa.Float, default=0.0),
        sa.Column("contributing_observation_ids", sa.Text, default="[]"),
        sa.Column("contributions", sa.Text, default="[]"),
        sa.Column("environmental_context", sa.Text, default="{}"),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "signal_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("signal_id", sa.String(36), index=True),
        sa.Column("sequence_number", sa.Integer, default=0),
        sa.Column("event_type", sa.String(30), default=""),
        sa.Column("previous_state", sa.String(30), nullable=True),
        sa.Column("new_state", sa.String(30), nullable=True),
        sa.Column("composite_score", sa.Float, default=0.0),
        sa.Column("contribution_entries", sa.Text, default="[]"),
        sa.Column("policy_version", sa.String(20), default="2.0"),
        sa.Column("engine_version", sa.String(20), default="2.1.0"),
        sa.Column("trigger", sa.String(100), default=""),
        sa.Column("reason", sa.Text, default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("signal_id", sa.String(36), index=True),
        sa.Column("event_type", sa.String(50), default=""),
        sa.Column("previous_state", sa.String(30), nullable=True),
        sa.Column("new_state", sa.String(30), nullable=True),
        sa.Column("composite_score", sa.Float, nullable=True),
        sa.Column("observation_count", sa.Integer, nullable=True),
        sa.Column("policy_version", sa.String(20), default="2.0"),
        sa.Column("engine_version", sa.String(20), default="2.1.0"),
        sa.Column("interpreter_version", sa.Text, default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "provider_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider_type", sa.String(50), index=True),
        sa.Column("raw_data", sa.Text, default="{}"),
        sa.Column("normalized_data", sa.Text, default="{}"),
        sa.Column("fetch_timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("freshness", sa.String(50), default=""),
        sa.Column("status", sa.String(20), default="available"),
        sa.Column("confidence", sa.Float, default=0.0),
        sa.Column("latency_ms", sa.Float, default=0.0),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("signal_id", sa.String(36), index=True),
        sa.Column("channel", sa.String(20), default=""),
        sa.Column("recipients", sa.Text, default="[]"),
        sa.Column("subject", sa.String(500), default=""),
        sa.Column("body", sa.Text, default=""),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "media",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("observation_id", sa.String(36), index=True),
        sa.Column("media_type", sa.String(20), default=""),
        sa.Column("storage_uri", sa.String(512), default=""),
        sa.Column("content_hash", sa.String(64), default=""),
        sa.Column("size_bytes", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "policy_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.String(20), index=True),
        sa.Column("config", sa.Text, default="{}"),
        sa.Column("is_active", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("policy_versions")
    op.drop_table("media")
    op.drop_table("notifications")
    op.drop_table("provider_records")
    op.drop_table("audit_events")
    op.drop_table("signal_events")
    op.drop_table("signals")
    op.drop_table("interpretations")
    op.drop_table("observations")
