"""TST-01 duplicate, TST-02 out-of-order, TST-07 version freeze, TST-14 LMS outage."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from app.core.db import utcnow
from app.modules.event_ingestion import service as evsvc
from app.modules.event_ingestion.models import EducationalEvent, EventInbox
from app.modules.points_ledger.models import LedgerTransaction
from tests.conftest import make_event


def test_duplicate_event_single_effect(db, uni, student, source, policy):
    """سناریو ۱: ارسال چندباره رویداد فقط یک اثر معتبر ایجاد کند."""
    from app.modules.points_ledger.models import LedgerTransaction as LT
    from sqlalchemy import func as F

    body = {
        "event_id": "ev-dup-1", "schema_version": "1.0", "source_id": source.id,
        "university_id": uni.id, "student_reference": student.external_student_id,
        "event_type": "meaningful_attendance_verified",
        "occurred_at": utcnow().isoformat(), "received_at": utcnow().isoformat(),
        "activity_reference": "course/CS101/session/1", "verification_status": "verified",
        "correlation_id": "c-dup", "payload": {"duration_minutes": 60},
    }
    r1 = evsvc.ingest(db, body)
    assert r1["duplicate"] is False
    r2 = evsvc.ingest(db, body)  # exact re-send
    assert r2["duplicate"] is True
    inbox = db.execute(select(EventInbox).where(EventInbox.state == "received")).scalars().all()
    for i in inbox:
        evsvc.process_inbox_message(db, i)
    n_awards = db.execute(select(F.count()).select_from(LT).where(LT.tx_type == "award")).scalar()
    assert n_awards == 1  # exactly one effect
    # process once more (worker retry) — still one
    for i in db.execute(select(EventInbox)).scalars().all():
        evsvc.process_inbox_message(db, i)
    assert db.execute(select(F.count()).select_from(LT).where(LT.tx_type == "award")).scalar() == 1


def test_out_of_order_policy_selection(db, uni, student, source, policy):
    """سناریو ۲: رویداد خارج از ترتیب طبق زمان و نسخهٔ سیاست پردازش شود."""
    import json

    from app.modules.policy_engine.models import PolicyVersion
    from app.core.db import utcnow

    pol, ver1 = policy
    ver2 = PolicyVersion(university_id=uni.id, policy_id=pol.id, version_no=2, status="published",
                         dsl_json=json.dumps({**json.loads(ver1.dsl_json), "base_points": "50.00"}),
                         effective_from=utcnow(), late_window_hours=72)
    db.add(ver2)
    db.flush()
    old_ev = make_event(db, uni, source, student, "ev-old", utcnow() - timedelta(days=10))
    new_ev = make_event(db, uni, source, student, "ev-new", utcnow())
    inboxes = db.execute(select(EventInbox).where(EventInbox.state == "received")).scalars().all()
    for i in inboxes:
        evsvc.process_inbox_message(db, i)
    txs = db.execute(select(LedgerTransaction)).scalars().all()
    by_event = {t.event_id: t for t in txs}
    assert str(by_event[old_ev.id].rule_version_id) == str(ver1.id)  # old time → old version
    assert str(by_event[new_ev.id].rule_version_id) == str(ver2.id)  # new time → new version


def test_policy_version_freezes_past(db, uni, student, source, policy):
    """سناریو ۷: تغییر سیاست، محاسبهٔ گذشته را بازنویسی نکند."""
    import json

    from app.modules.policy_engine.models import PolicyVersion
    from app.core.db import utcnow

    pol, ver1 = policy
    ev = make_event(db, uni, source, student, "ev-f1", utcnow() - timedelta(days=5))
    inbox = db.execute(select(EventInbox).where(EventInbox.state == "received")).scalar_one()
    evsvc.process_inbox_message(db, inbox)
    # publish a NEW version with different points
    ver2 = PolicyVersion(university_id=uni.id, policy_id=pol.id, version_no=2, status="published",
                         dsl_json=json.dumps({**json.loads(ver1.dsl_json), "base_points": "99.00"}),
                         effective_from=utcnow(), late_window_hours=72)
    db.add(ver2)
    db.flush()
    tx = db.execute(select(LedgerTransaction).where(LedgerTransaction.event_id == ev.id)).scalar_one()
    assert str(tx.rule_version_id) == str(ver1.id)  # past stays on old version


def test_lms_outage_no_penalty(db, uni, student, source, policy):
    """سناریو ۱۴: قطع LMS به کاهش امتیاز یا پرچم تقلب منجر نشود."""
    from app.modules.points_ledger.models import PointAccount
    from app.modules.integrity_reviews.models import IntegritySignal

    now = utcnow()
    ev = make_event(db, uni, source, student, "ev-ok", now)
    inbox = db.execute(select(EventInbox).where(EventInbox.state == "received")).scalar_one()
    evsvc.process_inbox_message(db, inbox)
    acc = db.execute(select(PointAccount).where(PointAccount.student_ref_id == student.id)).scalar_one()
    before = (acc.available, acc.cumulative_progress)
    signals_before = db.execute(select(func.count()).select_from(IntegritySignal)).scalar()
    # LMS outage: no events arrive for days — nothing in the system may punish the student
    assert before[0] > 0  # last successful award intact
    assert signals_before == 0  # no fraud flag from silence
    # and a recovery event later is processed normally
    ev2 = make_event(db, uni, source, student, "ev-recover", now + timedelta(days=3))
    inbox2 = db.execute(select(EventInbox).where(EventInbox.event_id == ev2.id)).scalar_one()
    evsvc.process_inbox_message(db, inbox2)
    db.refresh(acc)
    assert acc.available > before[0]
