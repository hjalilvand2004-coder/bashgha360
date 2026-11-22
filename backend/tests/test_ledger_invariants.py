"""TST-05 worker retry, TST-06 corrections, TST-08 progress invariant + property tests."""
from __future__ import annotations

import uuid
from datetime import timedelta

from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import func, select

import sqlalchemy

from app.core.db import TestingSession, engine, utcnow
from app.core.money import D
from app.modules.event_ingestion import service as evsvc
from app.modules.event_ingestion.models import EventInbox
from app.modules.points_ledger import service as ledger
from app.modules.points_ledger.models import LedgerEntry, LedgerTransaction, PointAccount
from app.modules.identity_access.models import StudentReference, University
from tests.conftest import make_event


def test_worker_retry_no_double_effect(db, uni, student, source, policy):
    """سناریو ۵: Retry Worker اثر مضاعف نسازد."""
    ev = make_event(db, uni, source, student, "ev-r1", utcnow())
    inbox = db.execute(select(EventInbox).where(EventInbox.state == "received")).scalar_one()
    evsvc.process_inbox_message(db, inbox)
    n1 = db.execute(select(func.count()).select_from(LedgerTransaction)).scalar()
    for _ in range(3):  # worker retries
        evsvc.process_inbox_message(db, inbox)
    n2 = db.execute(select(func.count()).select_from(LedgerTransaction)).scalar()
    assert n1 == n2


def test_correction_compensation_traceable(db, uni, student, source, policy):
    """سناریو ۶: اصلاح نتیجه با سند جبرانی قابل پیگیری باشد."""
    ev = make_event(db, uni, source, student, "ev-c1", utcnow())
    inbox = db.execute(select(EventInbox).where(EventInbox.state == "received")).scalar_one()
    evsvc.process_inbox_message(db, inbox)
    original = db.execute(select(LedgerTransaction).where(LedgerTransaction.tx_type == "award")).scalar_one()
    comp, created = ledger.adjust(db, uni.id, student.id, D("-5.00"), progress_delta=D("-5.00"),
                                  idempotency_key="corr-1", correction_of_tx_id=original.id,
                                  reason_fa="اصلاح دستاورد نامعتبر")
    db.commit()
    trace = ledger.tx_trace(db, comp.id)
    assert original.id in trace["compensated_by"] or trace["tx"]["correction_of"] == original.id
    comp2, created2 = ledger.adjust(db, uni.id, student.id, D("-5.00"), progress_delta=D("-5.00"),
                                    idempotency_key="corr-1", correction_of_tx_id=original.id)
    assert created2 is False and comp2.id == comp.id


def test_spend_keeps_progress(db, uni, student):
    """سناریو ۸: مصرف پاداش، پیشرفت تجمعی را کاهش ندهد."""
    ledger.seed_pool(db, uni.id, D("100.00"))
    ledger.award(db, uni.id, student.id, D("40.00"), idempotency_key="p1")
    db.commit()
    acc = db.execute(select(PointAccount).where(PointAccount.student_ref_id == student.id)).scalar_one()
    progress_before = D(acc.cumulative_progress)
    ledger.reserve(db, uni.id, student.id, D("30.00"), idempotency_key="r1")
    ledger.spend(db, uni.id, student.id, D("30.00"), idempotency_key="s1")
    db.commit()
    db.refresh(acc)
    assert D(acc.cumulative_progress) == progress_before
    assert D(acc.available) == D("10.00")


# ---- Property-based: ledger invariants under random operation sequences ----

def _truncate_all():
    tables = [t for t in __import__("app.core.db", fromlist=["Base"]).Base.metadata.tables if t != "alembic_version"]
    quoted = ", ".join(f'"{t}"' for t in sorted(tables))
    import time as _time

    for _attempt in range(5):
        try:
            with engine.begin() as c:
                c.execute(sqlalchemy.text("SET LOCAL lock_timeout = '5s'"))
                c.execute(sqlalchemy.text("SET LOCAL statement_timeout = '30s'"))
                c.execute(sqlalchemy.text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
            break
        except Exception:
            if _attempt == 4:
                raise
            _time.sleep(0.5)


@settings(max_examples=5, deadline=None)
@given(st.lists(st.sampled_from(["award", "reserve", "release", "spend"]), min_size=3, max_size=12),
       st.integers(min_value=0, max_value=10**6))
def test_ledger_invariants_property(ops, seed_val):
    """ناوردایی‌ها: توازن هر تراکنش + مانده‌های غیرمنفی + بازسازی Projection از entries."""
    _truncate_all()
    s = TestingSession()
    s2 = None
    try:
        u = University(id=str(uuid.uuid4()), code=f"P{seed_val % 10000}-{uuid.uuid4().hex[:6]}", name_fa="پ")
        s.add(u)
        s.flush()
        sref = StudentReference(university_id=u.id, external_student_id=f"p-{seed_val}-{uuid.uuid4().hex[:6]}")
        s.add(sref)
        s.flush()
        ledger.seed_pool(s, u.id, D("100000.00"))
        ledger.award(s, u.id, sref.id, D("80.00"), idempotency_key="seed")
        s.commit()
        for i, op in enumerate(ops):
            amt = D(str(1 + (seed_val + i) % 7) + ".00")
            try:
                if op == "award":
                    ledger.award(s, u.id, sref.id, amt, idempotency_key=f"p-{i}")
                elif op == "reserve":
                    ledger.reserve(s, u.id, sref.id, amt, idempotency_key=f"p-{i}")
                elif op == "release":
                    ledger.release(s, u.id, sref.id, amt, idempotency_key=f"p-{i}")
                elif op == "spend":
                    ledger.spend(s, u.id, sref.id, amt, idempotency_key=f"p-{i}")
                s.commit()
            except Exception:  # noqa: BLE001 — invalid transitions must be rejected cleanly
                s.rollback()
        txs = s.execute(select(LedgerTransaction)).scalars().all()
        for t in txs:
            deb = s.execute(select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.tx_id == t.id, LedgerEntry.direction == "debit")).scalar()
            cre = s.execute(select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.tx_id == t.id, LedgerEntry.direction == "credit")).scalar()
            assert D(deb) == D(cre), f"unbalanced tx {t.id}"
        s.rollback()
        s2 = TestingSession()
        acc = s2.execute(select(PointAccount).where(PointAccount.student_ref_id == sref.id)).scalar_one()
        assert D(acc.available) >= 0 and D(acc.reserved) >= 0 and D(acc.pending) >= 0
        res = ledger.rebuild_projection(s2, acc.id)
        assert res["cached_corrected"] is False
    finally:
        # هر مثال hypothesis باید نشست‌ها را ببندد؛ وگرنه shrink بعدی روی قفل
        # تراکنشِ بازِ همین مثال بن‌بست می‌زند و خطای اصلی را می‌پوشاند.
        s.rollback()
        s.close()
        if s2 is not None:
            s2.rollback()
            s2.close()
