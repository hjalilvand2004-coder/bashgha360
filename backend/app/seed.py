"""Seed دادهٔ نمونهٔ فارسی و برچسب‌خورده (SEED-01..12).

هرگز در Production خودکار بارگذاری نمی‌شود:
    python -m app.seed            # فقط environment=development/test
    FORCE_SEED=1 python -m app.seed  # انصراف آگاهانه
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from .core.config import get_settings
from .core.db import TestingSession, utcnow
from .core.security import hash_password
from .modules.achievements_tiers import service as ach
from .modules.achievements_tiers.models import BadgeDefinition, TierDefinition
from .modules.event_ingestion.models import EducationalEvent, EventInbox, IntegrationSource
from .modules.identity_access.models import (StudentReference, User, UserRoleScope, University)
from .modules.integrity_reviews import service as integrity
from .modules.integrity_reviews.models import ReviewCase
from .modules.missions_groups.models import (GroupContribution, GroupMember, LearningGroup, Mission,
                                             MissionParticipation)
from .modules.memberships_consents.models import ApprovalScope, Membership
from .modules.memberships_consents import service as mem
from .modules.memberships_consents.models import TermsVersion
from .modules.notifications.models import NotificationPreference
from .modules.points_ledger import service as ledger
from .modules.policy_engine.models import Policy, PolicyVersion
from .modules.rewards_fulfillment import service as rw
from .modules.rewards_fulfillment.models import Reward, RewardProvider
from .modules.student_goals.models import AcademicPeriod, StudentGoal
from .modules.appeals import service as appeals
from .modules.club_experience.models import OnboardingProfile, ShowcaseStory

LABEL = "نمونه — محیط آزمایشی"


def main() -> None:
    s = get_settings()
    if s.environment == "production" and os.environ.get("FORCE_SEED") != "1":
        print("Seed در Production مجاز نیست (SEED-12). در صورت نیاز صریح: FORCE_SEED=1")
        sys.exit(1)
    db = TestingSession()
    try:
        _seed(db)
        db.commit()
        print("Seed کامل شد — داده‌ها با برچسب «نمونه — محیط آزمایشی» ثبت شدند.")
    finally:
        db.close()


def _seed(db) -> None:
    now = utcnow()

    # ---- ۱) دو دانشگاه برای آزمون جداسازی (SEED-01) ----
    u1 = db.execute(select(University).where(University.code == "UNI-A")).scalar_one_or_none()
    if u1 is None:
        u1 = University(id="11111111-1111-4111-8111-111111111111", code="UNI-A",
                        name_fa="دانشگاه نمونه الف (آزمایشی)", timezone="Asia/Tehran")
        db.add(u1)
    u2 = db.execute(select(University).where(University.code == "UNI-B")).scalar_one_or_none()
    if u2 is None:
        u2 = University(id="22222222-2222-4222-8222-222222222222", code="UNI-B",
                        name_fa="دانشگاه نمونه ب (آزمایشی)", timezone="Asia/Tehran")
        db.add(u2)
    db.flush()

    ledger.seed_pool(db, u1.id, Decimal("500000.00"))
    ledger.seed_pool(db, u2.id, Decimal("500000.00"))

    # ---- ۲) کاربران همهٔ نقش‌های مهم (SEED-02) ----
    users_spec = [
        ("st1@u1.demo", "سارا دانشجو", "student", u1.id, "12345678"),
        ("st2@u1.demo", "رضا دانشجو", "student", u1.id, "12345678"),
        ("st3@u2.demo", "مینا دانشجو", "student", u2.id, "12345678"),
        ("prof1@u1.demo", "دکتر احمدی", "professor", u1.id, "12345678"),
        ("adv1@u1.demo", "مشاور کاظمی", "advisor", u1.id, "12345678"),
        ("mgr1@u1.demo", "مدیر باشگاه", "club_manager", u1.id, "12345678"),
        ("pol1@u1.demo", "مسئول سیاست", "policy_officer", u1.id, "12345678"),
        ("pol2@u1.demo", "تأییدکنندهٔ دوم سیاست", "policy_officer", u1.id, "12345678"),
        ("prov1@u1.demo", "ارائه‌دهندهٔ کتاب‌فروشی", "reward_provider", u1.id, "12345678"),
        ("rev1@u1.demo", "کارشناس سلامت آموزشی", "edtech_specialist", u1.id, "12345678"),
        ("ref1@u1.demo", "مرجع مستقل اعتراض", "appeal_referee", u1.id, "12345678"),
        ("tech1@u1.demo", "مدیر فنی", "tech_admin", u1.id, "12345678"),
        ("aud1@u1.demo", "حسابرس حریم خصوصی", "auditor", u1.id, "12345678"),
    ]
    users: dict[str, User] = {}
    for username, name, role, uni, pwd in users_spec:
        u = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if u is None:
            u = User(username=username, display_name=name, password_hash=hash_password(pwd),
                     identity_mode="local", is_demo=True)
            db.add(u)
            db.flush()
        if not db.execute(select(UserRoleScope).where(UserRoleScope.user_id == u.id,
                                                      UserRoleScope.role_code == role)).scalar_one_or_none():
            db.add(UserRoleScope(user_id=u.id, role_code=role, university_id=uni, granted_by="seed", is_emergency=False))
        users[username] = u
    db.flush()

    # ---- ۳) دانشجویان با وضعیت‌های متفاوت (SEED-03) ----
    def student(username: str, ext_id: str, program: str, uni):
        sref = db.execute(select(StudentReference).where(StudentReference.university_id == uni.id, StudentReference.external_student_id == ext_id)).scalar_one_or_none()
        if sref is None:
            sref = StudentReference(university_id=uni.id, user_id=users[username].id, external_student_id=ext_id,
                      program=program, entry_year=1402, source="s360_sim")
            db.add(sref)
            db.flush()
        return sref

    sara = student("st1@u1.demo", "stu-40101", "مهندسی کامپیوتر", u1)
    reza = student("st2@u1.demo", "stu-40102", "مهندسی برق", u1)
    mina = student("st3@u2.demo", "stu-90201", "مدیریت", u2)

    terms = db.execute(select(TermsVersion).where(TermsVersion.university_id == u1.id, TermsVersion.is_current.is_(True))).scalar_one_or_none()
    if terms is None:
        terms = TermsVersion(id="aaaa1111-0000-4000-8000-000000000001", university_id=u1.id, version_no=1,
                             title_fa="شرایط عضویت باشگاه (نمونهٔ آزمایشی)",
                             content_fa="مشارکت در باشگاه داوطلبانه است؛ امتیاز باشگاه با نمره و وضعیت تحصیلی متفاوت است. "
                                        "این متن نمونهٔ آزمایشی است و مصوبهٔ دانشگاه نیست.",
                             data_policy_fa="داده‌های رویداد آموزشی حداقلی نگهداری می‌شود؛ نمایش عمومی نشان فقط با رضایت شما.",
                             is_current=True, published_at=now)
        db.add(terms)
        db.flush()

    for sref, goal in ((sara, "skill"), (reza, "exam_prep")):
        m = db.execute(select(Membership).where(Membership.student_ref_id == sref.id)).scalar_one_or_none()
        if m is None:
            m = mem.join(db, university_id=u1.id, student_ref=sref, terms_version_id=terms.id,
                         consents={"personalization": True, "public_badge": sref is sara, "notifications": True})
        # مینا عمداً عضو نمی‌شود (PRN-04: خدمات پایه بدون عضویت هم کار کند)

    periods = db.execute(select(AcademicPeriod).where(AcademicPeriod.university_id == u1.id)).scalars().all()
    if not periods:
        p1 = AcademicPeriod(id="bbbb1111-0000-4000-8000-000000000001", university_id=u1.id,
                            title_fa="نیم‌سال اول ۱۴۰۵-۱۴۰۴ (نمونه)",
                            starts_at=datetime(2026, 9, 1).date(), ends_at=datetime(2027, 1, 31).date(), is_current=True)
        db.add(p1)
        db.flush()
    period_id = db.execute(select(AcademicPeriod).where(AcademicPeriod.university_id == u1.id)).scalars().first().id

    if not db.execute(select(StudentGoal).where(StudentGoal.student_ref_id == sara.id)).scalar_one_or_none():
        db.add(StudentGoal(university_id=u1.id, student_ref_id=sara.id, goal_type="skill",
                           title_fa="تقویت مهارت برنامه‌نویسی وب", status="active",
                           academic_period_id=period_id, declared_at=now))
        db.add(StudentGoal(university_id=u1.id, student_ref_id=reza.id, goal_type="exam_prep",
                           title_fa="آمادگی آزمون میان‌ترم مدار", status="active",
                           academic_period_id=period_id, declared_at=now))
    db.add(NotificationPreference(university_id=u1.id, user_id=sara.user_id,
                                  channels_json='{"in_app": true, "email": false, "sms": false}',
                                  quiet_start="22:00", quiet_end="07:00", daily_cap=5)) if not db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == sara.user_id)).scalar_one_or_none() else None

    # ---- ۴) منبع رویداد آزمایشی برچسب‌دار (SEED-04) ----
    src = db.execute(select(IntegrationSource).where(IntegrationSource.university_id == u1.id,
                                                     IntegrationSource.code == "lms-simulator")).scalar_one_or_none()
    if src is None:
        src = IntegrationSource(university_id=u1.id, code="lms-simulator",
                                name_fa="شبیه‌ساز LMS (آزمایشی)",
                                auth_key_hash="sim-key-u1", hmac_secret_ref=None, rate_limit_per_min=600,
                                is_active=True, is_simulator=True, schema_version="1.0")
        db.add(src)
    src2 = db.execute(select(IntegrationSource).where(IntegrationSource.university_id == u2.id,
                                                      IntegrationSource.code == "lms-simulator")).scalar_one_or_none()
    if src2 is None:
        db.add(IntegrationSource(university_id=u2.id, code="lms-simulator", name_fa="شبیه‌ساز LMS (آزمایشی)",
                                 auth_key_hash="sim-key-u2", is_active=True, is_simulator=True))
    self_src = db.execute(select(IntegrationSource).where(IntegrationSource.university_id == u1.id,
                                                          IntegrationSource.code == "self-report")).scalar_one_or_none()
    if self_src is None:
        db.add(IntegrationSource(university_id=u1.id, code="self-report", name_fa="خوداظهاری دانشجو",
                                 auth_key_hash="self-report-u1", is_active=True, is_simulator=False))
    db.flush()

    # ---- ۵) رویدادهای معتبر/تکراری/دیررس/اصلاحی/نامعتبر (SEED-05) ----
    def mk_event(eid: str, sref, etype: str, occ: datetime, payload: dict, status="verified", rev=1, ref_corr=None):
        e = EducationalEvent(university_id=u1.id, event_id=eid, schema_version="1.0", source_id=src.id,
                             student_reference=sref.external_student_id, event_type=etype,
                             occurred_at=occ, received_at=occ + timedelta(minutes=5),
                             activity_reference=f"course/CS101/session/{eid[-2:]}" if "attendance" in etype else "activity/" + eid[-4:],
                             verification_status=status, correlation_id=f"corr-{eid[-6:]}",
                             revision=rev, reference_to_corrected_event=ref_corr,
                             payload_json=json.dumps(payload, ensure_ascii=False))
        try:
            with db.begin_nested():
                db.add(e)
                db.flush()
        except Exception:
            # نمونهٔ ارسال مجدد (تکراری) — کلید یکتا مانع اثر دوم می‌شود
            return db.execute(select(EducationalEvent).where(EducationalEvent.university_id == u1.id,
                                                             EducationalEvent.event_id == eid)).scalar_one()
        db.add(EventInbox(university_id=u1.id, message_id=f"lms-simulator:{eid}:r{rev}", event_id=e.id, state="received"))
        return e

    t0 = now - timedelta(days=3)
    for i in range(6):
        mk_event(f"ev-att-{i:03d}", sara, "meaningful_attendance_verified", t0 + timedelta(hours=i),
                 {"duration_minutes": 60 + i * 5, "quality": "normal" if i % 2 else "high", "course_code": "CS101"})
    mk_event("ev-att-000", sara, "meaningful_attendance_verified", t0,
             {"duration_minutes": 60})  # duplicate send (TST-01 source data)
    mk_event("ev-study-001", reza, "study_completion_verified", now - timedelta(days=1),
             {"duration_minutes": 90, "quality": "high"})
    mk_event("ev-skill-001", sara, "skill_progress_verified", now - timedelta(days=2),
             {"skill_code": "web-dev", "progress_level": 2})
    mk_event("ev-peer-001", sara, "peer_support_verified", now - timedelta(days=1),
             {"peer_ref": "stu-40102", "duration_minutes": 45})
    old = mk_event("ev-late-001", sara, "meaningful_attendance_verified", now - timedelta(days=30),
                   {"duration_minutes": 50})
    old_correct = mk_event("ev-late-001-c1", sara, "meaningful_attendance_verified", now - timedelta(days=30),
                           {"duration_minutes": 95, "quality": "high"}, rev=2, ref_corr="ev-late-001")
    if not db.execute(select(EventInbox).where(EventInbox.message_id == "lms-simulator:ev-bad-001:q")).scalar_one_or_none():
        db.add(EventInbox(university_id=u1.id, message_id="lms-simulator:ev-bad-001:q", event_id=None,
                          state="quarantined", quarantined_reason="payload نامعتبر (نمونهٔ قرنطینه)"))

    # ---- ۶) سیاست دارای سقف و بازده کاهشی (SEED-06) ----
    pol = db.execute(select(Policy).where(Policy.university_id == u1.id, Policy.code == "ATT-BASE")).scalar_one_or_none()
    if pol is None:
        pol = Policy(university_id=u1.id, code="ATT-BASE", title_fa="امتیاز حضور معنادار تأییدشده (نمونه)",
                     exclusive_group="attendance", priority=10)
        db.add(pol)
        db.flush()
    ver = db.execute(select(PolicyVersion).where(PolicyVersion.policy_id == pol.id)).scalar_one_or_none()
    if ver is None:
        dsl = {
            "rule_id": "attendance_base_v1", "event_type": "meaningful_attendance_verified", "path": "learning",
            "conditions": {"all": [{"field": "payload.duration_minutes", "op": ">=", "value": 45}]},
            "base_points": "10.00",
            "quality_multiplier": {"field": "payload.quality", "map": {"high": "1.20", "normal": "1.00"},
                                   "default": "1.00"},
            "progress_multiplier": {"default": "1.00"},
            "repeat_policy": {"window_days": 7, "diminishing": ["1.00", "1.00", "0.50", "0.25"], "beyond": "0"},
            "caps": {"per_day": "30.00", "per_period": "300.00"},
            "exclusive_group": "attendance",
            "late_policy": {"max_late_hours": 72, "factor": "1.00"},
            "human_reason_template": "حضور معنادار تأییدشده در {activity_reference}",
        }
        ver = PolicyVersion(id="cccc1111-0000-4000-8000-000000000001", university_id=u1.id, policy_id=pol.id,
                            version_no=1, status="published",
                            dsl_json=json.dumps(dsl, ensure_ascii=False),
                            effective_from=now - timedelta(days=10), late_window_hours=72,
                            approved_by=users["pol2@u1.demo"].id, approved_at=now, approval_ref="SEED-DEMO-001",
                            change_note_fa="نسخهٔ نمونهٔ آزمایشی — اعداد مصوبهٔ دانشگاه نیستند.")
        db.add(ver)
        db.flush()

    # ---- ۶-ب) سیاست مطالعه (نمونهٔ دوم، منتشرشده) ----
    pol2 = db.execute(select(Policy).where(Policy.university_id == u1.id, Policy.code == "STUDY-BASE")).scalar_one_or_none()
    if pol2 is None:
        pol2 = Policy(university_id=u1.id, code="STUDY-BASE", title_fa="امتیاز تکمیل مطالعهٔ تأییدشده (نمونه)",
                      exclusive_group="study", priority=10)
        db.add(pol2)
        db.flush()
    if not db.execute(select(PolicyVersion).where(PolicyVersion.policy_id == pol2.id)).scalar_one_or_none():
        dsl2 = {
            "rule_id": "study_base_v1", "event_type": "study_completion_verified", "path": "learning",
            "conditions": {"all": [{"field": "payload.duration_minutes", "op": ">=", "value": 30}]},
            "base_points": "8.00",
            "quality_multiplier": {"field": "payload.quality", "map": {"high": "1.25", "normal": "1.00"}, "default": "1.00"},
            "progress_multiplier": {"default": "1.00"},
            "repeat_policy": {"window_days": 7, "diminishing": ["1.00", "0.75"], "beyond": "0.50"},
            "caps": {"per_day": "24.00", "per_period": "200.00"},
            "human_reason_template": "تکمیل مطالعهٔ تأییدشده در {activity_reference}",
        }
        db.add(PolicyVersion(university_id=u1.id, policy_id=pol2.id, version_no=1, status="published",
                             dsl_json=json.dumps(dsl2, ensure_ascii=False),
                             effective_from=now - timedelta(days=10), late_window_hours=72,
                             approved_by=users["pol2@u1.demo"].id, approved_at=now, approval_ref="SEED-DEMO-002",
                             change_note_fa="نسخهٔ نمونهٔ آزمایشی."))
        db.flush()

    # ---- ۷) سطوح و نشان (SEED-07) ----
    tiers_spec = [("learning", 1, "تازه‌کار", "10.00"), ("learning", 2, "پویا", "50.00"),
                  ("learning", 3, "پیشرو", "120.00"), ("skill", 1, "آغازگر مهارت", "20.00"),
                  ("collaboration", 1, "همیار", "15.00")]
    for path, lvl, title, mp in tiers_spec:
        if not db.execute(select(TierDefinition).where(TierDefinition.university_id == u1.id,
                                                       TierDefinition.path == path, TierDefinition.level_no == lvl)).scalar_one_or_none():
            db.add(TierDefinition(university_id=u1.id, path=path, level_no=lvl, title_fa=title, min_progress=Decimal(mp)))
    badges_spec = [
        ("حضور پیوسته (نمونه)", "badge-learning", "learning", {"meaningful_attendance_verified": 3}),
        ("رشد مهارت وب (نمونه)", "badge-skill", "skill", {"skill_progress_verified": 1}),
        ("همیار کلاس (نمونه)", "badge-collab", "collaboration", {"peer_support_verified": 1}),
    ]
    for title, svg, path, criteria in badges_spec:
        if not db.execute(select(BadgeDefinition).where(BadgeDefinition.university_id == u1.id,
                                                        BadgeDefinition.title_fa == title)).scalar_one_or_none():
            db.add(BadgeDefinition(university_id=u1.id, title_fa=title, svg_id=svg, path=path,
                                   criteria_json=json.dumps(criteria), issuer_fa="باشگاه۳۶۰ دانشگاه نمونه الف",
                                   is_auto=True))
    db.flush()

    # ---- ۸) مأموریت فردی و گروهی (SEED-08) ----
    if not db.execute(select(Mission).where(Mission.university_id == u1.id, Mission.title_fa == "مأموریت مطالعهٔ منظم (نمونه)")).scalar_one_or_none():
        db.add(Mission(university_id=u1.id, title_fa="مأموریت مطالعهٔ منظم (نمونه)",
                       description_fa="سه جلسهٔ مطالعهٔ تأییدشده در هفته — خروج بدون تنبیه.",
                       goal_type="exam_prep",
                       activities_json=json.dumps([{"event_type": "study_completion_verified", "min_count": 3}]),
                       starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=14),
                       max_points=Decimal("40.00"), is_group=False))
        db.add(Mission(university_id=u1.id, title_fa="گروه مطالعهٔ مدار (نمونه)",
                       description_fa="مأموریت گروهی با رضایت اعضا و ثبت سهم مشارکت.",
                       goal_type="collaboration",
                       activities_json=json.dumps([{"event_type": "peer_support_verified", "min_count": 2}]),
                       starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=21),
                       max_points=Decimal("60.00"), is_group=True))
    db.flush()
    mission_grp = db.execute(select(Mission).where(Mission.university_id == u1.id, Mission.is_group.is_(True))).scalars().first()
    grp = db.execute(select(LearningGroup).where(LearningGroup.university_id == u1.id)).scalar_one_or_none()
    if grp is None:
        grp = LearningGroup(university_id=u1.id, mission_id=mission_grp.id, title_fa="گروه مطالعهٔ مدار (نمونه)", capacity=6)
        db.add(grp)
        db.flush()
        db.add(GroupMember(university_id=u1.id, group_id=grp.id, student_ref_id=sara.id, consent_at=now))
        db.add(GroupContribution(university_id=u1.id, group_id=grp.id, student_ref_id=sara.id,
                                 activity_key="session-1", share_note_fa="توضیح تمرین ۳ برای گروه",
                                 approved_by=users["prof1@u1.demo"].id))
    db.add(MissionParticipation(university_id=u1.id, mission_id=mission_grp.id, student_ref_id=sara.id,
                                state="active", joined_at=now)) if not db.execute(
        select(MissionParticipation).where(MissionParticipation.mission_id == mission_grp.id,
                                           MissionParticipation.student_ref_id == sara.id)).scalar_one_or_none() else None

    # ---- ۹) پردازش رویدادها → دفترکل متوازن + سطح/نشان (SEED-09) ----
    from .modules.event_ingestion import service as evsvc

    db.commit()
    inboxes = db.execute(select(EventInbox).where(EventInbox.state == "received", EventInbox.event_id.is_not(None))).scalars().all()
    for inbox in inboxes:
        try:
            evsvc.process_inbox_message(db, inbox)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            fresh = db.get(EventInbox, inbox.id)
            if fresh is not None:
                fresh.state, fresh.quarantined_reason = "quarantined", f"seed: {str(exc)[:120]}"
                db.commit()
            print(f"  WARN: inbox {inbox.message_id} quarantined: {str(exc)[:120]}")
    db.flush()
    for sref, uni in ((sara, u1), (reza, u1), (mina, u2)):
        for path in ("learning", "skill", "collaboration"):
            ach.check_tier(db, university_id=uni.id, student_ref_id=sref.id, path=path)
        ach.check_badges(db, university_id=uni.id, student_ref_id=sref.id)
    db.flush()

    # ---- ۱۱) پروندهٔ بررسی و اعتراض پذیرفته‌شده (SEED-11) — قبل از پاداش‌ها تا مانده‌ها بسازد ----
    case = db.execute(select(ReviewCase).where(ReviewCase.university_id == u1.id)).scalar_one_or_none()
    if case is None:
        sig = integrity.create_signal(db, university_id=u1.id, kind="risk_pattern",
                                      rule_code="SEED_SAMPLE_PATTERN", severity="info",
                                      subject_student_ref=reza.id, refs={"note": "نمونهٔ آموزشی"})
        case = integrity.open_case(db, sig, summary_fa="نمونهٔ پروندهٔ بررسی برای آموزش")
    appeal = db.execute(select(appeals.Appeal).where(appeals.Appeal.university_id == u1.id)).scalar_one_or_none()
    if appeal is None:
        a = appeals.submit(db, university_id=u1.id, student_ref_id=reza.id, subject_type="ledger_correction",
                           subject_id=None, ground_fa="نمونهٔ اعتراض: امتیاز جلسهٔ ۲ ثبت نشده است")
        appeals.assign_reviewer(db, a, reviewer_user_id=users["ref1@u1.demo"].id,
                                first_handler_user_id=users["rev1@u1.demo"].id)
        appeals.decide(db, appeal=a, decision="accepted", decision_fa="نمونهٔ پذیرش اعتراض — سند جبرانی ثبت شد",
                       reviewer_user_id=users["ref1@u1.demo"].id, compensation_points=Decimal("5.00"))
    db.commit()

    # ---- ۱۰) پاداش محدود و نامحدود + درخواست‌های سه‌حالته (SEED-10) ----
    prov = db.execute(select(RewardProvider).where(RewardProvider.university_id == u1.id)).scalar_one_or_none()
    if prov is None:
        prov = RewardProvider(university_id=u1.id, name_fa="کتاب‌فروشی فنی (نمونه)",
                              callback_secret_ref="prov-callback-secret", is_active=True)
        db.add(prov)
        db.flush()
    r_limited = db.execute(select(Reward).where(Reward.university_id == u1.id, Reward.title_fa == "کارت هدیهٔ کتاب (نمونه)")).scalar_one_or_none()
    if r_limited is None:
        r_limited = Reward(university_id=u1.id, provider_id=prov.id, type="resource_access",
                           title_fa="کارت هدیهٔ کتاب (نمونه)", description_fa="کارت کتاب‌فروشی — ظرفیت ۲ (نمونه)",
                           cost_points=Decimal("12.00"), capacity_total=2, allocation="first_come",
                           delivery="external", goal_tags="skill,exam_prep",
                           refund_policy_fa="لغو تا پیش از تحویل آزاد است.", state="active")
        db.add(r_limited)
    r_unlimited = db.execute(select(Reward).where(Reward.university_id == u1.id, Reward.title_fa == "دسترسی منبع تکمیلی (نمونه)")).scalar_one_or_none()
    if r_unlimited is None:
        r_unlimited = Reward(university_id=u1.id, type="resource_access",
                             title_fa="دسترسی منبع تکمیلی (نمونه)", description_fa="بستهٔ تمرین اضافی درس مدار",
                             cost_points=Decimal("5.00"), capacity_total=None, allocation="first_come",
                             delivery="in_app", goal_tags="exam_prep", state="active")
        db.add(r_unlimited)
    db.flush()

    from .modules.rewards_fulfillment.models import RewardRequest

    def _request_once(sref, reward, actor="seed"):
        """درخواست پاداش فقط اگر قبلاً برای این (دانشجو، پاداش) ساخته نشده — seed بازپذیر."""
        if db.execute(select(RewardRequest).where(RewardRequest.student_ref_id == sref.id,
                                                  RewardRequest.reward_id == reward.id)).scalars().first():
            return None
        return rw.request_reward(db, university_id=u1.id, student_ref=sref, reward_id=reward.id, actor=actor)

    req1 = _request_once(sara, r_unlimited)
    if req1 is not None:
        rw.approve(db, req1, users["mgr1@u1.demo"].id)
        rw.start_fulfilling(db, req1, users["mgr1@u1.demo"].id)
        rw.deliver_in_app(db, req1, users["mgr1@u1.demo"].id)

    req2 = _request_once(reza, r_limited)
    if req2 is not None:
        rw.cancel(db, req2, actor="seed", reason_fa="نمونهٔ درخواست لغوشده")

    req3 = _request_once(sara, r_limited)
    if req3 is not None:
        rw.approve(db, req3, users["mgr1@u1.demo"].id)
        rw.start_fulfilling(db, req3, users["mgr1@u1.demo"].id)
        rw.mark_failed(db, req3, "نمونهٔ ارائه‌دهنده: شکست تحویل", actor="seed")
    db.commit()

    # ---- ۱۲) تجربهٔ باشگاه v1.3: نشان داستان‌محور، مأموریت ملموس، گروه علاقه‌ای، پاداش تجربه‌ساز ----
    story_badges_spec = [
        ("اولین قدم", "badge-learning", "learning", {"onboarding": "first_step"}, False,
         "یعنی اولین مأموریت خودت را شروع کرده‌ای — مهم‌ترین قدم، همین بود."),
        ("سازنده", "badge-skill", "skill", {"output": "deliverable"}, True,
         "یعنی یک خروجی واقعی (ابزار، محتوا یا نمونه‌کار) تحویل داده‌ای و می‌توانی درباره‌اش حرف بزنی."),
        ("هم‌مسیر", "badge-collab", "collaboration", {"group": "effective_participation"}, True,
         "یعنی در یک کار گروهی سهم مؤثر داشتی؛ کاری که تیم بدون آن همان نبود."),
        ("حل‌گر", "badge-learning", "learning", {"output": "problem_solved"}, True,
         "یعنی به حل یک مسئلهٔ واقعی کمک کرده‌ای — از شناسایی تا پیشنهاد قابل‌ارائه."),
        ("پیوسته", "badge-learning", "learning", {"streak_weeks": 3}, True,
         "یعنی یک مسیر را در چند هفته ادامه دادی؛ استمرار آرام، اما جدی."),
    ]
    for title, svg, path, criteria, is_auto, story in story_badges_spec:
        b = db.execute(select(BadgeDefinition).where(BadgeDefinition.university_id == u1.id,
                                                     BadgeDefinition.title_fa == title)).scalar_one_or_none()
        if b is None:
            db.add(BadgeDefinition(university_id=u1.id, title_fa=title, svg_id=svg, path=path,
                                   criteria_json=json.dumps(criteria), issuer_fa="باشگاه۳۶۰ دانشگاه نمونه الف",
                                   is_auto=is_auto, story_fa=story))
    db.flush()

    exp_missions_spec = [
        ("رویداد آغازین: اولین مأموریت را تجربه کن", "kickoff",
         "در یک نشست کوتاه و تعاملی، یک مأموریت کوچک را امتحان می‌کنی، با چند عضو آشنا می‌شوی و در پایان نشان «اولین قدم» را می‌گیری.",
         "نشان «اولین قدم» + پیشنهاد مسیر شخصی", "یک جلسهٔ ۳۰ دقیقه‌ای", "فردی", "explore,event",
         [{"event_type": "meaningful_attendance_verified", "min_count": 1}], "10.00", False),
        ("چالش ۲۰ دقیقه‌ای: یک مسئلهٔ واقعی دانشگاه را پیدا کن", "micro_challenge",
         "در ۲۰ دقیقه یک مسئلهٔ کوچک اما واقعی از زندگی روزمرهٔ دانشگاه شناسایی کن و یک راه‌حل کوتاه برایش بنویس.",
         "یک برگهٔ مسئله + پیشنهاد راه‌حل", "۲۰ دقیقه", "فردی", "problem,build",
         [], "0.00", False),
        ("مأموریت یک‌روزه: یک محتوای آموزشی کوتاه بساز", "one_day",
         "یک نکتهٔ درسی یا مهارتی را در قالب یک پست، ویدیوی کوتاه یا جزوهٔ چندصفحه‌ای برای دیگران آماده کن.",
         "یک محتوای منتشرشده و قابل‌اشتراک", "یک روز", "فردی", "skill,build",
         [{"event_type": "study_completion_verified", "min_count": 1}], "15.00", False),
        ("یک عصر، یک مهارت: ابزار تازه را امتحان کن", "skill_evening",
         "در یک عصر، یک ابزار یا مهارت کوچک را واقعاً امتحان می‌کنی و نتیجه را در دو جمله ثبت می‌کنی.",
         "یک نمونهٔ کوچک + بازخورد کوتاه", "یک عصر", "فردی", "skill,tech",
         [], "8.00", False),
        ("مأموریت واقعی هفته: راهنمای کاربردی برای ورودی‌های جدید", "guide",
         "با یک گروه کوچک، راهنمای عملی «ترم اول» بسازید: از انتخاب واحد تا نقاط گمشدهٔ campus.",
         "یک راهنمای قابل‌ارائه به ورودی‌ها", "یک هفته", "۲ تا ۳ نفر", "guide,help,team",
         [{"event_type": "peer_support_verified", "min_count": 2}], "25.00", True),
        ("مسئلهٔ واقعی: بهبود یک فرایند دانشگاه", "real_problem",
         "یک گروه ۳نفره یک مسئلهٔ واقعی دانشگاه را انتخاب، برایش راه‌حل طراحی و در پایان ارائه می‌کند.",
         "یک ارائهٔ راه‌حل به مدیریت دانشگاه", "دو هفته", "۳ نفر", "problem,team,event",
         [], "40.00", True),
    ]
    for title, kind, desc, output, duration, team, tags, activities, points, is_group in exp_missions_spec:
        if not db.execute(select(Mission).where(Mission.university_id == u1.id, Mission.title_fa == title)).scalar_one_or_none():
            db.add(Mission(university_id=u1.id, title_fa=title, description_fa=desc, goal_type="skill",
                           activities_json=json.dumps(activities), starts_at=now - timedelta(days=1),
                           ends_at=now + timedelta(days=30), max_points=Decimal(points), is_group=is_group,
                           mission_kind=kind, output_fa=output, duration_label_fa=duration,
                           team_size_hint=team, interest_tags=tags))
    db.flush()

    exp_groups_spec = [
        ("ساخت یک ابزار ساده", "build", "در یک هفته یک ابزار کوچک برای مشکل واقعی کلاس بسازید",
         "یک ابزار سادهٔ قابل‌اجرا", "یک هفته، سه نفر", 4),
        ("آمادگی برای ارائه", "skill", "تمرین ارائه و بازخورد هم‌تاها برای جلسهٔ دفاع/سمینار",
         "یک ارائهٔ ۱۰ دقیقه‌ای آماده", "دو هفته، چهار نفر", 5),
        ("کتاب و گفت‌وگو", "explore", "هر هفته یک فصل مشترک می‌خوانیم و درباره‌اش حرف می‌زنیم",
         "سه نشست گفت‌وگو + یادداشت مشترک", "سه هفته، پنج نفر", 6),
        ("حل یک مسئلهٔ محلی", "problem", "شناسایی و پیشنهاد راه‌حل برای یک مسئلهٔ واقعی دانشکده",
         "یک برگهٔ مسئله + ارائهٔ راه‌حل", "یک هفته، سه نفر", 4),
    ]
    for title, tag, goal, output, duration, cap in exp_groups_spec:
        if not db.execute(select(LearningGroup).where(LearningGroup.university_id == u1.id,
                                                      LearningGroup.title_fa == title)).scalar_one_or_none():
            db.add(LearningGroup(university_id=u1.id, mission_id=None, title_fa=title, capacity=cap,
                                 interest_tag=tag, goal_fa=goal, expected_output_fa=output,
                                 duration_label_fa=duration))
    db.flush()

    exp_rewards_spec = [
        ("کارگاه کوچک با یک متخصص (تجربه)", "کارگاه کوچک حضوری/آنلاین با یک متخصص حوزهٔ تو — پرسش مستقیم، ظرفیت محدود.", "workshop", "10.00", 3),
        ("بازدید از آزمایشگاه یا مجموعه (تجربه)", "همراه یک گروه کوچک از یک آزمایشگاه یا مجموعهٔ مرتبط با رشته بازدید می‌کنی.", "resource_access", "12.00", 4),
        ("بازخورد روی رزومه یا نمونه‌کار (تجربه)", "یک منتور رزومه یا نمونه‌کار تو را بررسی و بازخورد مشخص می‌دهد.", "counseling", "8.00", 5),
        ("فرصت ارائهٔ ایده (تجربه)", "ایده‌ات را در یک نشست به گروه یا استاد ارائه می‌کنی و بازخورد می‌گیری.", "project", "15.00", 2),
        ("دسترسی ابزار یا منبع تکمیلی (غیرضروری)", "دسترسی موقت به یک ابزار یا منبع یادگیری مکمل — چیز اضافه، نه جایگزین منابع ضروری.", "resource_access", "6.00", None),
        ("حق انتخاب موضوع رویداد بعدی", "موضوع مأموریت یا رویداد بعدی باشگاه را تو پیشنهاد می‌دهی و رأی می‌گیری.", "auto_perk", "20.00", 1),
        ("منتورینگ یک‌ماهه (تجربه)", "یک ماه همراهی یک منتور برای یک هدف کوچک و مشخص.", "counseling", "30.00", 2),
    ]
    for title, desc, rtype, cost, cap in exp_rewards_spec:
        r = db.execute(select(Reward).where(Reward.university_id == u1.id, Reward.title_fa == title)).scalar_one_or_none()
        if r is None:
            r = Reward(university_id=u1.id, provider_id=prov.id if prov else None, type=rtype,
                       title_fa=title, description_fa=desc, cost_points=Decimal(cost), capacity_total=cap,
                       allocation="first_come", delivery="in_app", kind="experience",
                       goal_tags="skill,explore,build", state="active",
                       validity_fa="در ترم جاری (نمونهٔ آزمایشی)")
            db.add(r)
    if r_unlimited is not None and r_unlimited.kind == "physical":
        r_unlimited.kind = "resource"
    db.flush()

    stories_spec = [
        ("«این تیم چه ساخت؟» — ابزار نوبت‌دهی آزمایشگاه", "build",
         "گروه سه‌نفرهٔ «ساخت یک ابزار ساده» در یک هفته، یک صفحهٔ سادهٔ نوبت‌دهی برای آزمایشگاه ساخت؛ این هفته روی صفحهٔ اصلی دانشکده نصب شد.",
         "گروه «ساخت یک ابزار ساده»"),
        ("«این مأموریت چه چیزی را حل کرد؟» — نقشهٔ گمشدهٔ campus", "help",
         "مأموریت یک‌روزهٔ راهنمای ورودی‌ها به یک نقشهٔ تصویری از نقاط گمشدهٔ دانشکده تبدیل شد؛ ورودی‌های ترم جاری از آن استفاده می‌کنند.",
         "مأموریت واقعی هفته"),
        ("«یک عضو چه تجربه‌ای داشت؟» — اولین نمونه‌کار", "skill",
         "سارا با «یک عصر، یک مهارت» اولین نمونه‌کار وب خودش را ساخت و با رضایت خودش اینجا نمایش داده می‌شود.",
         "سارا (رضایت نمایش ثبت شده)"),
    ]
    for title, kind, body, subject in stories_spec:
        if not db.execute(select(ShowcaseStory).where(ShowcaseStory.university_id == u1.id,
                                                      ShowcaseStory.title_fa == title)).scalar_one_or_none():
            db.add(ShowcaseStory(university_id=u1.id, title_fa=title, body_fa=body, kind=kind,
                                 has_consent=True, subject_label_fa=subject, state="published", published_at=now))

    # پروفایل onboarding نمونه برای سارا (تجربهٔ کامل) — رضا بدون پروفایل می‌ماند تا بنر شروع را ببیند
    if not db.execute(select(OnboardingProfile).where(OnboardingProfile.user_id == users["st1@u1.demo"].id)).scalar_one_or_none():
        db.add(OnboardingProfile(university_id=u1.id, user_id=users["st1@u1.demo"].id, student_ref_id=sara.id,
                                 persona="creator", interests_json=json.dumps(["build", "tech", "problem"], ensure_ascii=False),
                                 completed_at=now, first_badge_awarded=False))

    # ---- ۱۳) برچسب‌گذاری نمونه‌ها و پایان ----
    print("خلاصه: دانشگاه‌ها=2، کاربران=", len(users), "، رویدادهای معتبر پردازش‌شده و دفترکل متوازن.")


if __name__ == "__main__":
    main()
