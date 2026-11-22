"""integrity_reviews models: IntegritySignal, ReviewCase, CaseExplanation, CaseDecision."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base, utcnow
from ..identity_access.models import uid


class IntegritySignal(Base):
    __tablename__ = "integrity_signals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # deterministic | risk_pattern (INT-01)
    rule_code: Mapped[str] = mapped_column(String(60))  # explicit rule-based check title (INT-08)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    subject_student_ref: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    refs_json: Mapped[str] = mapped_column(Text, default="{}")  # minimal references, no sensitive payload
    is_advisory: Mapped[bool] = mapped_column(Boolean, default=True)  # never an auto verdict (PRN-07)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewCase(Base):
    __tablename__ = "review_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    signal_id: Mapped[str] = mapped_column(ForeignKey("integrity_signals.id"), index=True)
    student_ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(30), default="flagged", index=True)  # doc/05-7
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # INT-04
    sla_breached: Mapped[bool] = mapped_column(default=False)
    assigned_to: Mapped[str | None] = mapped_column(String(36), nullable=True)
    summary_fa: Mapped[str | None] = mapped_column(String(500), nullable=True)  # understandable summary for student
    decided_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CaseExplanation(Base):
    __tablename__ = "case_explanations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("review_cases.id"), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    body: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CaseDecision(Base):
    __tablename__ = "case_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("review_cases.id"), index=True)
    decision: Mapped[str] = mapped_column(String(30))  # cleared|violation_minor|violation_major|refer_official
    justification_fa: Mapped[str] = mapped_column(Text)  # INT-06: documented & proportionate
    affected_tx_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # only related tx (INT-05)
    decided_by: Mapped[str] = mapped_column(String(36))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
