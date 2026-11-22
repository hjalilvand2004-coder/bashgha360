"""integrity_reviews service — deterministic controls + rule-based risk checks (INT-01..08, PRN-07).

Deterministic controls raise/block. Probabilistic patterns only open a ReviewCase —
never an automatic verdict, never broad blocking (TST-12).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.db import utcnow
from ...core.errors import Conflict, Forbidden
from .models import CaseDecision, CaseExplanation, IntegritySignal, ReviewCase

CASE_TRANSITIONS = {
    "flagged": {"data_validation", "human_review", "dismissed"},
    "data_validation": {"human_review", "dismissed"},
    "human_review": {"awaiting_explanation", "decided"},
    "awaiting_explanation": {"decided"},
    "decided": {"notified", "appealed"},
    "notified": {"closed", "appealed"},
    "appealed": {"final_review"},
    "final_review": {"closed"},
    "dismissed": {"closed"},
    "closed": set(),
}


def create_signal(db: Session, *, university_id: str, kind: str, rule_code: str, severity: str = "info",
                  subject_student_ref: str | None = None, refs: dict | None = None, advisory: bool = True) -> IntegritySignal:
    sig = IntegritySignal(university_id=university_id, kind=kind, rule_code=rule_code, severity=severity,
                          subject_student_ref=subject_student_ref, refs_json=json.dumps(refs or {}, ensure_ascii=False),
                          is_advisory=advisory)
    db.add(sig)
    db.flush()
    return sig


def open_case(db: Session, signal: IntegritySignal, *, summary_fa: str, sla_hours: int = 72) -> ReviewCase:
    """SLA-tracked case (INT-04)."""
    case = ReviewCase(university_id=signal.university_id, signal_id=signal.id,
                      student_ref_id=signal.subject_student_ref, state="flagged", opened_at=utcnow(),
                      sla_due_at=utcnow() + timedelta(hours=sla_hours), summary_fa=summary_fa)
    db.add(case)
    db.flush()
    return case


def check_event_patterns(db: Session, *, university_id: str, event, student_ref_id: str) -> None:
    """Rule-based risk checks with explicit titles (INT-08). Advisory only."""
    hour_ago = utcnow() - timedelta(hours=1)
    burst = db.execute(select(func.count()).select_from(type(event)).where(
        type(event).university_id == university_id,
        type(event).student_reference == event.student_reference,
        type(event).received_at >= hour_ago,
    )).scalar() or 0
    if burst >= 20:  # burst volume — advisory, human review required
        sig = create_signal(db, university_id=university_id, kind="risk_pattern", rule_code="BURST_VOLUME_1H",
                            severity="warning", subject_student_ref=student_ref_id,
                            refs={"count_1h": int(burst), "event": event.event_id})
        if not _has_open_case(db, sig.id):
            open_case(db, sig, summary_fa="الگوی حجم فعالیت ناسازگار در یک ساعت مشاهده شد؛ بررسی انسانی لازم است.")

    day_ago = utcnow() - timedelta(hours=24)
    repeats = db.execute(select(func.count()).select_from(type(event)).where(
        type(event).university_id == university_id,
        type(event).student_reference == event.student_reference,
        type(event).event_type == event.event_type,
        type(event).activity_reference == event.activity_reference,
        type(event).received_at >= day_ago,
    )).scalar() or 0
    if repeats >= 5:
        sig = create_signal(db, university_id=university_id, kind="risk_pattern", rule_code="REPEAT_ACTIVITY_24H",
                            severity="warning", subject_student_ref=student_ref_id,
                            refs={"count_24h": int(repeats), "activity": event.activity_reference})
        if not _has_open_case(db, sig.id):
            open_case(db, sig, summary_fa="تکرار بی‌هدف یک فعالیت در بازهٔ ۲۴ ساعت مشاهده شد.")


def _has_open_case(db: Session, signal_id: str) -> bool:
    return db.execute(select(ReviewCase).where(
        ReviewCase.signal_id == signal_id,
        ReviewCase.state.notin_(["closed", "dismissed"]),
    )).scalar_one_or_none() is not None


def transition(db: Session, case: ReviewCase, new_state: str, actor: str | None = None) -> ReviewCase:
    if new_state not in CASE_TRANSITIONS.get(case.state, set()):
        raise Conflict(f"گذار «{case.state} → {new_state}» در گردش پرونده مجاز نیست.")
    case.state = new_state
    if new_state == "decided":
        case.decided_at, case.decided_by = utcnow(), actor
    return case


def decide(db: Session, *, case: ReviewCase, decision: str, justification_fa: str, decided_by: str,
           affected_tx_id: str | None = None) -> CaseDecision:
    """Documented & proportionate decision (INT-06). Only the related tx may be affected (INT-05)."""
    if decision not in {"cleared", "violation_minor", "violation_major", "refer_official"}:
        raise Conflict("نوع تصمیم نامعتبر است.")
    d = CaseDecision(case_id=case.id, university_id=case.university_id, decision=decision,
                     justification_fa=justification_fa, affected_tx_id=affected_tx_id,
                     decided_by=decided_by, decided_at=utcnow())
    db.add(d)
    transition(db, case, "decided", actor=decided_by)
    if case.student_ref_id:
        from ..notifications import service as notif
        from ..identity_access.models import StudentReference

        sref = db.get(StudentReference, case.student_ref_id)
        if sref and sref.user_id:
            notif.notify(db, university_id=case.university_id, user_id=str(sref.user_id),
                         kind="case_result", title_fa="نتیجهٔ بررسی پرونده",
                         body_fa="پروندهٔ بررسی شما به نتیجه رسید. جزئیات در بخش «پرونده‌ها» قابل مشاهده است.",
                         transactional=True, dedupe_key=f"case:{case.id}:decided")
    return d


def sla_sweep(db: Session) -> int:
    """هشدار تأخیر رسیدگی (INT-04)."""
    rows = db.execute(select(ReviewCase).where(
        ReviewCase.state.notin_(["closed", "dismissed"]),
        ReviewCase.sla_due_at.is_not(None),
        ReviewCase.sla_due_at < utcnow(),
        ReviewCase.sla_breached.is_(False),
    )).scalars().all()
    for c in rows:
        c.sla_breached = True
    return len(rows)
