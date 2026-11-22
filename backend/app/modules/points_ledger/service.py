"""Points Ledger service — the financial core (LED-01..16, PRN-03).

Invariants enforced here and by DB constraints:
- append-only entries (DB trigger), balanced transactions (constraint trigger)
- non-negative available/reserved/pending (CHECK)
- idempotent commands via idempotency_key unique partial index
- row locks (SELECT .. FOR UPDATE) for concurrent safety
- cumulative_progress is independent of spending (LED-02 / TST-08)
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.db import utcnow
from ...core.errors import Conflict, InsufficientPoints
from ...core.money import D, ZERO, add, round2, sub
from .models import BalanceProjection, LedgerEntry, LedgerTransaction, PointAccount

BUCKETS = ("pending", "available", "reserved", "spent", "expired", "adjusted")

_POOL_NS = uuid.UUID("7b2f4b8e-1111-4a2e-9d33-0c1e2f3a4b5c")


def pool_account_id(university_id: str) -> str:
    return str(uuid.uuid5(_POOL_NS, f"pool:{university_id}"))


def get_or_create_account(db: Session, university_id: str, student_ref_id: str | None = None, kind: str = "student") -> PointAccount:
    """Race-safe account fetch/create; row-locked for subsequent balance math."""
    q = select(PointAccount).where(PointAccount.university_id == university_id, PointAccount.kind == kind)
    if kind == "student":
        q = q.where(PointAccount.student_ref_id == student_ref_id)
    acc = db.execute(q.with_for_update()).scalar_one_or_none()
    if acc is not None:
        return acc
    acc = PointAccount(
        id=pool_account_id(university_id) if kind == "pool" else str(uuid.uuid4()),
        university_id=university_id, kind=kind, student_ref_id=student_ref_id,
        available=ZERO, reserved=ZERO, pending=ZERO, spent_total=ZERO, expired_total=ZERO,
        cumulative_progress=ZERO,
    )
    try:
        with db.begin_nested():
            db.add(acc)
            db.flush()
    except IntegrityError:
        acc = db.execute(q.with_for_update()).scalar_one()
    return acc


def seed_pool(db: Session, university_id: str, initial: Decimal) -> PointAccount:
    """University vault — a real, policy-set global cap on issued points (documented demo number)."""
    pid = pool_account_id(university_id)
    acc = db.get(PointAccount, pid)
    if acc is None:
        acc = PointAccount(id=pid, university_id=university_id, kind="pool", student_ref_id=None,
                           available=ZERO, reserved=ZERO, pending=ZERO, spent_total=ZERO,
                           expired_total=ZERO, cumulative_progress=ZERO)
        try:
            with db.begin_nested():
                db.add(acc)
                db.flush()
        except IntegrityError:
            acc = db.get(PointAccount, pid)
    acc.available = add(acc.available, initial)
    _upsert_projection(db, acc)
    return acc


def _upsert_projection(db: Session, acc: PointAccount) -> None:
    proj = db.execute(select(BalanceProjection).where(BalanceProjection.account_id == acc.id)).scalar_one_or_none()
    if proj is None:
        proj = BalanceProjection(id=str(uuid.uuid4()), account_id=acc.id, as_of=utcnow())
        db.add(proj)
    proj.available, proj.reserved, proj.pending = acc.available, acc.reserved, acc.pending
    proj.cumulative_progress = acc.cumulative_progress
    proj.as_of = utcnow()


class _BucketDelta:
    """Tracks per-account bucket changes to write entries with correct balance_after."""

    def __init__(self):
        self.deltas: dict[tuple[str, str], Decimal] = {}  # (account_id, bucket) -> signed delta
        self.balances: dict[tuple[str, str], Decimal] = {}

    def apply(self, acc: PointAccount, bucket: str, delta: Decimal) -> None:
        key = (acc.id, bucket)
        self.deltas[key] = self.deltas.get(key, ZERO) + D(delta)
        current = self.balances.get(key)
        if current is None:
            current = D(getattr(acc, bucket if bucket in ("pending", "available", "reserved") else "_sink"))
            if bucket not in ("pending", "available", "reserved"):
                current = ZERO
        self.balances[key] = current + D(delta)


def _entry(db: Session, tx: LedgerTransaction, acc: PointAccount, direction: str, bucket: str,
           amount: Decimal, balance_after: Decimal, reference: str | None, rule_version_id: str | None) -> None:
    db.add(LedgerEntry(tx_id=tx.id, university_id=tx.university_id, account_id=acc.id,
                       direction=direction, bucket=bucket, amount=amount, balance_after=balance_after,
                       rule_version_id=rule_version_id, reference=reference))


def _new_tx(db: Session, university_id: str, student_ref_id: str | None, tx_type: str,
            idempotency_key: str | None = None, actor: str | None = None, reason_fa: str | None = None,
            event_id: str | None = None, rule_version_id: str | None = None,
            reward_request_id: str | None = None, case_id: str | None = None,
            correction_of_tx_id: str | None = None) -> tuple[LedgerTransaction, bool]:
    """LED-06/07: idempotent tx creation enforced by the DB unique partial index."""
    if idempotency_key:
        existing = db.execute(select(LedgerTransaction).where(
            LedgerTransaction.idempotency_key == idempotency_key)).scalar_one_or_none()
        if existing is not None:
            return existing, False
    tx = LedgerTransaction(id=str(uuid.uuid4()), university_id=university_id, tx_type=tx_type,
                           status="committed", idempotency_key=idempotency_key, student_ref_id=student_ref_id or "",
                           event_id=event_id, rule_version_id=rule_version_id, reward_request_id=reward_request_id,
                           case_id=case_id, correction_of_tx_id=correction_of_tx_id, actor=actor, reason_fa=reason_fa)
    try:
        with db.begin_nested():
            db.add(tx)
            db.flush()
    except IntegrityError:
        if idempotency_key:
            existing = db.execute(select(LedgerTransaction).where(
                LedgerTransaction.idempotency_key == idempotency_key)).scalar_one()
            return existing, False
        raise
    return tx, True


def _bucket_balance(db: Session, acc: PointAccount, bucket: str) -> Decimal:
    """Authoritative bucket balance = sum of entries (LED-12: projection rebuildable)."""
    row = db.execute(text(
        "SELECT COALESCE(SUM(CASE WHEN direction='credit' THEN amount ELSE -amount END),0) "
        "FROM ledger_entries WHERE account_id=:a AND bucket=:b"
    ), {"a": acc.id, "b": bucket}).scalar()
    return round2(row or 0)


def _record(db: Session, acc: PointAccount, bucket: str, delta: Decimal) -> Decimal:
    """Apply a signed delta to the account's cached columns and return the new bucket balance."""
    if bucket == "available":
        acc.available = add(acc.available, delta)
        return acc.available
    if bucket == "reserved":
        acc.reserved = add(acc.reserved, delta)
        return acc.reserved
    if bucket == "pending":
        acc.pending = add(acc.pending, delta)
        return acc.pending
    if bucket == "spent":
        acc.spent_total = add(acc.spent_total, delta if delta > 0 else 0)
        return acc.spent_total
    if bucket == "expired":
        acc.expired_total = add(acc.expired_total, delta if delta > 0 else 0)
        return acc.expired_total
    return _bucket_balance(db, acc, bucket)


