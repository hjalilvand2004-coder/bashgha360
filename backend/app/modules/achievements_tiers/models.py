"""achievements_tiers models: TierDefinition, TierAward, BadgeDefinition, BadgeAward, BadgeShare."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid

NUM = Numeric(14, 2)


class TierDefinition(Base):
    __tablename__ = "tier_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    path: Mapped[str] = mapped_column(String(20), index=True)  # learning|skill|collaboration
    level_no: Mapped[int] = mapped_column(Integer)
    title_fa: Mapped[str] = mapped_column(String(60))
    min_progress: Mapped[float] = mapped_column(NUM)
    icon_svg_id: Mapped[str] = mapped_column(String(60), default="tier")
    __table_args__ = (UniqueConstraint("university_id", "path", "level_no", name="uq_tier_uni_path_lvl"),)


class TierAward(Base):
    __tablename__ = "tier_awards"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    tier_id: Mapped[str] = mapped_column(ForeignKey("tier_definitions.id"))
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("student_ref_id", "tier_id", name="uq_tieraward"),)


class BadgeDefinition(Base):
    __tablename__ = "badge_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    title_fa: Mapped[str] = mapped_column(String(120))
    svg_id: Mapped[str] = mapped_column(String(60), default="badge-learning")
    path: Mapped[str] = mapped_column(String(20))  # learning|skill|collaboration
    criteria_json: Mapped[str] = mapped_column(Text, default="{}")  # {event_type: min_count} or {tier_level: n}
    criteria_version: Mapped[int] = mapped_column(Integer, default=1)
    issuer_fa: Mapped[str] = mapped_column(String(120), default="باشگاه۳۶۰")
    valid_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_auto: Mapped[bool] = mapped_column(Boolean, default=True)
    state: Mapped[str] = mapped_column(String(20), default="active")
    # ---- v1.3 نشان‌های داستان‌محور: نشان می‌گوید چه کاری انجام شده و چرا ارزشمند است ----
    story_fa: Mapped[str] = mapped_column(String(400), default="")


class BadgeAward(Base):
    __tablename__ = "badge_awards"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    badge_id: Mapped[str] = mapped_column(ForeignKey("badge_definitions.id"))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="valid", index=True)  # valid|corrected|revoked
    reason_fa: Mapped[str | None] = mapped_column(String(300), nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    criteria_version: Mapped[int] = mapped_column(Integer, default=1)


class BadgeShare(Base):
    """ACH-03: public display only by student's own choice; revocable + expirable link."""
    __tablename__ = "badge_shares"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    badge_award_id: Mapped[str] = mapped_column(ForeignKey("badge_awards.id"), index=True)
    share_token: Mapped[str] = mapped_column(String(64), unique=True)
    created_by_user: Mapped[str | None] = mapped_column(String(36), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
