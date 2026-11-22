"""memberships_consents models: TermsVersion, Membership, ConsentRecord, AdvisorAssignment, ApprovalScope, NotificationPreference moved to notifications."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class TermsVersion(Base):
    __tablename__ = "terms_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    version_no: Mapped[int] = mapped_column()
    title_fa: Mapped[str] = mapped_column(String(200))
    content_fa: Mapped[str] = mapped_column(Text)
    data_policy_fa: Mapped[str] = mapped_column(Text, default="")
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str] = mapped_column(ForeignKey("student_references.id"), unique=True, index=True)
    state: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    membership_no: Mapped[str] = mapped_column(String(30), unique=True)
    terms_version_id: Mapped[str | None] = mapped_column(ForeignKey("terms_versions.id"), nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str] = mapped_column(ForeignKey("student_references.id"), index=True)
    consent_type: Mapped[str] = mapped_column(String(40))  # personalization | public_badge | notifications
    value: Mapped[bool] = mapped_column(Boolean)
    terms_version_id: Mapped[str | None] = mapped_column(ForeignKey("terms_versions.id"), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="self_service")


class AdvisorAssignment(Base):
    __tablename__ = "advisor_assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    advisor_user_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str] = mapped_column(ForeignKey("student_references.id"), index=True)
    scope_note: Mapped[str] = mapped_column(String(300), default="")
    __table_args__ = (UniqueConstraint("advisor_user_id", "student_ref_id", name="uq_advisor_student"),)


class ApprovalScope(Base):
    """ACC-04: professor may verify only within his allowed scope."""
    __tablename__ = "approval_scopes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    professor_user_id: Mapped[str] = mapped_column(String(36), index=True)
    activity_scope: Mapped[str] = mapped_column(String(120))  # course_code or activity prefix
    academic_period_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
