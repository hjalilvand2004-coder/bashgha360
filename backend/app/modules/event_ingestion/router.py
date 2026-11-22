"""events endpoints — ingest (service auth), self-report, verification, dead-letter (EVT)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...core.errors import Forbidden, NotFound
from ...core.money import D
from ...core.rbac import Principal, get_service_principal, require
from ...modules.audit import service as audit
from ...modules.identity_access.models import StudentReference
from ...modules.memberships_consents.models import ApprovalScope
from ...modules.points_ledger import service as ledger
from ...modules.points_ledger.models import LedgerEntry, LedgerTransaction
from ...shared.idempotency import idempotent_response
from .models import EducationalEvent, EventInbox, IntegrationSource
from .service import ingest

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/ingest")
async def ingest_event(request: Request, db: Session = Depends(get_db),
                       principal: Principal = Depends(get_service_principal)):
    """Service-to-service ingestion with HMAC + idempotency (EVT-01..05)."""
    body = await request.body()
    payload = json.loads(body.decode("utf-8"))
    payload["university_id"] = principal.university_id  # scope from authenticated source (EVT-03)
    key = request.headers.get("Idempotency-Key") or f"evt:{payload.get('event_id')}"

    def execute():
        result = ingest(db, payload, raw_body=body,
                        signature=request.headers.get("X-Signature", ""),
                        integration_source_id=getattr(request.state, "integration_source_id", None))
        return 202, result

    return idempotent_response(request, db, actor="service", key=key, body=body, execute=execute)


class SelfReportIn(BaseModel):
    event_type: str
    activity_reference: str
    note_fa: str = ""


def _self_report_source(db: Session, university_id: str) -> str:
    src = db.execute(select(IntegrationSource).where(
        IntegrationSource.university_id == university_id, IntegrationSource.code == "self-report")).scalar_one_or_none()
    return str(src.id) if src else ""


@router.post("/self-report")
def self_report(body: SelfReportIn, principal: Principal = Depends(require("events:self_report")),
                db: Session = Depends(get_db)):
    """EVT-09: self-declaration only into pending-human state with evidence expectation."""
    if not principal.student_ref_id:
        raise Forbidden("فقط دانشجو می‌تواند خوداظهاری ثبت کند.")
    sref = db.get(StudentReference, principal.student_ref_id)
    now = datetime.now(timezone.utc)
    ev = EducationalEvent(
        university_id=principal.university_id, event_id=f"self-{uuid.uuid4()}",
        schema_version="1.0", source_id=_self_report_source(db, principal.university_id),
        student_reference=sref.external_student_id, event_type=body.event_type,
        occurred_at=now, received_at=now,
        activity_reference=body.activity_reference, verification_status="pending_human",
        correlation_id="self-report", payload_json=json.dumps({"note_fa": body.note_fa}, ensure_ascii=False))
    db.add(ev)
    db.flush()
    db.add(EventInbox(university_id=principal.university_id, message_id=f"self:{ev.id}", event_id=ev.id,
                      state="received"))
    return {"event_id": ev.id, "verification_status": "pending_human",
            "note": "در انتظار شواهد یا تأیید انسانی — تا آن زمان امتیاز نهایی نمی‌شود."}


@router.post("/{event_id}/verify")
def verify_event(event_id: str, body: dict, principal: Principal = Depends(require("approvals:verify")),
                 db: Session = Depends(get_db)):
    """Professor verification within allowed scope (ACC-04). pending → available (LED-04)."""
    ev = db.get(EducationalEvent, event_id)
    if ev is None:
        raise NotFound("رویداد یافت نشد.")
    scopes = db.execute(select(ApprovalScope).where(
        ApprovalScope.professor_user_id == principal.user_id)).scalars().all()
    if not any(ev.activity_reference.startswith(s.activity_scope) for s in scopes):
        raise Forbidden("این فعالیت در حوزهٔ مجاز تأیید شما نیست.")
    if body.get("decision") == "reject":
        ev.verification_status = "rejected"
        audit.write(db, actor=principal.user_id, action="event.rejected", entity="educational_events",
                    entity_id=ev.id, university_id=ev.university_id, after={"reason": body.get("reason_fa", "")})
        return {"verification_status": "rejected"}
    if ev.verification_status != "pending_human":
        raise Forbidden("این رویداد در انتظار تأیید نیست.")
    ev.verification_status = "verified"
    sref = db.execute(select(StudentReference).where(
        StudentReference.university_id == ev.university_id,
        StudentReference.external_student_id == ev.student_reference)).scalar_one_or_none()
    if sref:
        award_tx = db.execute(select(LedgerTransaction).where(
            LedgerTransaction.event_id == ev.id, LedgerTransaction.tx_type == "award")).scalar_one_or_none()
        if award_tx is not None:
            amount = sum((D(e.amount) for e in db.execute(select(LedgerEntry).where(
                LedgerEntry.tx_id == award_tx.id, LedgerEntry.bucket == "pending",
                LedgerEntry.direction == "credit")).scalars().all()), D(0))
            if amount > 0:
                ledger.verify_pending(db, ev.university_id, str(sref.id), amount,
                                      idempotency_key=f"verify:{ev.id}",
                                      event_id=ev.id, reason_fa="تأیید انسانی شواهد", actor=principal.user_id)
    audit.write(db, actor=principal.user_id, action="event.verified", entity="educational_events",
                entity_id=ev.id, university_id=ev.university_id)
    return {"verification_status": "verified"}


@router.get("/pending-verification")
def pending_verification(principal: Principal = Depends(require("approvals:verify")), db: Session = Depends(get_db)):
    """Professor's queue: pending events inside his scope (شواهد و روبرک)."""
    scopes = db.execute(select(ApprovalScope).where(
        ApprovalScope.professor_user_id == principal.user_id)).scalars().all()
    prefixes = tuple(s.activity_scope for s in scopes) or ("__none__",)
    rows = db.execute(select(EducationalEvent).where(
        EducationalEvent.verification_status == "pending_human")).scalars().all()
    items = [{"id": e.id, "student_reference": e.student_reference, "event_type": e.event_type,
              "activity_reference": e.activity_reference, "occurred_at": e.occurred_at.isoformat(),
              "payload": json.loads(e.payload_json or "{}")}
             for e in rows if e.activity_reference.startswith(prefixes)]
    return {"items": items}


@router.get("/dead-letter")
def dead_letter(principal: Principal = Depends(require("events:manage")), db: Session = Depends(get_db)):
    rows = db.execute(select(EventInbox).where(EventInbox.state == "quarantined")
                      .order_by(EventInbox.created_at.desc()).limit(100)).scalars().all()
    return {"items": [{"id": i.id, "message_id": i.message_id, "reason": i.quarantined_reason,
                       "attempts": i.attempts, "created_at": i.created_at.isoformat()} for i in rows]}


@router.post("/dead-letter/{inbox_id}/requeue")
def requeue(inbox_id: str, principal: Principal = Depends(require("events:manage")), db: Session = Depends(get_db)):
    inbox = db.get(EventInbox, inbox_id)
    if inbox is None:
        raise NotFound("پیام یافت نشد.")
    inbox.state, inbox.attempts, inbox.quarantined_reason = "received", 0, None
    return {"state": "received"}
