"""تجربهٔ باشگاه v1.3: شروع فوری ۱۵ دقیقه‌ای، دعوت دوست (مأموریت مشترک، نه جذب)، فضای دستاوردها.

اصول آزمون‌شده:
  - مسیرهای انتخابی (persona) فقط برچسب ملموس سه مسیر مصوب هستند؛ هیچ امتیاز مستقیمی از onboarding نمی‌آید.
  - نشان «اولین قدم» فقط یک‌بار صادر می‌شود (idempotent) و فقط وقتی تعریف نشان موجود باشد.
  - دعوت بدون عضویتِ دعوت‌کننده ممکن نیست؛ هر کد یک‌بار مصرف است؛ امتیاز جذب وجود ندارد.
  - فضای دستاوردها فقط روایت‌های منتشرشده با رضایت را نشان می‌دهد و هیچ رتبه‌بندی ندارد.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.core.rbac import get_principal, make_principal_for_tests
from app.main import app
from app.modules.achievements_tiers.models import BadgeAward, BadgeDefinition
from app.modules.club_experience.models import MissionInvite, OnboardingProfile, ShowcaseStory
from app.modules.missions_groups.models import Mission, MissionParticipation


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


@pytest.fixture
def kickoff_mission(db, uni):
    m = Mission(university_id=uni.id, title_fa="رویداد آغازین (آزمون)", description_fa="شروع فوری",
                goal_type="skill", activities_json="[]", mission_kind="kickoff",
                output_fa="نشان اولین قدم", duration_label_fa="۳۰ دقیقه", team_size_hint="فردی",
                starts_at=__import__("datetime").datetime(2026, 1, 1),
                ends_at=__import__("datetime").datetime(2027, 1, 1))
    db.add(m)
    db.flush()
    return m


@pytest.fixture
def first_step_badge(db, uni):
    b = BadgeDefinition(university_id=uni.id, title_fa="اولین قدم", svg_id="badge-learning", path="learning",
                        criteria_json='{"onboarding": "first_step"}', is_auto=False,
                        story_fa="اولین مأموریت خودت را شروع کرده‌ای.")
    db.add(b)
    db.flush()
    return b


def test_onboarding_state_suggests_kickoff(client, db, uni, kickoff_mission):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.get("/api/v1/club-experience/onboarding")
    assert r.status_code == 200
    body = r.json()
    assert body["completed"] is False
    assert body["first_mission"]["id"] == kickoff_mission.id
    assert any(p["key"] == "creator" for p in body["personas"])
    assert any(o["key"] == "build" for o in body["interest_options"])


def test_onboarding_save_awards_first_step_badge_once(client, db, uni, kickoff_mission, first_step_badge):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.post("/api/v1/club-experience/onboarding", json={"persona": "creator", "interests": ["build", "tech", "bogus"]})
    assert r.status_code == 200
    body = r.json()
    assert body["completed"] is True and body["first_badge_awarded"] is True
    assert body["mapped_path"] == "skill"
    assert body["interests"] == ["build", "tech"]  # ورودی نامعتبر فیلتر شد

    awards = db.query(BadgeAward).filter(BadgeAward.badge_id == first_step_badge.id).all()
    assert len(awards) == 1  # یک‌بار، بی‌تکرار

    r2 = client.post("/api/v1/club-experience/onboarding", json={"persona": "explorer", "interests": ["event"]})
    assert r2.status_code == 200
    db.expire_all()
    assert db.query(BadgeAward).filter(BadgeAward.badge_id == first_step_badge.id).count() == 1
    assert db.query(OnboardingProfile).count() == 1  # upsert، نه ردیف دوم


def test_onboarding_gives_no_points(db, client, uni, kickoff_mission, first_step_badge):
    """هیچ سند امتیازی از onboarding ساخته نمی‌شود — امتیاز فقط از سیاست‌های مصوب."""
    from app.modules.points_ledger.models import LedgerTransaction

    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    client.post("/api/v1/club-experience/onboarding", json={"persona": "helper", "interests": ["help"]})
    assert db.query(LedgerTransaction).count() == 0


def test_invite_requires_participation_and_is_single_use(client, db, uni):
    """دعوت فقط برای عضو مأموریت؛ کد یک‌بار مصرف؛ امتیازی برای تعداد دعوت وجود ندارد."""
    m = Mission(university_id=uni.id, title_fa="مأموریت واقعی هفته (آزمون)", goal_type="collaboration",
                activities_json="[]", mission_kind="guide", is_group=True,
                starts_at=__import__("datetime").datetime(2026, 1, 1), ends_at=__import__("datetime").datetime(2027, 1, 1))
    db.add(m)
    db.flush()
    inviter = _as(db, "u-inv", uni.id, ["student"], student_ref_id="sref-inv")

    r0 = client.post("/api/v1/club-experience/invites", json={"mission_id": m.id, "invitee_contact": "a@b.ir"})
    assert r0.status_code == 409  # بدون عضویت، دعوت ممنوع

    db.add(MissionParticipation(university_id=uni.id, mission_id=m.id, student_ref_id="sref-inv",
                                state="active", joined_at=__import__("datetime").datetime(2026, 1, 1)))
    db.flush()
    r1 = client.post("/api/v1/club-experience/invites", json={"mission_id": m.id, "invitee_contact": "a@b.ir"})
    assert r1.status_code == 200
    code = r1.json()["invite_code"]
    assert "مشارکت مشترک" in r1.json()["note_fa"]

    # دعوت‌شده
    _as(db, "u-guest", uni.id, ["student"], student_ref_id="sref-guest")
    r2 = client.post(f"/api/v1/club-experience/invites/{code}/accept")
    assert r2.status_code == 200
    assert r2.json()["state"] == "joined"
    assert db.query(MissionParticipation).filter(
        MissionParticipation.mission_id == m.id, MissionParticipation.student_ref_id == "sref-guest").count() == 1

    # دوباره استفاده نمی‌شود
    r3 = client.post(f"/api/v1/club-experience/invites/{code}/accept")
    assert r3.status_code == 409

    # دعوت‌کننده نمی‌تواند دعوت خودش را بپذیرد
    inviter2 = _as(db, "u-inv", uni.id, ["student"], student_ref_id="sref-inv")
    r4 = client.post("/api/v1/club-experience/invites", json={"mission_id": m.id, "invitee_contact": ""})
    code2 = r4.json()["invite_code"]
    r5 = client.post(f"/api/v1/club-experience/invites/{code2}/accept")
    assert r5.status_code == 409

    # دعوت هیچ امتیازی نساخته باشد (بدون سیاست، بدون تراکنش)
    from app.modules.points_ledger.models import LedgerTransaction
    assert db.query(LedgerTransaction).count() == 0


def test_invite_requires_student_profile(client, db, uni):
    m = Mission(university_id=uni.id, title_fa="م", goal_type="skill", activities_json="[]",
                starts_at=__import__("datetime").datetime(2026, 1, 1), ends_at=__import__("datetime").datetime(2027, 1, 1))
    db.add(m)
    db.flush()
    _as(db, "u-mgr", uni.id, ["club_manager"])  # بدون student_ref
    r = client.post("/api/v1/club-experience/invites", json={"mission_id": m.id, "invitee_contact": ""})
    assert r.status_code == 403


def test_showcase_consent_gate_and_no_ranking(client, db, uni):
    """روایت بدون رضایت نمایش داده نمی‌شود؛ خروجی هیچ فیلد رتبه/امتیازی ندارد."""
    _as(db, "u-mgr", uni.id, ["club_manager"])
    r = client.post("/api/v1/club-experience/showcase", json={
        "title_fa": "این تیم چه ساخت؟", "body_fa": "یک ابزار کوچک برای نوبت‌دهی آزمایشگاه.",
        "kind": "build", "subject_label_fa": "گروه سازندگان", "has_consent": False})
    assert r.status_code == 200
    no_consent_id = r.json()["id"]
    r2 = client.post("/api/v1/club-experience/showcase", json={
        "title_fa": "یک عضو چه تجربه‌ای داشت؟", "body_fa": "اولین نمونه‌کار وب با «یک عصر، یک مهارت».",
        "kind": "skill", "subject_label_fa": "سارا", "has_consent": True})
    assert r2.status_code == 200

    _as(db, "u-stu", uni.id, ["student"], student_ref_id="sref-x")
    r3 = client.get("/api/v1/club-experience/showcase")
    assert r3.status_code == 200
    items = r3.json()["items"]
    ids = {i["id"] for i in items}
    assert no_consent_id not in ids  # بدون رضایت → نمایش داده نمی‌شود
    assert len(items) == 1
    forbidden_keys = {"rank", "points", "score", "position", "leaderboard"}
    assert not forbidden_keys & set(items[0].keys())  # هیچ رتبه‌بندی

    # دانشجو نمی‌تواند روایت بسازد
    r4 = client.post("/api/v1/club-experience/showcase", json={"title_fa": "x", "kind": "build"})
    assert r4.status_code == 403


def test_missions_list_exposes_experience_fields(client, db, uni, kickoff_mission):
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.get("/api/v1/missions")
    assert r.status_code == 200
    item = next(i for i in r.json()["items"] if i["id"] == kickoff_mission.id)
    assert item["mission_kind"] == "kickoff"
    assert item["kind_label_fa"] == "رویداد آغازین"
    assert item["output_fa"] == "نشان اولین قدم"
    assert item["duration_label_fa"] == "۳۰ دقیقه"


def test_groups_list_exposes_interest_fields(client, db, uni):
    from app.modules.missions_groups.models import LearningGroup
    db.add(LearningGroup(university_id=uni.id, title_fa="ساخت یک ابزار ساده", capacity=4,
                         interest_tag="build", goal_fa="یک ابزار کوچک برای کلاس",
                         expected_output_fa="یک ابزار قابل‌اجرا", duration_label_fa="یک هفته، سه نفر"))
    db.flush()
    _as(db, "u-1", uni.id, ["student"], student_ref_id="sref-1")
    r = client.get("/api/v1/groups")
    assert r.status_code == 200
    g = r.json()["items"][0]
    assert g["interest_tag"] == "build" and g["duration_label_fa"] == "یک هفته، سه نفر"
    assert g["expected_output_fa"] == "یک ابزار قابل‌اجرا"
    assert g["my_state"] is None and g["member_count"] == 0
