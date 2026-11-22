"""student_goals models: AcademicPeriod, StudentGoal, DataCorrectionRequest."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class AcademicPeriod(Base):
    __tablename__ = "academic_periods"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    title_fa: Mapped[str] = mapped_column(String(100))
    starts_at: Mapped[date] = mapped_column(Date)
    ends_at: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(default=False)


class StudentGoal(Base):
    __tablename__ = "student_goals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str] = mapped_column(ForeignKey("student_references.id"), index=True)
    goal_type: Mapped[str] = mapped_column(String(40))  # weakness|exam_prep|skill|collaboration|other
    title_fa: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|archived
    academic_period_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    declared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DataCorrectionRequest(Base):
    __tablename__ = "data_correction_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    requester_user_id: Mapped[str] = mapped_column(String(36), index=True)
    subject_entity: Mapped[str] = mapped_column(String(60))  # ledger|profile|event|badge|...
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason_fa: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), default="submitted", index=True)  # submitted|in_review|applied|rejected|closed
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
