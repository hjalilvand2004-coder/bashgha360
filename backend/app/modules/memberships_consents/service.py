"""memberships service — join/consents/exit & lifecycle, personal data export (CLUB-01..07, PRN-04)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import utcnow
from ...core.errors import Conflict, NotFound
from ..identity_access.models import StudentReference
from .models import ConsentRecord, Membership, TermsVersion

MEMBERSHIP_TRANSITIONS = {
    "draft": {"pending_terms"},
    "pending_terms": {"active"},
    "active": {"paused", "left_voluntary", "graduated", "transferred", "suspended"},
    "paused": {"active", "left_voluntary", "graduated"},
    "suspended": {"active", "left_voluntary"},
    "left_voluntary": set(), "graduated": set(), "transferred": set(),
}

CONSENT_TYPES = ("personalization", "public_badge", "notifications")


def current_terms(db: Session, university_id: str) -> TermsVersion | None:
    return db.execute(select(TermsVersion).where(
        TermsVersion.university_id == university_id, TermsVersion.is_current.is_(True))).scalar_one_or_none()


def join(db: Session, *, university_id: str, student_ref: StudentReference, terms_version_id: str,
         consents: dict, goal_service=None) -> Membership:
    m = db.execute(select(Membership).where(Membership.student_ref_id == student_ref.id)).scalar_one_or_none()
    terms = db.get(TermsVersion, terms_version_id)
    if terms is None or str(terms.university_id) != str(university_id) or not terms.is_current:
        raise Conflict("نسخهٔ شرایط معتبر نیست — نسخهٔ فعلی را بپذیرید.")
    if m is None:
        m = Membership(id=str(uuid.uuid4()), university_id=university_id, student_ref_id=student_ref.id,
                       state="pending_terms", membership_no=f"CLUB-{uuid.uuid4().hex[:8].upper()}")
        db.add(m)
        db.flush()
    if m.state not in ("draft", "pending_terms", "left_voluntary", "paused"):
        raise Conflict("عضویت فعال دارید.")
    m.terms_version_id = terms.id
    if m.state == "left_voluntary":
        m.state, m.left_at = "pending_terms", None
    if m.state == "pending_terms":
        m.state, m.joined_at = "active", utcnow()
    for ctype in CONSENT_TYPES:
        set_consent(db, university_id=university_id, student_ref=student_ref, consent_type=ctype,
                    value=bool(consents.get(ctype, False)), terms_version_id=terms.id)
    return m


def set_consent(db: Session, *, university_id: str, student_ref: StudentReference, consent_type: str,
                value: bool, terms_version_id: str | None = None) -> ConsentRecord:
    """CLUB-02/04: consent change is time-stamped, traceable, and has REAL effects."""
    if consent_type not in CONSENT_TYPES:
        raise Conflict("نوع رضایت نامعتبر است.")
    rec = ConsentRecord(id=str(uuid.uuid4()), university_id=university_id, student_ref_id=student_ref.id,
                        consent_type=consent_type, value=value, terms_version_id=terms_version_id,
                        decided_at=utcnow(), revoked_effective_at=utcnow() if not value else None)
    db.add(rec)
    db.flush()
    if consent_type == "public_badge" and not value:
        from ..achievements_tiers.models import BadgeAward, BadgeShare

        shares = db.execute(select(BadgeShare).join(BadgeAward, BadgeAward.id == BadgeShare.badge_award_id)
                            .where(BadgeAward.student_ref_id == student_ref.id,
                                   BadgeShare.revoked_at.is_(None))).scalars().all()
        for s in shares:
            s.revoked_at = utcnow()
    return rec


def latest_consents(db: Session, student_ref_id: str) -> dict:
    out = {c: None for c in CONSENT_TYPES}
    rows = db.execute(select(ConsentRecord).where(ConsentRecord.student_ref_id == student_ref_id)
                      .order_by(ConsentRecord.decided_at.desc())).scalars().all()
    for r in rows:
        if out.get(r.consent_type) is None:
            out[r.consent_type] = {"value": r.value, "decided_at": r.decided_at.isoformat()}
    return out


def has_consent(db: Session, student_ref_id: str, consent_type: str) -> bool:
    row = db.execute(select(ConsentRecord).where(
        ConsentRecord.student_ref_id == student_ref_id, ConsentRecord.consent_type == consent_type)
        .order_by(ConsentRecord.decided_at.desc())).scalars().first()
    return bool(row and row.value)


def change_state(db: Session, membership: Membership, new_state: str, reason_fa: str | None = None) -> Membership:
    if new_state not in MEMBERSHIP_TRANSITIONS.get(membership.state, set()):
        raise Conflict(f"گذار «{membership.state} → {new_state}» مجاز نیست.")
    membership.state = new_state
    membership.state_reason = reason_fa
    if new_state in ("left_voluntary", "graduated", "transferred"):
        membership.left_at = utcnow()
    return membership


def export_personal_data(db: Session, *, student_ref: StudentReference) -> dict:
    """CLUB-07: downloadable allowed personal data with source & freshness (S360-10)."""
    from ..points_ledger.models import PointAccount
    from ..student_goals.models import StudentGoal

    acc = db.execute(select(PointAccount).where(PointAccount.student_ref_id == student_ref.id)).scalar_one_or_none()
    goals = db.execute(select(StudentGoal).where(StudentGoal.student_ref_id == student_ref.id)).scalars().all()
    return {
        "student_reference": student_ref.external_student_id,
        "source": student_ref.source,
        "snapshot_at": student_ref.snapshot_at.isoformat(),
        "university_id": student_ref.university_id,
        "program": student_ref.program,
        "membership_state": (db.execute(select(Membership).where(Membership.student_ref_id == student_ref.id))
                             .scalar_one_or_none().state if db.execute(select(Membership)
                             .where(Membership.student_ref_id == student_ref.id)).scalar_one_or_none() else None),
        "consents": latest_consents(db, student_ref.id),
        "points": {"available": str(acc.available), "reserved": str(acc.reserved),
                   "pending": str(acc.pending), "cumulative_progress": str(acc.cumulative_progress)} if acc else None,
        "goals": [{"type": g.goal_type, "title": g.title_fa, "status": g.status} for g in goals],
        "note": "این خروجی فقط داده‌های مجاز شخصی شماست؛ داده‌های حسابرسی ناشناس نگهداری می‌شوند.",
    }
