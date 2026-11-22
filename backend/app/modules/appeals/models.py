"""appeals models: Appeal, AppealOutcome."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class Appeal(Base):
    __tablename__ = "appeals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    case_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    subject_type: Mapped[str] = mapped_column(String(40))  # review_decision | ledger_correction | points_not_awarded
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ground_fa: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), default="submitted", index=True)  # doc/05-8
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewer_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # must != first reviewer (ACC-07)
    decision_fa: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(20), nullable=True)  # accepted|rejected
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppealOutcome(Base):
    __tablename__ = "appeal_outcomes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    appeal_id: Mapped[str] = mapped_column(ForeignKey("appeals.id"), index=True)
    ledger_tx_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # compensating document
    tiers_recalculated: Mapped[bool] = mapped_column(default=False)
    badges_recalculated: Mapped[bool] = mapped_column(default=False)
    note_fa: Mapped[str | None] = mapped_column(String(300), nullable=True)
