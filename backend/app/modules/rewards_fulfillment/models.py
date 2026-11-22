"""rewards_fulfillment models: RewardProvider, Reward, RewardCapacity, RewardRequest, RewardReservation, FulfillmentAttempt, DeliveryReceipt, ReconciliationCase."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid

NUM = Numeric(14, 2)

ACTIVE_REQUEST_STATES = ("requested", "reserved", "approved", "fulfilling")


class RewardProvider(Base):
    __tablename__ = "reward_providers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    name_fa: Mapped[str] = mapped_column(String(200))
    contact_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    callback_secret_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Reward(Base):
    __tablename__ = "reward_items"
    __table_args__ = (
        CheckConstraint("NOT is_essential OR cost_points = 0", name="essential_free"),  # PRN-06
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("reward_providers.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(40))  # RWD-01: badge_auto|resource_access|workshop|counseling|project|internship_invite|professional_perk|auto_perk
    title_fa: Mapped[str] = mapped_column(String(200))
    description_fa: Mapped[str] = mapped_column(Text, default="")
    cost_points: Mapped[float] = mapped_column(NUM, default=0)
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_grant: Mapped[bool] = mapped_column(Boolean, default=False)  # RWD-03: distinct from paid rewards
    capacity_total: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    allocation: Mapped[str] = mapped_column(String(20), default="first_come")  # first_come|quota|queue|lottery
    delivery: Mapped[str] = mapped_column(String(20), default="in_app")  # in_app|code|external
    conditions_json: Mapped[str] = mapped_column(Text, default="{}")  # {programs:[], skills:[], period_id, accessibility}
    validity_fa: Mapped[str | None] = mapped_column(String(200), nullable=True)
    refund_policy_fa: Mapped[str] = mapped_column(String(300), default="")
    data_consent_note: Mapped[str | None] = mapped_column(String(300), nullable=True)  # minimal data sharing note
    state: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|paused
    goal_tags: Mapped[str] = mapped_column(String(200), default="")  # csv tags matching StudentGoal.goal_type
    # ---- v1.3 پاداش‌های تجربه‌ساز: experience=کارگاه/بازدید/منتورینگ، choice=حق انتخاب دانشجو ----
    kind: Mapped[str] = mapped_column(String(20), default="physical")  # physical|experience|resource|choice


class RewardCapacity(Base):
    __tablename__ = "reward_capacities"
    __table_args__ = (
        UniqueConstraint("reward_id", name="uq_reward_capacity_reward"),  # one row → race-safe reservation
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    reward_id: Mapped[str] = mapped_column(ForeignKey("reward_items.id"), index=True)
    total: Mapped[int] = mapped_column(Integer)
    reserved_count: Mapped[int] = mapped_column(Integer, default=0)
    final_count: Mapped[int] = mapped_column(Integer, default=0)


class RewardRequest(Base):
    __tablename__ = "reward_requests"
    __table_args__ = (
        # exactly one ACTIVE request per (student, reward) — partial unique index (LED-07)
        Index("uq_rr_active", "student_ref_id", "reward_id", unique=True,
              postgresql_where=text("active_group = '1'")),
        CheckConstraint("active_group IN ('0','1')", name="active_group_domain"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    reward_id: Mapped[str] = mapped_column(ForeignKey("reward_items.id"), index=True)
    state: Mapped[str] = mapped_column(String(20), default="requested", index=True)
    active_group: Mapped[str] = mapped_column(String(1), default="1")  # "1" while active, "0" when terminal (unique guard)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ttl_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason_fa: Mapped[str | None] = mapped_column(String(300), nullable=True)


class RewardReservation(Base):
    __tablename__ = "reward_reservations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("reward_requests.id"), unique=True, index=True)
    capacity_id: Mapped[str | None] = mapped_column(ForeignKey("reward_capacities.id"), nullable=True)
    points_tx_id: Mapped[str] = mapped_column(String(36))  # ledger reserve tx
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FulfillmentAttempt(Base):
    __tablename__ = "fulfillment_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("reward_requests.id"), index=True)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(20), default="created")  # created|sent|confirmed|failed|unknown|reconciled
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail_json: Mapped[str] = mapped_column(Text, default="{}")


class DeliveryReceipt(Base):
    __tablename__ = "delivery_receipts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("reward_requests.id"), unique=True)
    one_time_code_hash: Mapped[str] = mapped_column(String(64))  # RWD-07: unguessable, single-use
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    receipt_json: Mapped[str] = mapped_column(Text, default="{}")


class ReconciliationCase(Base):
    """RWD-08: unknown delivery => reconciliation first; NO auto refund."""
    __tablename__ = "reconciliation_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("reward_requests.id"), index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(40), nullable=True)  # delivered|failed — human decision
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