def award(db: Session, university_id: str, student_ref_id: str, amount: Decimal, *, to_bucket: str = "available",
          idempotency_key: str | None = None, event_id: str | None = None, rule_version_id: str | None = None,
          reason_fa: str | None = None, actor: str | None = None, counts_progress: bool = True,
          reference: str | None = None) -> tuple[LedgerTransaction, bool]:
    """Issue points from the university vault into pending|available (LED, PNT)."""
    amount = round2(amount)
    if amount <= 0:
        raise Conflict("مبلغ امتیاز باید مثبت باشد.")
    pool = get_or_create_account(db, university_id, kind="pool")
    acc = get_or_create_account(db, university_id, student_ref_id)
    tx, created = _new_tx(db, university_id, student_ref_id, "award", idempotency_key=idempotency_key,
                          actor=actor, reason_fa=reason_fa, event_id=event_id, rule_version_id=rule_version_id)
    if not created:
        return tx, False
    pool_after = _record(db, pool, "available", -amount)
    _entry(db, tx, pool, "debit", "available", amount, pool_after, reference, rule_version_id)
    acc_after = _record(db, acc, to_bucket, amount)
    _entry(db, tx, acc, "credit", to_bucket, amount, acc_after, reference, rule_version_id)
    if counts_progress:
        acc.cumulative_progress = add(acc.cumulative_progress, amount)
    _upsert_projection(db, acc)
    _upsert_projection(db, pool)
    return tx, True


def verify_pending(db: Session, university_id: str, student_ref_id: str, amount: Decimal, *,
                   idempotency_key: str | None = None, event_id: str | None = None,
                   reason_fa: str | None = None, actor: str | None = None) -> tuple[LedgerTransaction, bool]:
    """pending → available after human verification (LED-04)."""
    amount = round2(amount)
    acc = get_or_create_account(db, university_id, student_ref_id)
    tx, created = _new_tx(db, university_id, student_ref_id, "award", idempotency_key=idempotency_key,
                          actor=actor, reason_fa=reason_fa, event_id=event_id)
    if not created:
        return tx, False
    if D(acc.pending) < amount:
        raise Conflict("موجودی در انتظار کافی نیست.")
    p_after = _record(db, acc, "pending", -amount)
    _entry(db, tx, acc, "debit", "pending", amount, p_after, None, None)
    a_after = _record(db, acc, "available", amount)
    _entry(db, tx, acc, "credit", "available", amount, a_after, None, None)
    _upsert_projection(db, acc)
    return tx, True


