"""event_ingestion models: IntegrationSource, EducationalEvent (immutable), EventCorrection, EvidenceReference, EventInbox."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class IntegrationSource(Base):
    __tablename__ = "integration_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    code: Mapped[str] = mapped_column(String(60))
    name_fa: Mapped[str] = mapped_column(String(200))
    auth_key_hash: Mapped[str] = mapped_column(String(200))  # X-Integration-Key (hashed at rest)
    hmac_secret_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)  # secret stored outside repo
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, default=600)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_simulator: Mapped[bool] = mapped_column(Boolean, default=False)  # EVT-11 label
    schema_version: Mapped[str] = mapped_column(String(10), default="1.0")
    __table_args__ = (UniqueConstraint("university_id", "code", name="uq_intsrc_uni_code"),)


class EducationalEvent(Base):
    """Raw minimal event — IMMUTABLE (trigger denies UPDATE/DELETE; corrections are new rows)."""
    __tablename__ = "educational_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    event_id: Mapped[str] = mapped_column(String(120))
    schema_version: Mapped[str] = mapped_column(String(10))
    source_id: Mapped[str] = mapped_column(ForeignKey("integration_sources.id"), index=True)
    student_reference: Mapped[str] = mapped_column(String(60), index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    activity_reference: Mapped[str] = mapped_column(String(200))
    evidence_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="verified")  # pending_human|verified|rejected
    correlation_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    reference_to_corrected_event: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    __table_args__ = (
        UniqueConstraint("university_id", "source_id", "event_id", name="uq_edevent_uni_src_event"),
        Index("ix_edevent_type_occ", "event_type", "occurred_at"),
    )


class EventCorrection(Base):
    __tablename__ = "event_corrections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    target_event_id: Mapped[str] = mapped_column(ForeignKey("educational_events.id"), index=True)
    correction_event_id: Mapped[str] = mapped_column(ForeignKey("educational_events.id"), index=True)
    reason_fa: Mapped[str] = mapped_column(String(500))


class EvidenceReference(Base):
    __tablename__ = "evidence_references"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    storage_key: Mapped[str] = mapped_column(String(300))  # private S3/MinIO key — never public URL
    sha256: Mapped[str] = mapped_column(String(64))
    uploaded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EventInbox(Base):
    """Processing envelope — at-least-once delivery, exactly-once effect via unique keys."""
    __tablename__ = "event_inbox"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    message_id: Mapped[str] = mapped_column(String(120), unique=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("educational_events.id"), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(20), default="received", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    quarantined_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
