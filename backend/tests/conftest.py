"""Shared test fixtures — real PostgreSQL (SEC-15: no SQLite)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres:@/club360_test?host=/home/z/my-project/.pgdata")
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
import sqlalchemy  # noqa: E402

from app import models_registry  # noqa: E402,F401
from app.core.db import Base, TestingSession, engine  # noqa: E402
from app.core.money import Decimal  # noqa: E402

D = Decimal


@pytest.fixture(autouse=True)
def clean_db():
    """Truncate all domain tables before each test (fast, real PG).

    Terminates stale idle-in-transaction sessions first so TRUNCATE never blocks
    on locks left by pooled connections of previous tests.
    """
    tables = [t for t in Base.metadata.tables if t != "alembic_version"]
    quoted = ", ".join(f'"{t}"' for t in sorted(tables))
    import time

    for attempt in range(5):
        try:
            with engine.begin() as c:
                c.execute(sqlalchemy.text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND pid <> pg_backend_pid() "
                    "AND state <> 'active'"))  # tests own the DB: clear every stale backend
                c.execute(sqlalchemy.text("SET LOCAL lock_timeout = '5s'"))
                c.execute(sqlalchemy.text("SET LOCAL statement_timeout = '30s'"))
                c.execute(sqlalchemy.text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
            break
        except Exception:
            if attempt == 4:
                raise
            time.sleep(0.5)
    yield
    # تضمین ضدبن‌بست: نشست‌های درون‌آزمونی که بسته نشده‌اند (مثلاً s = TestingSession()
    # در آزمون‌های هم‌روندی/property) اتصال را با تراکنش باز نگه می‌دارند؛
    # dispose اتصال‌های checkout شده را نمی‌بندد، پس در سمت سرور هر backend
    # غیرفعال این پایگاه‌داده را می‌کشیم تا هیچ قفلی از آزمون قبلی نماند.
    try:
        with engine.connect() as c:
            c.execute(sqlalchemy.text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = current_database() AND pid <> pg_backend_pid() "
                "AND state <> 'active' AND application_name <> 'psql'"))
        engine.dispose()
    except Exception:  # noqa: BLE001 — teardown must never raise
        pass


@pytest.fixture
def db():
    s = TestingSession()
    yield s
    s.rollback()
    s.close()


@pytest.fixture
def uni(db):
    from app.modules.identity_access.models import University

    u = University(id="11111111-1111-4111-8111-000000000001", code="TU1", name_fa="دانشگاه آزمون ۱")
    db.add(u)
    u2 = University(id="11111111-1111-4111-8111-000000000002", code="TU2", name_fa="دانشگاه آزمون ۲")
    db.add(u2)
    db.flush()
    return u


@pytest.fixture
def student(db, uni):
    """A student with membership + consents + account."""
    from app.core.security import hash_password
    from app.modules.identity_access.models import StudentReference, User, UserRoleScope
    from app.modules.memberships_consents.models import Membership, TermsVersion
    from app.modules.memberships_consents import service as mem

    user = User(username="stu@test", display_name="دانشجوی آزمون", password_hash=hash_password("pw"),
                identity_mode="local")
    db.add(user)
    db.flush()
    db.add(UserRoleScope(user_id=user.id, role_code="student", university_id=uni.id))
    sref = StudentReference(university_id=uni.id, user_id=user.id, external_student_id="stu-x1",
                            program="مهندسی کامپیوتر", source="s360_sim")
    db.add(sref)
    terms = TermsVersion(university_id=uni.id, version_no=1, title_fa="شرایط آزمون",
                         content_fa="متن آزمایشی", is_current=True, published_at=TermsVersion.__table__.c.created_at.default.arg(None) if False else None)
    db.add(terms)
    db.flush()
    mem.join(db, university_id=uni.id, student_ref=sref, terms_version_id=terms.id,
             consents={"personalization": True, "public_badge": False, "notifications": True})
    db.flush()
    return sref


@pytest.fixture
def policy(db, uni):
    """Published attendance policy with caps + diminishing returns (demo numbers)."""
    import json
    from datetime import timedelta

    from app.core.db import utcnow
    from app.modules.policy_engine.models import Policy, PolicyVersion

    pol = Policy(university_id=uni.id, code="ATT", title_fa="حضور (آزمون)", exclusive_group="attendance", priority=10)
    db.add(pol)
    db.flush()
    dsl = {
        "rule_id": "att_v1", "event_type": "meaningful_attendance_verified", "path": "learning",
        "conditions": {"all": [{"field": "payload.duration_minutes", "op": ">=", "value": 45}]},
        "base_points": "10.00",
        "quality_multiplier": {"field": "payload.quality", "map": {"high": "1.20", "normal": "1.00"}, "default": "1.00"},
        "progress_multiplier": {"default": "1.00"},
        "repeat_policy": {"window_days": 7, "diminishing": ["1.00", "1.00", "0.50"], "beyond": "0"},
        "caps": {"per_day": "25.00"},
        "exclusive_group": "attendance",
        "human_reason_template": "حضور تأییدشده در {activity_reference}",
    }
    ver = PolicyVersion(university_id=uni.id, policy_id=pol.id, version_no=1, status="published",
                        dsl_json=json.dumps(dsl), effective_from=utcnow() - timedelta(days=30),
                        late_window_hours=72)
    db.add(ver)
    db.flush()
    return pol, ver


@pytest.fixture
def source(db, uni):
    from app.modules.event_ingestion.models import IntegrationSource

    src = IntegrationSource(university_id=uni.id, code="lms-sim", name_fa="شبیه‌ساز (آزمون)",
                            auth_key_hash="k-test", is_active=True, is_simulator=True)
    db.add(src)
    db.flush()
    return src


def make_event(db, uni, source, sref, event_id: str, occurred_at, event_type="meaningful_attendance_verified",
               payload: dict | None = None, status="verified"):
    import json
    from datetime import timedelta

    from app.core.db import utcnow
    from app.modules.event_ingestion.models import EducationalEvent, EventInbox

    ev = EducationalEvent(university_id=uni.id, event_id=event_id, schema_version="1.0", source_id=source.id,
                          student_reference=sref.external_student_id, event_type=event_type,
                          occurred_at=occurred_at, received_at=occurred_at + timedelta(minutes=1),
                          activity_reference=f"activity/{event_id}", verification_status=status,
                          correlation_id=f"c-{event_id}",
                          payload_json=json.dumps(payload or {"duration_minutes": 60}, ensure_ascii=False))
    db.add(ev)
    db.flush()
    db.add(EventInbox(university_id=uni.id, message_id=f"{source.code}:{event_id}:r1", event_id=ev.id,
                      state="received"))
    db.flush()
    return ev


def account_of(db, sref):
    from app.modules.points_ledger.models import PointAccount

    return db.execute(select_account(sref)).scalar_one_or_none()


def select_account(sref):
    from sqlalchemy import select

    from app.modules.points_ledger.models import PointAccount

    return select(PointAccount).where(PointAccount.student_ref_id == sref.id)
