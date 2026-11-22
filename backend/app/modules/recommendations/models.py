"""recommendations models: RecommendationRun, RecommendationItem, RecommendationFeedback."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    basis: Mapped[str] = mapped_column(String(30))  # consent_personal | generic (REC-03)
    inputs_snapshot: Mapped[str] = mapped_column(Text, default="{}")  # only allowed inputs (REC-02)
    recommender_version: Mapped[str] = mapped_column(String(20), default="rules-1.0")
    rule_pack_version: Mapped[str | None] = mapped_column(String(40), nullable=True)


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("recommendation_runs.id"), index=True)
    reward_id: Mapped[str] = mapped_column(ForeignKey("reward_items.id"))
    score: Mapped[float] = mapped_column(Numeric(6, 4), default=0)
    reasons_fa: Mapped[str] = mapped_column(Text, default="[]")  # real computed causes (REC-07)
    rank: Mapped[int] = mapped_column(default=0)


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("recommendation_items.id"), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    feedback: Mapped[str] = mapped_column(String(20))  # like|dismiss|not_now
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
