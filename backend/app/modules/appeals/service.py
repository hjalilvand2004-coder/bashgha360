"""appeals service — independent review path (INT-06, ACC-07, TST-13)."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import utcnow
from ...core.errors import Conflict, Forbidden
from ...core.money import D, ZERO
from ..achievements_tiers import service as ach
from ..audit import service as audit
from ..points_ledger import service as ledger
from .models import Appeal, AppealOutcome

APPEAL_TRANSITIONS = {
    "submitted": {"in_review"},
    "in_review": {"accepted", "rejected"},
    "accepted": {"closed"},
    "rejected": {"closed"},
    "closed": set(),
}


def submit(db: Session, *, university_id: str, student_ref_id: str, subject_type: str,
           subject_id: str | None, ground_fa: str) -> Appeal:
    appeal = Appeal(id=str(uuid.uuid4()), university_id=university_id, student_ref_id=student_ref_id,
                    case_id=subject_id if subject_type == "review_decision" else None,
                    subject_type=subject_type, subject_id=subject_id, ground_fa=ground_fa,
                    state="submitted", submitted_at=utcnow())
    db.add(appeal)
    db.flush()
    return appeal


def assign_reviewer(db: Session, appeal: Appeal, reviewer_user_id: str, first_handler_user_id: str | None) -> Appeal:
    """Independence: referee must differ from the first handler (ACC-07)."""
    if first_handler_user_id and reviewer_user_id == first_handler_user_id:
        raise Forbidden("مرجع اعتراض باید مستقل از کارشناس اولیه باشد.")
    appeal.reviewer_user_id = reviewer_user_id
    _transition(appeal, "in_review")
    return appeal


def _transition(appeal: Appeal, new_state: str) -> None:
    if new_state not in APPEAL_TRANSITIONS.get(appeal.state, set()):
        raise Conflict(f"گذار «{appeal.state} → {new_state}» مجاز نیست.")
    appeal.state = new_state


def decide(db: Session, *, appeal: Appeal, decision: str, decision_fa: str, reviewer_user_id: str,
           compensation_points: Decimal | None = None) -> AppealOutcome:
    """Accepted appeal => ledger compensation + tier/badge recalculation (TST-13)."""
    if appeal.reviewer_user_id != reviewer_user_id:
        raise Forbidden("فقط مرجع مستقل تعیین‌شده می‌تواند تصمیم بگیرد.")
    _transition(appeal, "accepted" if decision == "accepted" else "rejected")
    appeal.decision, appeal.decision_fa, appeal.decided_at = decision, decision_fa, utcnow()
    outcome = AppealOutcome(id=str(uuid.uuid4()), university_id=appeal.university_id, appeal_id=appeal.id)
    if decision == "accepted":
        from ..identity_access.models import StudentReference

        sref = db.get(StudentReference, appeal.student_ref_id)
        delta = D(compensation_points or ZERO)
        tx = None
        if delta != 0:
            tx, _ = ledger.adjust(db, appeal.university_id, appeal.student_ref_id, delta,
                                  bucket="available", progress_delta=delta if delta > 0 else delta,
                                  idempotency_key=f"appeal:{appeal.id}:compensate",
                                  case_id=appeal.case_id, correction_of_tx_id=None,
                                  reason_fa=f"اصلاح پس از پذیرش اعتراض: {decision_fa[:80]}",
                                  actor=f"referee:{reviewer_user_id}")
            outcome.ledger_tx_id = tx.id
        # recompute tiers & badges after correction (INT-06)
        if sref:
            for path in ("learning", "skill", "collaboration"):
                ach.check_tier(db, university_id=appeal.university_id, student_ref_id=str(sref.id), path=path)
            ach.check_badges(db, university_id=appeal.university_id, student_ref_id=str(sref.id))
            outcome.tiers_recalculated = outcome.badges_recalculated = True
        audit.write(db, actor=f"referee:{reviewer_user_id}", action="appeal.accepted",
                    entity="appeals", entity_id=appeal.id, university_id=appeal.university_id,
                    after={"compensation": str(delta), "tx": outcome.ledger_tx_id})
    _transition(appeal, "closed")
    db.add(outcome)
    db.flush()
    return outcome
