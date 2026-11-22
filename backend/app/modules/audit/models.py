"""audit models: AuditLog (append-only), RetentionPolicy, AnonymizationLog."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class AuditLog(Base):
    """Append-only — DB trigger denies UPDATE/DELETE (DM-03). No sensitive PII (masked upstream)."""
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str] = mapped_column(String(60), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    ip_masked: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class RetentionPolicy(Base):
    """DM-05: unlimited retention is not the default — per-entity policy, versioned by approval ref."""
    __tablename__ = "retention_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    entity: Mapped[str] = mapped_column(String(60), unique=True)
    keep_months: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(20))  # anonymize | delete
    approval_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)


class AnonymizationLog(Base):
    """DM-04: identity/analytics separation — proof trail for approved erasures."""
    __tablename__ = "anonymization_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    subject_student_ref: Mapped[str] = mapped_column(String(36), index=True)
    scope: Mapped[str] = mapped_column(String(120))
    done_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
