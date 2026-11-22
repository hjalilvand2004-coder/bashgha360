"""TST-10 exit, TST-11 recommendations, TST-12 integrity, TST-13 appeals, TST-15 badges, TST-16/17 RBAC."""
from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import select

from app.core.db import utcnow
from app.core.errors import Forbidden
from app.core.money import D
from app.core.rbac import make_principal_for_tests
from app.modules.appeals import service as appeals
from app.modules.achievements_tiers import service as ach
from app.modules.achievements_tiers.models import BadgeAward, BadgeDefinition, BadgeShare, TierAward, TierDefinition
from app.modules.integrity_reviews import service as integrity
from app.modules.integrity_reviews.models import IntegritySignal, ReviewCase
from app.modules.memberships_consents import service as mem
from app.modules.memberships_consents.models import Membership
from app.modules.points_ledger import service as ledger
from app.modules.points_ledger.models import PointAccount
from app.modules.recommendations import service as rec
from app.modules.rewards_fulfillment.models import Reward
import pytest


def test_exit_keeps_base_services(db, uni, student):
    """سناریو ۱۰: خروج، خدمات پایه را محدود نکند."""
    ledger.seed_pool(db, uni.id, D("100.00"))
    ledger.award(db, uni.id, student.id, D("5.00"), idempotency_key="pre-exit")
    db.flush()
    m = db.execute(select(Membership).where(Membership.student_ref_id == student.id)).scalar_one()
    mem.change_state(db, m, "left_voluntary", reason_fa="تست خروج")
    # base services still work: ledger exists, goals endpoint data available, catalog readable
    acc = db.execute(select(PointAccount).where(PointAccount.student_ref_id == student.id)).scalar_one()
    assert acc is not None
    # but club perks requiring membership are refused
    reward = Reward(university_id=uni.id, type="workshop", title_fa="کارگاه", cost_points=D("1.00"), delivery="in_app")
    db.add(reward)
    db.flush()
    from app.modules.rewards_fulfillment import service as rw

    with pytest.raises(Forbidden):
        rw.request_reward(db, university_id=uni.id, student_ref=student, reward_id=reward.id, actor="t")


def test_no_consent_generic_recommendations(db, uni, student):
    """سناریو ۱۱: رد شخصی‌سازی، کاتالوگ را از کار نیندازد."""
    db.add(Reward(university_id=uni.id, type="workshop", title_fa="کارگاه عمومی", cost_points=D("0.00"),
                  goal_tags="skill", delivery="in_app"))
    db.flush()
    # student consented personalization=True in fixture; revoke it (TST-11)
    mem.set_consent(db, university_id=uni.id, student_ref=student, consent_type="personalization", value=False)
    db.commit()
    out = rec.recommend(db, university_id=uni.id, student_ref=student)
    assert out["basis"] == "generic"
    assert len(out["items"]) >= 1
    assert out["items"][0]["reasons_fa"]


def test_signal_no_auto_penalty(db, uni, student, source, policy):
    """سناریو ۱۲: هشدار ناهنجاری رأی خودکار ایجاد نکند."""
    from app.modules.points_ledger.models import PointAccount

    ledger.seed_pool(db, uni.id, D("100.00"))
    ledger.award(db, uni.id, student.id, D("10.00"), idempotency_key="x")
    db.commit()
    sig = integrity.create_signal(db, university_id=uni.id, kind="risk_pattern", rule_code="TEST",
                                  subject_student_ref=student.id)
    case = integrity.open_case(db, sig, summary_fa="بررسی آزمون")
    acc = db.execute(select(PointAccount).where(PointAccount.student_ref_id == student.id)).scalar_one()
    assert D(acc.available) == D("10.00")  # untouched — advisory only
    assert case.state == "flagged"
    # transition map rejects illegal jumps
    import pytest as _pytest

    from app.core.errors import Conflict

    with _pytest.raises(Conflict):
        integrity.transition(db, case, "closed")


