"""Concurrency tests on real PostgreSQL — TST-03, TST-04, TST-19."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from sqlalchemy import select

from app.core.db import TestingSession, utcnow
from app.core.money import D
from app.modules.points_ledger import service as ledger
from app.modules.policy_engine import service as polsvc
from app.modules.rewards_fulfillment import service as rw
from app.modules.rewards_fulfillment.models import Reward, RewardRequest
from tests.conftest import make_event


def _worker(fn, *args):
    s = TestingSession()
    try:
        out = fn(s, *args)
        s.commit()
        return out
    except Exception as exc:  # noqa: BLE001
        s.rollback()
        return ("ERROR", f"{type(exc).__name__}: {str(exc)[:140]}")
    finally:
        s.close()


def test_concurrent_spend_never_negative(db, uni, student):
    """سناریو ۴: درخواست هم‌زمان از چند دستگاه باعث خرج مضاعف نشود."""
    ledger.seed_pool(db, uni.id, D("1000.00"))
    tx, _ = ledger.award(db, uni.id, student.id, D("50.00"), idempotency_key="seed-award")
    db.commit()

    def reserve_and_spend(s, i):
        ledger.reserve(s, uni.id, student.id, D("20.00"), idempotency_key=f"spend-{i}")
        return ledger.spend(s, uni.id, student.id, D("20.00"), idempotency_key=f"spend-{i}")

    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_worker, reserve_and_spend, i) for i in range(8)]
        results = [f.result() for f in futs]
    ok = [r for r in results if not (isinstance(r, tuple) and r[0] == "ERROR")]
    errs = [r for r in results if isinstance(r, tuple) and r[0] == "ERROR"]
    assert len(ok) == 2, f"ok={len(ok)} errs={errs[:2]}"  # exactly two 20-point spends fit in 50
    assert len(errs) == 6, f"errs={errs[:2]}"
    s = TestingSession()
    acc = s.execute(select(__import__("app.modules.points_ledger.models", fromlist=["PointAccount"]).PointAccount)
                    .where(__import__("app.modules.points_ledger.models", fromlist=["PointAccount"]).PointAccount.student_ref_id == student.id)).scalar_one()
    assert D(acc.available) == D("10.00")
    assert D(acc.available) >= 0 and D(acc.reserved) >= 0


def test_capacity_race_single_winner(db, uni, student):
    """سناریو ۳: دو درخواست برای آخرین ظرفیت، بیش از یک رزرو موفق ایجاد نکند."""
    from app.core.security import hash_password
    from app.modules.identity_access.models import StudentReference, User, UserRoleScope
    from app.modules.memberships_consents import service as mem
    from app.modules.memberships_consents.models import Membership, TermsVersion

    # reward with capacity 1
    reward = Reward(university_id=uni.id, type="resource_access", title_fa="آخرین ظرفیت",
                    cost_points=D("5.00"), capacity_total=1, allocation="first_come", delivery="in_app")
    db.add(reward)
    db.flush()
    # two students with membership + enough points
    srefs = []
    for i in range(2):
        u = User(username=f"race{i}@test", display_name=f"دانشجو {i}", password_hash=hash_password("pw"))
        db.add(u)
        db.flush()
        db.add(UserRoleScope(user_id=u.id, role_code="student", university_id=uni.id))
        sref = StudentReference(university_id=uni.id, user_id=u.id, external_student_id=f"race-{i}")
        db.add(sref)
        terms = TermsVersion(university_id=uni.id, version_no=9 + i, title_fa="t", content_fa="c", is_current=True)
        db.add(terms)
        db.flush()
        mem.join(db, university_id=uni.id, student_ref=sref, terms_version_id=terms.id, consents={})
        ledger.seed_pool(db, uni.id, D("100.00"))
        ledger.award(db, uni.id, sref.id, D("20.00"), idempotency_key=f"race-award-{i}")
        srefs.append(sref)
    db.commit()

    def try_request(s, sref_id):
        sref = s.get(StudentReference, sref_id)
        return rw.request_reward(s, university_id=uni.id, student_ref=sref, reward_id=reward.id, actor="test")

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(_worker, try_request, sr.id) for sr in srefs]
        results = [f.result() for f in futs]
    ok = [r for r in results if not (isinstance(r, tuple) and r[0] == "ERROR")]
    exhausted = [r for r in results if isinstance(r, tuple) and "CapacityExhausted" in r[1]]
    assert len(ok) == 1 and len(exhausted) == 1, f"results={results}"
    s = TestingSession()
    from app.modules.rewards_fulfillment.models import RewardCapacity

    cap = s.execute(select(RewardCapacity).where(RewardCapacity.reward_id == reward.id)).scalar_one()
    assert cap.reserved_count == 1 and cap.final_count == 0


def test_cap_parallel_respected(db, uni, student, source, policy):
    """سناریو ۱۹: سقف امتیاز در پردازش موازی رعایت شود."""
    from app.modules.event_ingestion import service as evsvc
    from app.modules.event_ingestion.models import EventInbox
    from app.modules.points_ledger.models import PointAccount

    ledger.seed_pool(db, uni.id, D("10000.00"))
    db.commit()
    now = utcnow()
    for i in range(6):
        make_event(db, uni, source, student, f"ev-cap-{i}", now + timedelta(minutes=i))
    db.commit()

    def process_one(s, inbox_id):
        inbox = s.get(EventInbox, inbox_id)
        evsvc.process_inbox_message(s, inbox)

    inboxes = db.execute(select(EventInbox).where(EventInbox.state == "received")).scalars().all()
    ids = [i.id for i in inboxes]
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(lambda i: _worker(process_one, i), ids))

    s = TestingSession()
    from app.modules.points_ledger.models import PointAccount as PA

    acc = s.execute(select(PA).where(PA.student_ref_id == student.id)).scalar_one()
    total = D(acc.available) + D(acc.reserved) + D(acc.pending)
    # per_day cap = 25 — regardless of parallelism, never exceeded
    assert total <= D("25.00"), f"cap violated: {total}"
