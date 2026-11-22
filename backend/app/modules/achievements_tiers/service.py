"""achievements_tiers service — tiers & badges on three independent paths (ACH-01..04)."""
from __future__ import annotations

import json
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.db import utcnow
from ...core.errors import Forbidden
from ...core.money import D
from ..event_ingestion.models import EducationalEvent
from ..identity_access.models import StudentReference
from ..points_ledger.models import PointAccount
from .models import BadgeAward, BadgeDefinition, BadgeShare, TierAward, TierDefinition


def progress_for_path(db: Session, student_ref_id: str, path: str) -> float:
    acc = db.execute(select(PointAccount).where(PointAccount.student_ref_id == student_ref_id)).scalar_one_or_none()
    return float(D(acc.cumulative_progress)) if acc else 0.0


def check_tier(db: Session, *, university_id: str, student_ref_id: str, path: str) -> TierAward | None:
    """Award the highest tier whose threshold is met (idempotent per tier)."""
    best = db.execute(select(TierDefinition).where(
        TierDefinition.university_id == university_id, TierDefinition.path == path,
        TierDefinition.min_progress <= D(progress_for_path(db, student_ref_id, path))
    ).order_by(TierDefinition.min_progress.desc())).scalars().first()
    if best is None:
        return None
    existing = db.execute(select(TierAward).where(
        TierAward.student_ref_id == student_ref_id, TierAward.tier_id == best.id)).scalar_one_or_none()
    if existing is not None:
        return existing
    award = TierAward(id=str(uuid.uuid4()), university_id=university_id,
                      student_ref_id=student_ref_id, tier_id=best.id, awarded_at=utcnow())
    db.add(award)
    db.flush()
    return award


def check_badges(db: Session, *, university_id: str, student_ref_id: str) -> list[BadgeAward]:
    """Auto badges: criteria {event_type: min_count} over verified events (idempotent)."""
    ext = select(StudentReference.external_student_id).where(StudentReference.id == student_ref_id)
    defs = db.execute(select(BadgeDefinition).where(
        BadgeDefinition.university_id == university_id, BadgeDefinition.state == "active",
        BadgeDefinition.is_auto.is_(True))).scalars().all()
    awarded: list[BadgeAward] = []
    for b in defs:
        criteria = json.loads(b.criteria_json or "{}")
        ok = True
        for ev_type, min_count in criteria.items():
            try:
                threshold = int(min_count)
            except (TypeError, ValueError):
                # معیار غیرشمارشی (مثل output/group) — نشان داستانی است و در جریان
                # دیگری صادر می‌شود؛ شمارش رویداد نمی‌تواند آن را تأیید یا رد کند
                ok = False
                break
            cnt = db.execute(
                select(func.count()).select_from(EducationalEvent).where(
                    EducationalEvent.university_id == university_id,
                    EducationalEvent.event_type == ev_type,
                    EducationalEvent.verification_status == "verified",
                    EducationalEvent.student_reference.in_(ext),
                )).scalar() or 0
            if int(cnt) < threshold:
                ok = False
                break
        if not ok:
            continue
        exists = db.execute(select(BadgeAward).where(
            BadgeAward.student_ref_id == student_ref_id, BadgeAward.badge_id == b.id,
            BadgeAward.criteria_version == b.criteria_version)).scalar_one_or_none()
        if exists is not None:
            continue
        expires = utcnow() + timedelta(days=30 * b.valid_months) if b.valid_months else None
        award = BadgeAward(id=str(uuid.uuid4()), university_id=university_id,
                           student_ref_id=student_ref_id, badge_id=b.id, issued_at=utcnow(),
                           expires_at=expires, criteria_version=b.criteria_version)
        db.add(award)
        awarded.append(award)
    if awarded:
        db.flush()
    return awarded


def create_share(db: Session, *, award: BadgeAward, by_user: str | None, consent_ok: bool) -> BadgeShare:
    """ACH-03: public display requires explicit consent; link revocable & expirable."""
    if not consent_ok:
        raise Forbidden("نمایش عمومی نشان بدون رضایت ثبت‌شدهٔ شما مجاز نیست.")  # TST-15
    share = BadgeShare(id=str(uuid.uuid4()), university_id=award.university_id,
                       badge_award_id=award.id, share_token=secrets.token_urlsafe(24),
                       created_by_user=by_user, expires_at=utcnow() + timedelta(days=90))
    db.add(share)
    db.flush()
    return share


def revoke_award(db: Session, award: BadgeAward, reason_fa: str) -> None:
    award.state, award.reason_fa = "revoked", reason_fa