def reserve(db: Session, university_id: str, student_ref_id: str, amount: Decimal, *,
            idempotency_key: str | None = None, reward_request_id: str | None = None,
            reason_fa: str | None = None, actor: str | None = None) -> tuple[LedgerTransaction, bool]:
    """available → reserved (TST-04: multi-device safe via row lock)."""
    amount = round2(amount)
    acc = get_or_create_account(db, university_id, student_ref_id)
    tx, created = _new_tx(db, university_id, student_ref_id, "reserve", idempotency_key=idempotency_key,
                          actor=actor, reason_fa=reason_fa, reward_request_id=reward_request_id)
    if not created:
        return tx, False
    if D(acc.available) < amount:
        raise InsufficientPoints("امتیاز قابل مصرف کافی نیست.")
    a_after = _record(db, acc, "available", -amount)
    _entry(db, tx, acc, "debit", "available", amount, a_after, None, None)
    r_after = _record(db, acc, "reserved", amount)
    _entry(db, tx, acc, "credit", "reserved", amount, r_after, None, None)
    _upsert_projection(db, acc)
    return tx, True


def release(db: Session, university_id: str, student_ref_id: str, amount: Decimal, *,
            idempotency_key: str | None = None, reward_request_id: str | None = None,
            reason_fa: str | None = None, actor: str | None = None) -> tuple[LedgerTransaction, bool]:
    """reserved → available (cancel / expired reservation)."""
    amount = round2(amount)
    acc = get_or_create_account(db, university_id, student_ref_id)
    tx, created = _new_tx(db, university_id, student_ref_id, "release", idempotency_key=idempotency_key,
                          actor=actor, reason_fa=reason_fa, reward_request_id=reward_request_id)
    if not created:
        return tx, False
    if D(acc.reserved) < amount:
        raise Conflict("رزرو کافی برای آزادسازی وجود ندارد.")
    r_after = _record(db, acc, "reserved", -amount)
    _entry(db, tx, acc, "debit", "reserved", amount, r_after, None, None)
    a_after = _record(db, acc, "available", amount)
    _entry(db, tx, acc, "credit", "available", amount, a_after, None, None)
    _upsert_projection(db, acc)
    return tx, True


def spend(db: Session, university_id: str, student_ref_id: str, amount: Decimal, *,
          idempotency_key: str | None = None, reward_request_id: str | None = None,
          reason_fa: str | None = None, actor: str | None = None) -> tuple[LedgerTransaction, bool]:
    """reserved → pool (delivery). spent_total is a display counter; points return to the vault.

    Never touches cumulative_progress (TST-08). Balanced: debit student.reserved, credit pool.available.
    """
    amount = round2(amount)
    pool = get_or_create_account(db, university_id, kind="pool")
    acc = get_or_create_account(db, university_id, student_ref_id)
    tx, created = _new_tx(db, university_id, student_ref_id, "spend", idempotency_key=idempotency_key,
                          actor=actor, reason_fa=reason_fa, reward_request_id=reward_request_id)
    if not created:
        return tx, False
    if D(acc.reserved) < amount:
        raise Conflict("رزرو کافی برای مصرف وجود ندارد.")
    r_after = _record(db, acc, "reserved", -amount)
    _entry(db, tx, acc, "debit", "reserved", amount, r_after, None, None)
    pool_after = _record(db, pool, "available", amount)
    _entry(db, tx, pool, "credit", "available", amount, pool_after, None, None)
    acc.spent_total = add(acc.spent_total, amount)  # display counter (not a bucket entry)
    _upsert_projection(db, acc)
    _upsert_projection(db, pool)
    return tx, True


def expire(db: Session, university_id: str, student_ref_id: str, amount: Decimal, *,
           idempotency_key: str | None = None, reason_fa: str | None = None, actor: str | None = None):
    """available → expired per published policy (LED-15). Balanced: debit student.available, credit pool."""
    amount = round2(amount)
    pool = get_or_create_account(db, university_id, kind="pool")
    acc = get_or_create_account(db, university_id, student_ref_id)
    tx, created = _new_tx(db, university_id, student_ref_id, "expire", idempotency_key=idempotency_key,
                          actor=actor, reason_fa=reason_fa)
    if not created:
        return tx, False
    a_after = _record(db, acc, "available", -amount)
    _entry(db, tx, acc, "debit", "available", amount, a_after, None, None)
    pool_after = _record(db, pool, "available", amount)
    _entry(db, tx, pool, "credit", "available", amount, pool_after, None, None)
    acc.expired_total = add(acc.expired_total, amount)
    _upsert_projection(db, acc)
    _upsert_projection(db, pool)
    return tx, True


