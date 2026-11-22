"""missions_groups models: Mission, MissionParticipation, LearningGroup, GroupContribution."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    title_fa: Mapped[str] = mapped_column(String(200))
    description_fa: Mapped[str] = mapped_column(Text, default="")
    goal_type: Mapped[str] = mapped_column(String(40))
    activities_json: Mapped[str] = mapped_column(Text, default="[]")  # [{event_type, min_count}]
    success_criteria_json: Mapped[str] = mapped_column(Text, default="{}")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reward_ref: Mapped[str | None] = mapped_column(String(36), nullable=True)
    max_points: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    alternative_path_fa: Mapped[str | None] = mapped_column(String(500), nullable=True)  # ACH-05
    is_group: Mapped[bool] = mapped_column(Boolean, default=False)
    state: Mapped[str] = mapped_column(String(20), default="active")
    # ---- v1.3 تجربهٔ باشگاه: مأموریت‌های کوتاه، تیمی و دارای خروجی ملموس ----
    mission_kind: Mapped[str] = mapped_column(String(30), default="standard")
    # kickoff | micro_challenge | one_day | trial_workshop | skill_evening | real_problem | build | guide | standard
    output_fa: Mapped[str] = mapped_column(String(300), default="")  # خروجی ملموس مأموریت
    duration_label_fa: Mapped[str] = mapped_column(String(40), default="")  # «۲۰ دقیقه» / «یک روز» / «یک هفته»
    team_size_hint: Mapped[str] = mapped_column(String(40), default="")  # «۲ تا ۳ نفر» / «فردی»
    interest_tags: Mapped[str] = mapped_column(String(200), default="")  # csv: build,tech,event,help,skill,guide


class MissionParticipation(Base):
    __tablename__ = "mission_participations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id"), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    state: Mapped[str] = mapped_column(String(20), default="active")  # active|completed|quit|expired
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("mission_id", "student_ref_id", name="uq_missionpart"),)


class LearningGroup(Base):
    __tablename__ = "learning_groups"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    mission_id: Mapped[str | None] = mapped_column(ForeignKey("missions.id"), nullable=True)
    title_fa: Mapped[str] = mapped_column(String(200))
    capacity: Mapped[int | None] = mapped_column(nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="active")
    # ---- v1.3 گروه‌های کوچک علاقه‌ای با هدف/زمان/خروجی روشن ----
    interest_tag: Mapped[str] = mapped_column(String(60), default="")
    goal_fa: Mapped[str] = mapped_column(String(300), default="")
    expected_output_fa: Mapped[str] = mapped_column(String(300), default="")
    duration_label_fa: Mapped[str] = mapped_column(String(60), default="")


class GroupMember(Base):
    __tablename__ = "group_members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("learning_groups.id"), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # ACH-06
    __table_args__ = (UniqueConstraint("group_id", "student_ref_id", name="uq_groupmember"),)


class GroupContribution(Base):
    __tablename__ = "group_contributions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("learning_groups.id"), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    activity_key: Mapped[str] = mapped_column(String(120))  # dedupe repeated points (ACH-06)
    share_note_fa: Mapped[str] = mapped_column(String(500), default="")
    evidence_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    points_tx_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    __table_args__ = (UniqueConstraint("group_id", "student_ref_id", "activity_key", name="uq_groupcontrib"),)
