"""v1.5 پایلوت زندگی دانشجویی — چهار وعدهٔ محصول روی PostgreSQL واقعی.

اصول آزمون‌شده (ارزیابی v1.5):
  - ارزش فوری بدون امتیاز: هیچ مسیر هم‌پایه/فرصت/بسته/صدا امتیاز نمی‌دهد یا نمی‌گیرد.
  - هم‌پایه: ظرفیت جمع کوچک، شرکت آزمایشی، خروج امن، گزارش محرمانه برای مدیر.
  - فرصت‌های زنده: پر شدن ظرفیت = صف انتظار شفاف (نه مزیت امتیازی)؛ لغو، سرِ صف را ارتقا می‌دهد.
  - بستهٔ ساخت: صندلی محفوظ تازه‌وارد فقط با پیشرفت تجمعی کم (< ۵۰) قابل استفاده است.
  - صدای دانشجو: رأی برابر و یک‌بارمصرف؛ گذار وضعیت فقط در مسیر مصوب.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db, utcnow
from app.core.rbac import get_principal, make_principal_for_tests
from app.main import app
from app.modules.points_ledger.models import PointAccount
from app.modules.student_life.models import (
    BundleEnrollment, Opportunity, OpportunityReg, PeerActivity, PeerReport, PortfolioBundle,
    ProposalVote, StudentProposal,
)


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _as(db, user_id, uni_id, roles, student_ref_id=None):
    p = make_principal_for_tests(user_id, uni_id, roles, student_ref_id)
    app.dependency_overrides[get_principal] = lambda: p
    return p


def make_sref(db, uni, ext_id: str, username: str) -> str:
    """StudentReference واقعی — برای FK جدول point_accounts لازم است."""
    from app.core.security import hash_password
    from app.modules.identity_access.models import StudentReference, User

    u = User(username=username, display_name=username, password_hash=hash_password("pw"), identity_mode="local")
    db.add(u)
    db.flush()
    sr = StudentReference(university_id=uni.id, user_id=u.id, external_student_id=ext_id, source="s360_sim")
    db.add(sr)
    db.flush()
    return sr.id


@pytest.fixture
def opp(db, uni):
    o = Opportunity(university_id=uni.id, title_fa="بازدید آزمایشگاه (آزمون)", what_fa="دیدن نزدیک",
                    location_fa="ساختمان ۳", starts_at=utcnow() + timedelta(days=2), duration_minutes=60,
                    cost_label_fa="رایگان", is_free=True, prereq_fa="هیچ", solo_friendly=True,
                    capacity=2, kind="visit", state="published", created_at=utcnow())
    db.add(o)
    db.flush()
    return o


@pytest.fixture
def bundle(db, uni):
    import json
    b = PortfolioBundle(university_id=uni.id, title_fa="اولین پوسترت را بساز (آزمون)",
                        output_fa="یک پوستر چاپ‌شنی", tools_fa="قالب آماده", guide_fa="راهنمای حضوری",
                        feedback_note_fa="بازخورد واقعی", steps_json=json.dumps([{"label_fa": "ایده"}, {"label_fa": "ساخت"}]),
                        estimated_hours=2, capacity=2, newcomer_seats=1, state="published", created_at=utcnow())
    db.add(b)
    db.flush()
    return b


# ---------------- هم‌پایه ----------------

def test_peer_create_list_and_seats(client, db, uni):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.post("/api/v1/student-life/peer-up", json={
        "title_fa": "هم‌مطالعهٔ ریاضی", "activity_kind": "study", "time_label_fa": "دوشنبه ۱۷:۰۰",
        "location_fa": "سالن مطالعه", "capacity": 3, "trial_ok": True, "interest_tags": ["ریاضی", "درس"]})
    assert r.status_code == 200
    items = client.get("/api/v1/student-life/peer-up").json()["items"]
    assert len(items) == 1 and items[0]["seats_left"] == 3
    assert items[0]["is_host"] is True and items[0]["interest_tags"] == ["ریاضی", "درس"]


def test_peer_create_rejects_bad_capacity(client, db, uni):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.post("/api/v1/student-life/peer-up", json={
        "title_fa": "جمع خیلی بزرگ", "activity_kind": "study", "time_label_fa": "دوشنبه",
        "location_fa": "سالن", "capacity": 20, "trial_ok": True, "interest_tags": []})
    assert r.status_code == 422


def test_peer_join_trial_capacity_and_duplicate(client, db, uni):
    _as(db, "u-h", uni.id, ["student"], student_ref_id="sref-h")
    aid = client.post("/api/v1/student-life/peer-up", json={
        "title_fa": "همراه تمرین زبان", "activity_kind": "language", "time_label_fa": "سه‌شنبه ۱۰:۰۰",
        "location_fa": "کافه دانشجویی", "capacity": 2, "trial_ok": True, "interest_tags": ["زبان"]}).json()["id"]
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    assert client.post(f"/api/v1/student-life/peer-up/{aid}/join", json={"mode": "trial"}).json()["seats_left"] == 1
    _as(db, "u-2", uni.id, ["student"], student_ref_id="sref-2")
    assert client.post(f"/api/v1/student-life/peer-up/{aid}/join", json={"mode": "trial"}).json()["seats_left"] == 0
    _as(db, "u-3", uni.id, ["student"], student_ref_id="sref-3")
    r = client.post(f"/api/v1/student-life/peer-up/{aid}/join", json={"mode": "trial"})
    assert r.status_code == 409  # ظرفیت پر
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.post(f"/api/v1/student-life/peer-up/{aid}/join", json={"mode": "committed"})
    assert r.status_code == 409  # عضویت تکراری


def test_peer_safe_exit_and_host_close(client, db, uni):
    _as(db, "u-h", uni.id, ["student"], student_ref_id="sref-h")
    aid = client.post("/api/v1/student-life/peer-up", json={
        "title_fa": "بازی فکری", "activity_kind": "games", "time_label_fa": "پنج‌شنبه ۱۸:۰۰",
        "location_fa": "کافه دانشجویی", "capacity": 4, "trial_ok": True, "interest_tags": []}).json()["id"]
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    assert client.post(f"/api/v1/student-life/peer-up/{aid}/join", json={"mode": "trial"}).status_code == 200
    assert client.post(f"/api/v1/student-life/peer-up/{aid}/leave").json()["state"] == "left"
    p = _as(db, "u-h", uni.id, ["student"], student_ref_id="sref-h")
    assert client.post(f"/api/v1/student-life/peer-up/{aid}/join", json={"mode": "trial"}).status_code == 200
    client.post(f"/api/v1/student-life/peer-up/{aid}/leave")  # میزبان خارج شد
    a = db.get(PeerActivity, aid)
    assert a.state == "closed"


def test_peer_report_confidential_and_resolve(client, db, uni):
    _as(db, "u-h", uni.id, ["student"], student_ref_id="sref-h")
    aid = client.post("/api/v1/student-life/peer-up", json={
        "title_fa": "جمع آزمون گزارش", "activity_kind": "other", "time_label_fa": "دوشنبه",
        "location_fa": "حیاط", "capacity": 4, "trial_ok": True, "interest_tags": []}).json()["id"]
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    client.post(f"/api/v1/student-life/peer-up/{aid}/join", json={"mode": "trial"})
    r = client.post(f"/api/v1/student-life/peer-up/{aid}/report", json={"reason_fa": "رفتار نامناسب"})
    assert r.status_code == 200 and "محرمانه" in r.json()["note_fa"]
    _as(db, "u-2", uni.id, ["student"], student_ref_id="sref-2")
    assert client.get("/api/v1/student-life/peer-reports").status_code == 403  # فقط مدیر
    _as(db, "u-mgr", uni.id, ["club_manager"])
    rid = client.get("/api/v1/student-life/peer-reports").json()["items"][0]["id"]
    r = client.post(f"/api/v1/student-life/peer-reports/{rid}/resolve",
                    json={"resolution_note_fa": "بررسی شد", "hide_activity": True})
    assert r.json()["state"] == "resolved"
    assert db.get(PeerActivity, aid).state == "hidden"


def test_peer_host_max_three_open(client, db, uni):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    for i in range(3):
        assert client.post("/api/v1/student-life/peer-up", json={
            "title_fa": f"جمع {i}", "activity_kind": "other", "time_label_fa": "دوشنبه",
            "location_fa": "سالن", "capacity": 4, "trial_ok": True, "interest_tags": []}).status_code == 200
    assert client.post("/api/v1/student-life/peer-up", json={
        "title_fa": "جمع چهارم", "activity_kind": "other", "time_label_fa": "دوشنبه",
        "location_fa": "سالن", "capacity": 4, "trial_ok": True, "interest_tags": []}).status_code == 422


# ---------------- همین هفته در دانشگاه ----------------

def test_opportunity_register_seats_and_duplicate(client, db, uni, opp):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.post(f"/api/v1/student-life/week/{opp.id}/register")
    assert r.json()["state"] == "registered" and r.json()["seats_left"] == 1
    r = client.post(f"/api/v1/student-life/week/{opp.id}/register")
    assert r.status_code == 409


def test_opportunity_waitlist_promotes_in_order(client, db, uni, opp):
    for i, uid_ in enumerate(("u-1", "u-2", "u-3")):
        _as(db, uid_, uni.id, ["student"], student_ref_id=f"sref-{i + 1}")
        r = client.post(f"/api/v1/student-life/week/{opp.id}/register").json()
        if i < 2:
            assert r["state"] == "registered"
        else:
            assert r["state"] == "waitlisted"  # ظرفیت ۲ پر شد → صف، نه رد
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.post(f"/api/v1/student-life/week/{opp.id}/cancel").json()
    assert r["promoted_next"] is True
    _as(db, "u-3", uni.id, ["student"], student_ref_id="sref-3")
    mine = client.get("/api/v1/student-life/week/mine").json()["items"]
    assert mine and mine[0]["my_state"] == "registered"  # سرِ صف ارتقا یافت


def test_opportunity_filters(client, db, uni):
    now = utcnow()
    db.add_all([
        Opportunity(university_id=uni.id, title_fa="کارگاه پولی", what_fa="", location_fa="ا۱",
                    starts_at=now + timedelta(days=1), duration_minutes=120, cost_label_fa="۵۰ هزار تومان",
                    is_free=False, prereq_fa="هیچ", solo_friendly=True, capacity=10, kind="workshop",
                    state="published", created_at=now),
        Opportunity(university_id=uni.id, title_fa="گفت‌وگوی کوتاه بین دو کلاس", what_fa="", location_fa="ا۲",
                    starts_at=now + timedelta(hours=2), duration_minutes=45, cost_label_fa="رایگان",
                    is_free=True, prereq_fa="هیچ", solo_friendly=True, capacity=10, kind="talk",
                    state="published", created_at=now),
        Opportunity(university_id=uni.id, title_fa="کار گروهی طولانی", what_fa="", location_fa="ا۳",
                    starts_at=now + timedelta(days=1), duration_minutes=240, cost_label_fa="رایگان",
                    is_free=True, prereq_fa="هیچ", solo_friendly=False, capacity=10, kind="other",
                    state="published", created_at=now),
    ])
    db.flush()
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    titles = lambda **q: [i["title_fa"] for i in client.get("/api/v1/student-life/week", params=q).json()["items"]]
    assert len(titles()) == 3
    assert titles(free=True) == ["گفت‌وگوی کوتاه بین دو کلاس", "کار گروهی طولانی"]
    assert titles(short=True) == ["گفت‌وگوی کوتاه بین دو کلاس"]
    assert titles(solo=True, short=True, free=True) == ["گفت‌وگوی کوتاه بین دو کلاس"]


# ---------------- بستهٔ ساخت نمونه‌کار ----------------

def test_bundle_enroll_steps_output_verify(client, db, uni, bundle):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.post(f"/api/v1/student-life/bundles/{bundle.id}/enroll", json={"use_newcomer_seat": False})
    assert r.json() == {"state": "active", "is_newcomer_seat": False}
    r = client.post(f"/api/v1/student-life/bundles/{bundle.id}/steps", json={"step_index": 0})
    assert r.json()["steps_done"] == [0]
    r = client.post(f"/api/v1/student-life/bundles/{bundle.id}/steps", json={"step_index": 0})
    assert r.json()["steps_done"] == []  # سوییچ رفت‌وبرگشت
    client.post(f"/api/v1/student-life/bundles/{bundle.id}/steps", json={"step_index": 0})
    r = client.post(f"/api/v1/student-life/bundles/{bundle.id}/output", json={"output_url": "https://x.example/p1"})
    assert r.status_code == 200
    _as(db, "u-mgr", uni.id, ["club_manager"])
    eid = db.query(BundleEnrollment).one().id
    r = client.post(f"/api/v1/student-life/bundle-enrollments/{eid}/verify")
    assert r.json()["state"] == "completed" and r.json()["output_verified"] is True


def test_bundle_newcomer_seat_threshold(client, db, uni, bundle):
    # دانشجوی تازه‌وارد (پیشرفت ۱۰) صندلی می‌گیرد؛ دانشجوی پیشرفته (۱۲۰) رد می‌شود
    s1 = make_sref(db, uni, "new-1", "new1@test")
    s2 = make_sref(db, uni, "senior-1", "senior1@test")
    db.add(PointAccount(university_id=uni.id, kind="student", student_ref_id=s1, cumulative_progress=10.0))
    db.add(PointAccount(university_id=uni.id, kind="student", student_ref_id=s2, cumulative_progress=120.0))
    db.flush()
    _as(db, "u-2", uni.id, ["student"], student_ref_id=s2)
    r = client.post(f"/api/v1/student-life/bundles/{bundle.id}/enroll", json={"use_newcomer_seat": True})
    assert r.status_code == 403
    _as(db, "u-1", uni.id, ["student"], student_ref_id=s1)
    r = client.post(f"/api/v1/student-life/bundles/{bundle.id}/enroll", json={"use_newcomer_seat": True})
    assert r.json()["is_newcomer_seat"] is True
    _as(db, "u-3", uni.id, ["student"], student_ref_id="sref-3")
    r = client.post(f"/api/v1/student-life/bundles/{bundle.id}/enroll", json={"use_newcomer_seat": True})
    assert r.status_code == 409  # صندلی تازه‌وارد فقط ۱ بود و گرفته شد


def test_bundle_no_points_involved(client, db, uni, bundle):
    """ارزش فوری بدون امتیاز: ثبت‌نام در بسته هیچ تغییری در حساب امتیاز نمی‌دهد."""
    s1 = make_sref(db, uni, "nopts-1", "nopts1@test")
    acc = PointAccount(university_id=uni.id, kind="student", student_ref_id=s1,
                       available=0, cumulative_progress=0)
    db.add(acc)
    db.flush()
    _as(db, "u-1", uni.id, ["student"], student_ref_id=s1)
    client.post(f"/api/v1/student-life/bundles/{bundle.id}/enroll", json={"use_newcomer_seat": False})
    db.expire(acc)
    assert float(acc.available) == 0 and float(acc.cumulative_progress) == 0


# ---------------- صدای دانشجو ----------------

def test_voice_propose_vote_toggle_and_equal_weight(client, db, uni):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    pid = client.post("/api/v1/student-life/voice", json={
        "title_fa": "دورهمی عکاسی", "body_fa": "دوشنبه‌ها ساعت ۵", "support_fa": "فضا + دو همراه",
        "kind": "program"}).json()["id"]
    assert client.post(f"/api/v1/student-life/voice/{pid}/vote").json() == {"voted": True, "vote_count": 1}
    assert client.post(f"/api/v1/student-life/voice/{pid}/vote").json() == {"voted": False, "vote_count": 0}
    # دانشجوی «پُرامتیاز» — رأیش هم فقط یک رأی است
    srich = make_sref(db, uni, "rich-1", "rich@test")
    db.add(PointAccount(university_id=uni.id, kind="student", student_ref_id=srich, cumulative_progress=900.0))
    db.flush()
    _as(db, "u-rich", uni.id, ["student"], student_ref_id=srich)
    assert client.post(f"/api/v1/student-life/voice/{pid}/vote").json()["vote_count"] == 1
    votes = db.query(ProposalVote).all()
    assert len(votes) == 1  # رأی تکراری نبوده


def test_voice_decision_flow_guard(client, db, uni):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    pid = client.post("/api/v1/student-life/voice", json={"title_fa": "پیشنهاد آزمون", "kind": "space"}).json()["id"]
    _as(db, "u-mgr", uni.id, ["club_manager"])
    r = client.post(f"/api/v1/student-life/voice/{pid}/decision", json={"state": "accepted"})
    assert r.status_code == 422  # received → accepted مجاز نیست
    assert client.post(f"/api/v1/student-life/voice/{pid}/decision", json={"state": "in_review"}).json()["state"] == "in_review"
    assert client.post(f"/api/v1/student-life/voice/{pid}/decision", json={"state": "accepted"}).json()["state"] == "accepted"
    assert client.post(f"/api/v1/student-life/voice/{pid}/decision", json={"state": "executed"}).json()["state"] == "executed"
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    body = client.get("/api/v1/student-life/voice").json()["items"][0]
    assert body["state"] == "executed" and body["vote_count"] == 0 and body["my_vote"] is False


# ---------------- خانهٔ نو ----------------

def test_home_feed_shape(client, db, uni, opp, bundle):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.get("/api/v1/student-life/home")
    assert r.status_code == 200
    body = r.json()
    assert len(body["suggestions"]["opportunities"]) == 1
    assert body["suggestions"]["bundles"][0]["id"] == bundle.id
    assert body["in_progress"]["peer"] == [] and body["in_progress"]["bundles"] == []