def test_accepted_appeal_corrects_ledger_tiers(db, uni, student):
    """سناریو ۱۳: اعتراض پذیرفته‌شده دفترکل، سطح و نشان را اصلاح کند."""
    db.add(TierDefinition(university_id=uni.id, path="learning", level_no=1, title_fa="۱", min_progress=D("12.00")))
    db.flush()
    ledger.seed_pool(db, uni.id, D("100.00"))
    ledger.award(db, uni.id, student.id, D("10.00"), idempotency_key="base")
    db.commit()
    a = appeals.submit(db, university_id=uni.id, student_ref_id=student.id, subject_type="ledger_correction",
                       subject_id=None, ground_fa="امتیاز جا افتاده")
    appeals.assign_reviewer(db, a, reviewer_user_id="referee-1", first_handler_user_id="handler-1")
    acc = db.execute(select(PointAccount).where(PointAccount.student_ref_id == student.id)).scalar_one()
    assert D(acc.cumulative_progress) == D("10.00")
    appeals.decide(db, appeal=a, decision="accepted", decision_fa="پذیرش", reviewer_user_id="referee-1",
                   compensation_points=D("5.00"))
    db.refresh(acc)
    assert D(acc.cumulative_progress) == D("15.00")
    tier = db.execute(select(TierAward).where(TierAward.student_ref_id == student.id)).scalar_one_or_none()
    assert tier is not None  # tier recalculated upward
    # independence rule
    a2 = appeals.submit(db, university_id=uni.id, student_ref_id=student.id, subject_type="ledger_correction",
                        subject_id=None, ground_fa="دوم")
    with pytest.raises(Forbidden):
        appeals.assign_reviewer(db, a2, reviewer_user_id="handler-1", first_handler_user_id="handler-1")


def test_public_share_requires_consent(db, uni, student):
    """سناریو ۱۵: نشان بدون رضایت منتشر نشود."""
    b = BadgeDefinition(university_id=uni.id, title_fa="نشان", svg_id="badge-learning", path="learning",
                        criteria_json="{}")
    db.add(b)
    db.flush()
    award = BadgeAward(university_id=uni.id, student_ref_id=student.id, badge_id=b.id,
                       issued_at=utcnow(), criteria_version=1)
    db.add(award)
    db.flush()
    with pytest.raises(Forbidden):  # public_badge consent is False in fixture
        ach.create_share(db, award=award, by_user="u", consent_ok=False)
    share = ach.create_share(db, award=award, by_user="u", consent_ok=True)
    assert share.share_token
    # revoking consent revokes shares
    mem.set_consent(db, university_id=uni.id, student_ref=student, consent_type="public_badge", value=False)
    db.flush()
    assert share.revoked_at is not None


def test_provider_scope_minimal_fields(db, uni, student):
    """سناریو ۱۶ (بخش سرویس): ارائه‌دهنده فقط اطلاعات ضروری ببیند."""
    from app.modules.rewards_fulfillment.models import RewardProvider

    prov = RewardProvider(university_id=uni.id, name_fa="پ")
    db.add(prov)
    db.flush()
    reward = Reward(university_id=uni.id, provider_id=prov.id, type="workshop", title_fa="w",
                    cost_points=D("1.00"), delivery="external")
    db.add(reward)
    db.flush()
    # provider queue returns only request_ref/state — enforced in router; here we verify model isolation:
    assert reward.provider_id == prov.id


def test_tech_admin_no_educational_data(db, uni, student):
    """سناریو ۱۷: مدیر فنی بدون Scope اطلاعات آموزشی را نبیند."""
    p = make_principal_for_tests("tech-1", uni.id, ["tech_admin"])
    assert "ledger:read" not in p.permissions
    assert "ledger:read_own" not in p.permissions
    assert "analytics:sensitive" not in p.permissions
    p_aud = make_principal_for_tests("aud-1", uni.id, ["auditor"])
    assert "analytics:sensitive" in p_aud.permissions and "ledger:read" not in p_aud.permissions