def adjust(db: Session, university_id: str, student_ref_id: str, delta: Decimal, *, bucket: str = "available",
           progress_delta: Decimal = ZERO, idempotency_key: str | None = None, case_id: str | None = None,
           correction_of_tx_id: str | None = None, reason_fa: str | None = None, actor: str | None = None) -> tuple[LedgerTransaction, bool]:
    """Compensating document (LED-11/14) — never deletes history; may reduce progress per approved policy."""
    delta = round2(delta)
    progress_delta = round2(progress_delta)
    if delta == 0 and progress_delta == 0:
        raise Conflict("سند جبرانی بدون اثر ثبت نمی‌شود.")
    pool = get_or_create_account(db, university_id, kind="pool")
    acc = get_or_create_account(db, university_id, student_ref_id)
    tx, created = _new_tx(db, university_id, student_ref_id, "adjust", idempotency_key=idempotency_key,
                          actor=actor, reason_fa=reason_fa, case_id=case_id, correction_of_tx_id=correction_of_tx_id)
    if not created:
        return tx, False
    if delta > 0:
        pool_after = _record(db, pool, "available", -delta)
        _entry(db, tx, pool, "debit", "available", delta, pool_after, None, None)
        a_after = _record(db, acc, bucket, delta)
        _entry(db, tx, acc, "credit", bucket, delta, a_after, None, None)
    else:
        a_after = _record(db, acc, bucket, delta)
        _entry(db, tx, acc, "debit", bucket, -delta, a_after, None, None)
        pool_after = _record(db, pool, "available", -delta)
        _entry(db, tx, pool, "credit", "available", -delta, pool_after, None, None)
    if progress_delta != 0:
        acc.cumulative_progress = add(acc.cumulative_progress, progress_delta)
    _upsert_projection(db, acc)
    _upsert_projection(db, pool)
    return tx, True


def rebuild_projection(db: Session, account_id: str) -> dict:
    """LED-12: reconstruct balances from the append-only entries."""
    acc = db.get(PointAccount, account_id)
    sums = {}
    for b in BUCKETS:
        sums[b] = _bucket_balance(db, acc, b)
    changed = (acc.available != sums["available"] or acc.reserved != sums["reserved"] or acc.pending != sums["pending"])
    acc.available, acc.reserved, acc.pending = sums["available"], sums["reserved"], sums["pending"]
    _upsert_projection(db, acc)
    return {"account_id": account_id, "buckets": {k: str(v) for k, v in sums.items()}, "cached_corrected": changed}


def reconcile_account(db: Session, account_id: str) -> dict:
    """Job تطبیق مانده و هشدار مغایرت (LED-12)."""
    acc = db.get(PointAccount, account_id)
    if acc is None:
        return {"account_id": account_id, "exists": False}
    sums = {b: _bucket_balance(db, acc, b) for b in ("available", "reserved", "pending")}
    mismatch = (D(acc.available) != sums["available"] or D(acc.reserved) != sums["reserved"] or D(acc.pending) != sums["pending"])
    return {
        "account_id": account_id, "exists": True, "mismatch": mismatch,
        "cached": {"available": str(acc.available), "reserved": str(acc.reserved), "pending": str(acc.pending)},
        "from_entries": {k: str(v) for k, v in sums.items()},
    }


def tx_trace(db: Session, tx_id: str) -> dict:
    """Full trace of a transaction incl. linked CalculationTrace (PNT-05/PRN-08)."""
    tx = db.get(LedgerTransaction, tx_id)
    if tx is None:
        raise Conflict("تراکنش یافت نشد.")
    entries = db.execute(select(LedgerEntry).where(LedgerEntry.tx_id == tx.id).order_by(LedgerEntry.seq)).scalars().all()
    trace = {"tx": {"id": tx.id, "type": tx.tx_type, "status": tx.status, "reason_fa": tx.reason_fa,
                    "idempotency_key": tx.idempotency_key, "correction_of": tx.correction_of_tx_id,
                    "event_id": tx.event_id, "rule_version_id": tx.rule_version_id,
                    "created_at": tx.created_at.isoformat()},
             "entries": [{"account": e.account_id, "direction": e.direction, "bucket": e.bucket,
                          "amount": str(e.amount), "balance_after": str(e.balance_after)} for e in entries],
             "compensated_by": [r.id for r in db.execute(select(LedgerTransaction).where(
                 LedgerTransaction.correction_of_tx_id == tx.id)).scalars().all()]}
    return trace
