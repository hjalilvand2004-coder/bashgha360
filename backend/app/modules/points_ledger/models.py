"""points_ledger models: PointAccount, LedgerTransaction, LedgerEntry (append-only), BalanceProjection, ProgressRecord."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Identity, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid

NUM = Numeric(14, 2)


class PointAccount(Base):
    __tablename__ = "point_accounts"
    __table_args__ = (
        CheckConstraint("available >= 0", name="available_nonneg"),
        CheckConstraint("reserved >= 0", name="reserved_nonneg"),
        CheckConstraint("pending >= 0", name="pending_nonneg"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="student")  # student | pool (university vault)
    student_ref_id: Mapped[str | None] = mapped_column(ForeignKey("student_references.id"), nullable=True, index=True)
    available: Mapped[float] = mapped_column(NUM, default=0)
    reserved: Mapped[float] = mapped_column(NUM, default=0)
    pending: Mapped[float] = mapped_column(NUM, default=0)
    spent_total: Mapped[float] = mapped_column(NUM, default=0)
    expired_total: Mapped[float] = mapped_column(NUM, default=0)
    cumulative_progress: Mapped[float] = mapped_column(NUM, default=0)  # LED-02: independent of spending
    __table_args__ = (
        UniqueConstraint("university_id", "student_ref_id", name="uq_pointaccount_uni_sref"),
    )


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"
    __table_args__ = (
        Index("uq_ledgertx_idem", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    tx_type: Mapped[str] = mapped_column(String(30), index=True)  # award|reserve|release|spend|expire|adjust|reversal
    status: Mapped[str] = mapped_column(String(20), default="committed")
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)  # unique (LED-07)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    event_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    rule_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reward_request_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    case_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correction_of_tx_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)  # LED-11
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_fa: Mapped[str | None] = mapped_column(String(500), nullable=True)


class LedgerEntry(Base):
    """Append-only — DB trigger denies UPDATE/DELETE (DM-03, LED-01)."""
    __tablename__ = "ledger_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tx_id: Mapped[str] = mapped_column(ForeignKey("ledger_transactions.id"), index=True)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("point_accounts.id"), index=True)
    direction: Mapped[str] = mapped_column(String(6))  # debit|credit
    bucket: Mapped[str] = mapped_column(String(12))  # pending|available|reserved|spent|expired|adjusted
    amount: Mapped[float] = mapped_column(NUM)
    balance_after: Mapped[float] = mapped_column(NUM)
    rule_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seq: Mapped[int] = mapped_column(Integer, Identity(always=False), nullable=False)


class BalanceProjection(Base):
    __tablename__ = "balance_projections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    account_id: Mapped[str] = mapped_column(ForeignKey("point_accounts.id"), unique=True, index=True)
    available: Mapped[float] = mapped_column(NUM, default=0)
    reserved: Mapped[float] = mapped_column(NUM, default=0)
    pending: Mapped[float] = mapped_column(NUM, default=0)
    cumulative_progress: Mapped[float] = mapped_column(NUM, default=0)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProgressRecord(Base):
    """PRN-03: personal progress vs valid baseline (not absolute performance)."""
    __tablename__ = "progress_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str] = mapped_column(ForeignKey("student_references.id"), index=True)
    metric: Mapped[str] = mapped_column(String(40))  # learning_streak|skill_growth|collaboration
    value: Mapped[float] = mapped_column(NUM, default=0)
    baseline_value: Mapped[float] = mapped_column(NUM, default=0)
    baseline_type: Mapped[str] = mapped_column(String(30), default="own_baseline")
    academic_period_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
