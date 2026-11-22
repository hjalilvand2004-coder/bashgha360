"""recommendations + notifications + analytics + audit + reviews + appeals + goals + data-corrections routers."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.db import get_db
from ...core.errors import NotFound
from ...core.money import D
from ...core.rbac import Principal, require
from ...modules.identity_access.models import StudentReference
from ...modules.audit import service as audit
from ...modules.audit.models import AuditLog
from ...modules.appeals import service as appeals_svc
from ...modules.appeals.models import Appeal
from ...modules.integrity_reviews import service as integrity
from ...modules.integrity_reviews.models import CaseDecision, CaseExplanation, ReviewCase
from ...modules.notifications.models import Notification, NotificationPreference
from ...modules.points_ledger.models import LedgerTransaction
from ...modules.rewards_fulfillment.models import RewardRequest
from ...modules.student_goals.models import AcademicPeriod, DataCorrectionRequest, StudentGoal
from . import service as rec

rec_router = APIRouter(prefix="/recommendations", tags=["recommendations"])
notif_router = APIRouter(prefix="/notifications", tags=["notifications"])
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])
audit_router = APIRouter(prefix="/audit", tags=["audit"])
reviews_router = APIRouter(prefix="/reviews", tags=["reviews"])
appeals_router = APIRouter(prefix="/appeals", tags=["appeals"])
goals_router = APIRouter(prefix="/goals", tags=["goals"])
dc_router = APIRouter(prefix="/data-corrections", tags=["data-corrections"])


@rec_router.get("")
def get_recommendations(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """TST-11: no consent ⇒ generic recommendations, catalog still works."""
    sref = db.get(StudentReference, principal.student_ref_id) if principal.student_ref_id else None
    return rec.recommend(db, university_id=principal.university_id, student_ref=sref)


class FeedbackIn(BaseModel):
    item_id: str
    feedback: str
    note: str | None = None


@rec_router.post("/feedback")
def send_feedback(body: FeedbackIn, principal: Principal = Depends(require("ledger:read_own")),
                  db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        raise NotFound("پروفایل یافت نشد.")
    rec.feedback(db, item_id=body.item_id, student_ref_id=principal.student_ref_id,
                 feedback=body.feedback, note=body.note)
    return {"ok": True}


@notif_router.get("")
def my_notifications(principal: Principal = Depends(require("notifications:read_own")),
                     db: Session = Depends(get_db)):
    rows = db.execute(select(Notification).where(Notification.user_id == principal.user_id)
                      .order_by(Notification.created_at.desc()).limit(50)).scalars().all()
    return {"items": [{"id": n.id, "kind": n.kind, "title_fa": n.title_fa, "body_fa": n.body_fa,
                       "state": n.state, "transactional": n.transactional,
                       "created_at": n.created_at.isoformat(), "read_at": n.read_at.isoformat() if n.read_at else None}
                      for n in rows]}


@notif_router.post("/{notification_id}/read")
def mark_read(notification_id: str, principal: Principal = Depends(require("notifications:read_own")),
              db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != principal.user_id:
        raise NotFound("اعلان یافت نشد.")
    n.read_at = datetime.now(timezone.utc)
    return {"ok": True}


@notif_router.get("/preferences")
def get_prefs(principal: Principal = Depends(require("notifications:read_own")), db: Session = Depends(get_db)):
    p = db.execute(select(NotificationPreference).where(NotificationPreference.user_id == principal.user_id)).scalar_one_or_none()
    if p is None:
        return {"channels": {"in_app": True, "email": True, "sms": False}, "quiet_start": None,
                "quiet_end": None, "daily_cap": 10, "mute_until": None}
    return {"channels": json.loads(p.channels_json or "{}"), "quiet_start": p.quiet_start,
            "quiet_end": p.quiet_end, "daily_cap": p.daily_cap,
            "mute_until": p.mute_until.isoformat() if p.mute_until else None}


@notif_router.patch("/preferences")
def patch_prefs(body: dict, principal: Principal = Depends(require("notifications:read_own")),
                db: Session = Depends(get_db)):
    p = db.execute(select(NotificationPreference).where(NotificationPreference.user_id == principal.user_id)).scalar_one_or_none()
    if p is None:
        p = NotificationPreference(id=str(uuid.uuid4()), university_id=principal.university_id, user_id=principal.user_id)
        db.add(p)
    if "channels" in body:
        p.channels_json = json.dumps(body["channels"], ensure_ascii=False)
    for k in ("quiet_start", "quiet_end"):
        if k in body:
            setattr(p, k, body[k])
    if "daily_cap" in body:
        p.daily_cap = int(body["daily_cap"])
    if "mute_until" in body:
        p.mute_until = datetime.fromisoformat(body["mute_until"]) if body["mute_until"] else None
    return {"ok": True}


@analytics_router.get("/overview")
def overview(period_id: str | None = None, principal: Principal = Depends(require("analytics:read")),
             db: Session = Depends(get_db)):
    """ANA-01: real aggregates with definition/window/coverage + k-anonymity (ANA-03)."""
    k = get_settings().k_anonymity_threshold
    uni = principal.university_id

    def safe_count(q) -> int | None:
        n = db.execute(q).scalar() or 0
        return int(n) if int(n) >= k else None  # small groups are hidden

    awarded = safe_count(select(func.count()).select_from(LedgerTransaction).where(
        LedgerTransaction.university_id == uni, LedgerTransaction.tx_type == "award"))
    spent = safe_count(select(func.count()).select_from(LedgerTransaction).where(
        LedgerTransaction.university_id == uni, LedgerTransaction.tx_type == "spend"))
    requests = safe_count(select(func.count()).select_from(RewardRequest).where(
        RewardRequest.university_id == uni))
    cases = safe_count(select(func.count()).select_from(ReviewCase).where(ReviewCase.university_id == uni))
    return {
        "label": "دادهٔ تجمیعی واقعی سامانه",
        "metrics": [
            {"key": "points_awarded_tx", "title_fa": "تراکنش‌های کسب امتیاز", "value": awarded,
             "definition_fa": "تعداد تراکنش award ثبت‌شده در دفترکل", "window_fa": "کل دوره",
             "coverage_fa": "همهٔ دانشجویان دارای حساب", "hidden_small_group": awarded is None},
            {"key": "reward_spend_tx", "title_fa": "مصرف امتیاز پاداش", "value": spent,
             "definition_fa": "تعداد تراکنش spend (تحویل پاداش)", "window_fa": "کل دوره",
             "coverage_fa": "همهٔ درخواست‌های پاداش", "hidden_small_group": spent is None},
            {"key": "reward_requests", "title_fa": "درخواست‌های پاداش", "value": requests,
             "definition_fa": "همهٔ درخواست‌های ثبت‌شده", "window_fa": "کل دوره",
             "coverage_fa": "همهٔ اعضا", "hidden_small_group": requests is None},
            {"key": "review_cases", "title_fa": "پرونده‌های بررسی", "value": cases,
             "definition_fa": "پرونده‌های سلامت آموزشی", "window_fa": "کل دوره",
             "coverage_fa": "همهٔ سیگنال‌ها", "hidden_small_group": cases is None},
        ],
        "note": "افزایش کلیک شاخص موفقیت آموزشی نیست؛ این گزارش توصیفی است و اثبات علیت نمی‌کند."}


@audit_router.get("")
def audit_list(entity: str | None = None, page: int = 1, page_size: int = 50,
               principal: Principal = Depends(require("audit:read")), db: Session = Depends(get_db)):
    q = db.query(AuditLog).filter(AuditLog.university_id == principal.university_id)
    if entity:
        q = q.filter(AuditLog.entity == entity)
    q = q.order_by(AuditLog.created_at.desc())
    rows = q.limit(min(page_size, 100)).offset((page - 1) * page_size).all()
    return {"items": [{"id": a.id, "actor": a.actor, "action": a.action, "entity": a.entity,
                       "entity_id": a.entity_id, "created_at": a.created_at.isoformat(),
                       "correlation_id": a.correlation_id} for a in rows], "page": page}


@reviews_router.get("/cases")
def case_queue(state: str | None = None, principal: Principal = Depends(require("reviews:handle")),
               db: Session = Depends(get_db)):
    q = select(ReviewCase).where(ReviewCase.university_id == principal.university_id)
    if state:
        q = q.where(ReviewCase.state == state)
    rows = db.execute(q.order_by(ReviewCase.opened_at.desc()).limit(100)).scalars().all()
    return {"items": [{"id": c.id, "state": c.state, "student_ref_id": c.student_ref_id,
                       "summary_fa": c.summary_fa, "opened_at": c.opened_at.isoformat(),
                       "sla_due_at": c.sla_due_at.isoformat() if c.sla_due_at else None,
                       "sla_breached": c.sla_breached} for c in rows]}


@reviews_router.get("/cases/{case_id}")
def case_detail(case_id: str, principal: Principal = Depends(require("reviews:handle")), db: Session = Depends(get_db)):
    c = db.get(ReviewCase, case_id)
    if c is None:
        raise NotFound("پرونده یافت نشد.")
    explanations = db.execute(select(CaseExplanation).where(CaseExplanation.case_id == case_id)).scalars().all()
    decisions = db.execute(select(CaseDecision).where(CaseDecision.case_id == case_id)).scalars().all()
    return {"case": {"id": c.id, "state": c.state, "summary_fa": c.summary_fa,
                     "opened_at": c.opened_at.isoformat(), "sla_breached": c.sla_breached},
            "explanations": [{"body": e.body, "submitted_at": e.submitted_at.isoformat()} for e in explanations],
            "decisions": [{"decision": d.decision, "justification_fa": d.justification_fa,
                           "decided_at": d.decided_at.isoformat()} for d in decisions]}


@reviews_router.post("/cases/{case_id}/explanation")
def add_explanation(case_id: str, body: dict, principal: Principal = Depends(require("ledger:read_own")),
                    db: Session = Depends(get_db)):
    """Student's awaited explanation (awaiting_explanation step)."""
    c = db.get(ReviewCase, case_id)
    if c is None or c.student_ref_id != principal.student_ref_id:
        raise NotFound("پرونده یافت نشد.")
    db.add(CaseExplanation(id=str(uuid.uuid4()), university_id=c.university_id, case_id=case_id,
                           student_ref_id=c.student_ref_id, body=str(body.get("body", "")),
                           submitted_at=datetime.now(timezone.utc)))
    return {"ok": True, "note": "پاسخ شما ثبت شد و در جریان رسیدگی دیده می‌شود."}


