"""Contract + API tests: structured errors, idempotency conflict, RBAC endpoints, health."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.db import TestingSession
from app.core.rbac import build_principal, make_principal_for_tests
from app.main import app
from app.modules.identity_access.models import StudentReference


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.core.db", fromlist=["get_db"]).get_db] = override_get_db
    return TestClient(app)


def _login_as(db, user_id, uni_id, roles, student_ref_id=None):
    p = make_principal_for_tests(user_id, uni_id, roles, student_ref_id)
    app.dependency_overrides[  # noqa: B010
        __import__("app.core.rbac", fromlist=["get_principal"]).get_principal
    ] = lambda: p
    return p


def test_health_and_system_info(client):
    r = client.get("/api/v1/healthz")
    assert r.status_code == 200
    r = client.get("/api/v1/system/info")
    assert r.status_code == 200
    assert r.json()["integration_mode"] in ("simulator", "oidc_pending_approval")


def test_structured_error_shape(client):
    r = client.get("/api/v1/points/summary")  # no auth → 401 structured
    assert r.status_code == 401
    body = r.json()
    assert {"code", "message", "correlation_id"} <= set(body.keys())


def test_points_summary_rbac(client, db, uni, student):
    principal = _login_as(db, "user-1", uni.id, ["student"], student.id)
    r = client.get("/api/v1/points/summary")
    assert r.status_code == 200
    assert r.json()["available"] == "0.00"
    # tech_admin cannot read points
    _login_as(db, "user-1", uni.id, ["tech_admin"])
    r = client.get("/api/v1/points/summary")
    assert r.status_code == 403


def test_university_isolation(client, db, uni, student):
    """SEED-01/ACC-11: data of another university is invisible."""
    from app.modules.rewards_fulfillment.models import Reward

    db.add(Reward(university_id="11111111-1111-4111-8111-000000000002", type="workshop",
                  title_fa="پاداش دانشگاه دیگر", delivery="in_app"))
    db.flush()
    _login_as(db, "user-1", uni.id, ["student"], student.id)
    r = client.get("/api/v1/rewards")
    titles = [x["title_fa"] for x in r.json()["items"]]
    assert "پاداش دانشگاه دیگر" not in titles


def test_idempotency_conflict_on_same_key_different_payload(client, db, uni, student):
    """API-04: same Idempotency-Key with different payload ⇒ 409."""
    from app.modules.rewards_fulfillment.models import Reward

    reward = Reward(university_id=uni.id, type="workshop", title_fa="w", cost_points="0.00", delivery="in_app")
    db.add(reward)
    db.flush()
    _login_as(db, "user-1", uni.id, ["student"], student.id)
    h = {"Idempotency-Key": "idem-1"}
    r1 = client.post("/api/v1/reward-requests", json={"reward_id": reward.id}, headers=h)
    assert r1.status_code == 201
    # same key + same payload → replay
    r2 = client.post("/api/v1/reward-requests", json={"reward_id": reward.id}, headers=h)
    assert r2.status_code == 201 and r2.json()["request_id"] == r1.json()["request_id"]
    # same key + different payload → conflict
    r3 = client.post("/api/v1/reward-requests", json={"reward_id": "other"}, headers=h)
    assert r3.status_code == 409 and r3.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_event_ingest_contract(client, db, uni, student, source):
    """EVT contract via HTTP: valid → 202; duplicate → duplicate=true."""
    from app.core.rbac import get_service_principal

    p = make_principal_for_tests("svc", uni.id, ["service"])
    app.dependency_overrides[get_service_principal] = lambda: p
    # زمان نسبی به اکنون — پنجرهٔ رویداد دیررس (۷۲ ساعت) با تاریخ مطلق آزمون را خراب می‌کند
    _now = datetime.now(timezone.utc)
    body = {
        "event_id": "ev-http-1", "schema_version": "1.0", "source_id": source.id,
        "university_id": uni.id, "student_reference": student.external_student_id,
        "event_type": "meaningful_attendance_verified",
        "occurred_at": (_now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "received_at": (_now - timedelta(hours=2, minutes=-1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "activity_reference": "course/CS101/session/1", "verification_status": "verified",
        "correlation_id": "c-1", "payload": {"duration_minutes": 60},
    }
    r = client.post("/api/v1/events/ingest", json=body)
    assert r.status_code == 202 and r.json()["duplicate"] is False
    # different Idempotency-Key ⇒ goes through ingest again ⇒ contract-level duplicate flag
    r2 = client.post("/api/v1/events/ingest", json=body, headers={"Idempotency-Key": "second-send"})
    assert r2.status_code == 202 and r2.json()["duplicate"] is True
    # invalid type rejected
    bad = {**body, "event_id": "ev-http-2", "event_type": "click_click"}
    r3 = client.post("/api/v1/events/ingest", json=bad)
    assert r3.status_code == 422
