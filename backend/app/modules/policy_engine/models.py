"""policy_engine models: Policy, PolicyVersion, PolicyApproval, RuleSimulation, RuleEvaluation, PolicyCapUsage."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class Policy(Base):
    __tablename__ = "policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    code: Mapped[str] = mapped_column(String(60))
    title_fa: Mapped[str] = mapped_column(String(200))
    exclusive_group: Mapped[str | None] = mapped_column(String(60), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)  # lower wins inside exclusive_group
    __table_args__ = (UniqueConstraint("university_id", "code", name="uq_policy_uni_code"),)


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    dsl_json: Mapped[str] = mapped_column(Text)  # validated RuleSpec — no eval (PNT-02)
    academic_period_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    late_window_hours: Mapped[int] = mapped_column(Integer, default=72)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    change_note_fa: Mapped[str | None] = mapped_column(String(500), nullable=True)
    __table_args__ = (UniqueConstraint("policy_id", "version_no", name="uq_policyversion_no"),)


class PolicyApproval(Base):
    __tablename__ = "policy_approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("policy_versions.id"), index=True)
    approver_user_id: Mapped[str] = mapped_column(String(36))
    decision: Mapped[str] = mapped_column(String(20))  # approve|reject
    comment_fa: Mapped[str | None] = mapped_column(String(500), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("version_id", "approver_user_id", name="uq_policyapproval"),)


class RuleSimulation(Base):
    __tablename__ = "rule_simulations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("policy_versions.id"), index=True)
    input_json: Mapped[str] = mapped_column(Text)
    output_json: Mapped[str] = mapped_column(Text)
    ran_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class RuleEvaluation(Base):
    """Calculation Trace for every decision (PNT-05)."""
    __tablename__ = "rule_evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("educational_events.id"), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("policy_versions.id"), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    matched: Mapped[bool] = mapped_column(default=False)
    conditions_result: Mapped[str] = mapped_column(Text, default="{}")
    effective_inputs: Mapped[str] = mapped_column(Text, default="{}")
    caps_applied: Mapped[str] = mapped_column(Text, default="{}")
    rounding: Mapped[str] = mapped_column(String(40), default="ROUND_HALF_UP@2dp")
    final_points: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    human_reason_fa: Mapped[str] = mapped_column(String(500), default="")
    excluded_reason_fa: Mapped[str | None] = mapped_column(String(300), nullable=True)
    tx_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class PolicyCapUsage(Base):
    """Concurrency-safe cap ledger — row-locked per (student, version, window)."""
    __tablename__ = "policy_cap_usage"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36))
    version_id: Mapped[str] = mapped_column(ForeignKey("policy_versions.id"))
    window_key: Mapped[str] = mapped_column(String(60))  # e.g. day:2026-11-11 / period:<id>
    used: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    __table_args__ = (UniqueConstraint("student_ref_id", "version_id", "window_key", name="uq_capusage"),)