@reviews_router.post("/cases/{case_id}/transition")
def case_transition(case_id: str, body: dict, principal: Principal = Depends(require("reviews:handle")),
                    db: Session = Depends(get_db)):
    c = db.get(ReviewCase, case_id)
    if c is None:
        raise NotFound("پرونده یافت نشد.")
    integrity.transition(db, c, str(body["state"]), actor=principal.user_id)
    return {"state": c.state}


@reviews_router.post("/cases/{case_id}/decide")
def decide_case(case_id: str, body: dict, principal: Principal = Depends(require("reviews:handle")),
                db: Session = Depends(get_db)):
    c = db.get(ReviewCase, case_id)
    if c is None:
        raise NotFound("پرونده یافت نشد.")
    d = integrity.decide(db, case=c, decision=str(body["decision"]),
                         justification_fa=str(body.get("justification_fa", "")),
                         decided_by=principal.user_id, affected_tx_id=body.get("affected_tx_id"))
    return {"decision": d.decision, "case_state": c.state}


class AppealIn(BaseModel):
    subject_type: str
    subject_id: str | None = None
    ground_fa: str


@appeals_router.post("")
def submit_appeal(body: AppealIn, principal: Principal = Depends(require("appeals:submit")),
                  db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        raise NotFound("پروفایل یافت نشد.")
    a = appeals_svc.submit(db, university_id=principal.university_id, student_ref_id=principal.student_ref_id,
                           subject_type=body.subject_type, subject_id=body.subject_id, ground_fa=body.ground_fa)
    return {"id": a.id, "state": a.state}


@appeals_router.get("/mine")
def my_appeals(principal: Principal = Depends(require("appeals:submit")), db: Session = Depends(get_db)):
    rows = db.execute(select(Appeal).where(Appeal.student_ref_id == principal.student_ref_id)
                      .order_by(Appeal.submitted_at.desc())).scalars().all()
    return {"items": [{"id": a.id, "subject_type": a.subject_type, "state": a.state,
                       "decision_fa": a.decision_fa, "submitted_at": a.submitted_at.isoformat()} for a in rows]}


@appeals_router.get("/queue")
def appeal_queue(principal: Principal = Depends(require("appeals:review")), db: Session = Depends(get_db)):
    rows = db.execute(select(Appeal).where(Appeal.university_id == principal.university_id,
                                           Appeal.state.in_(["submitted", "in_review"]))).scalars().all()
    return {"items": [{"id": a.id, "state": a.state, "subject_type": a.subject_type,
                       "ground_fa": a.ground_fa, "student_ref_id": a.student_ref_id,
                       "reviewer_user_id": a.reviewer_user_id} for a in rows]}


@appeals_router.post("/{appeal_id}/assign")
def assign_appeal(appeal_id: str, body: dict, principal: Principal = Depends(require("appeals:review")),
                  db: Session = Depends(get_db)):
    a = db.get(Appeal, appeal_id)
    if a is None:
        raise NotFound("اعتراض یافت نشد.")
    appeals_svc.assign_reviewer(db, a, reviewer_user_id=principal.user_id,
                                first_handler_user_id=body.get("first_handler_user_id"))
    return {"state": a.state}


@appeals_router.post("/{appeal_id}/decide")
def decide_appeal(appeal_id: str, body: dict, principal: Principal = Depends(require("appeals:review")),
                  db: Session = Depends(get_db)):
    a = db.get(Appeal, appeal_id)
    if a is None:
        raise NotFound("اعتراض یافت نشد.")
    outcome = appeals_svc.decide(db, appeal=a, decision=str(body["decision"]),
                                 decision_fa=str(body.get("decision_fa", "")),
                                 reviewer_user_id=principal.user_id,
                                 compensation_points=str(body.get("compensation_points", "0")))
    return {"state": a.state, "ledger_tx_id": outcome.ledger_tx_id,
            "tiers_recalculated": outcome.tiers_recalculated}


class GoalIn(BaseModel):
    goal_type: str
    title_fa: str


@goals_router.get("")
def my_goals(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    rows = db.execute(select(StudentGoal).where(StudentGoal.student_ref_id == principal.student_ref_id)).scalars().all()
    return {"items": [{"id": g.id, "goal_type": g.goal_type, "title_fa": g.title_fa, "status": g.status} for g in rows]}


@goals_router.post("")
def add_goal(body: GoalIn, principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """CLUB-03: allowed goal types only."""
    if body.goal_type not in ("weakness", "exam_prep", "skill", "collaboration", "other"):
        raise NotFound("نوع هدف مجاز نیست.")
    g = StudentGoal(id=str(uuid.uuid4()), university_id=principal.university_id,
                    student_ref_id=principal.student_ref_id, goal_type=body.goal_type,
                    title_fa=body.title_fa, status="active", declared_at=datetime.now(timezone.utc))
    db.add(g)
    db.flush()
    return {"id": g.id}


@goals_router.post("/{goal_id}/archive")
def archive_goal(goal_id: str, principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    g = db.get(StudentGoal, goal_id)
    if g is None or g.student_ref_id != principal.student_ref_id:
        raise NotFound("هدف یافت نشد.")
    g.status = "archived"
    return {"status": g.status}


@dc_router.post("")
def submit_correction(body: dict, principal: Principal = Depends(require("appeals:submit")),
                      db: Session = Depends(get_db)):
    d = DataCorrectionRequest(id=str(uuid.uuid4()), university_id=principal.university_id,
                              requester_user_id=principal.user_id,
                              subject_entity=str(body.get("subject_entity", "profile")),
                              subject_id=body.get("subject_id"), reason_fa=str(body.get("reason_fa", "")),
                              state="submitted")
    db.add(d)
    db.flush()
    return {"id": d.id, "state": d.state}


@dc_router.get("/mine")
def my_corrections(principal: Principal = Depends(require("appeals:submit")), db: Session = Depends(get_db)):
    rows = db.execute(select(DataCorrectionRequest).where(
        DataCorrectionRequest.requester_user_id == principal.user_id)).scalars().all()
    return {"items": [{"id": d.id, "subject_entity": d.subject_entity, "state": d.state,
                       "reason_fa": d.reason_fa} for d in rows]}


@goals_router.get("/periods")
def periods(principal: Principal = Depends(require("policies:read")), db: Session = Depends(get_db)):
    rows = db.execute(select(AcademicPeriod).where(AcademicPeriod.university_id == principal.university_id)).scalars().all()
    return {"items": [{"id": p.id, "title_fa": p.title_fa, "starts_at": p.starts_at.isoformat(),
                       "ends_at": p.ends_at.isoformat(), "is_current": p.is_current} for p in rows]}
