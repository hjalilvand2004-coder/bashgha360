"""rewards + reward-requests + providers endpoints (RWD)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...core.errors import NotFound
from ...core.money import D
from ...core.rbac import Principal, get_service_principal, require
from ...modules.identity_access.models import StudentReference
from ...modules.audit import service as audit
from ...shared.idempotency import idempotent_response
from . import service as rw
from .models import DeliveryReceipt, FulfillmentAttempt, ReconciliationCase, Reward, RewardProvider, RewardRequest

router = APIRouter(prefix="/rewards", tags=["rewards"])
req_router = APIRouter(prefix="/reward-requests", tags=["reward-requests"])
prov_router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
def catalog(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    rows = db.execute(select(Reward).where(Reward.university_id == principal.university_id,
                                           Reward.state == "active")).scalars().all()
    return {"items": [{"id": r.id, "type": r.type, "title_fa": r.title_fa, "description_fa": r.description_fa,
                       "cost_points": str(D(r.cost_points)), "capacity_total": r.capacity_total,
                       "allocation": r.allocation, "delivery": r.delivery, "is_essential": r.is_essential,
                       "auto_grant": r.auto_grant, "validity_fa": r.validity_fa,
                       "refund_policy_fa": r.refund_policy_fa, "kind": r.kind,
                       "data_consent_note": r.data_consent_note} for r in rows]}


@router.post("")
def create_reward(body: dict, principal: Principal = Depends(require("rewards:manage")), db: Session = Depends(get_db)):
    r = Reward(id=str(uuid.uuid4()), university_id=principal.university_id,
               provider_id=body.get("provider_id"), type=body["type"], title_fa=body["title_fa"],
               description_fa=body.get("description_fa", ""), cost_points=str(body.get("cost_points", "0")),
               is_essential=bool(body.get("is_essential", False)), auto_grant=bool(body.get("auto_grant", False)),
               capacity_total=body.get("capacity_total"), allocation=body.get("allocation", "first_come"),
               delivery=body.get("delivery", "in_app"),
               conditions_json=__import__("json").dumps(body.get("conditions", {}), ensure_ascii=False),
               validity_fa=body.get("validity_fa"), refund_policy_fa=body.get("refund_policy_fa", ""),
               data_consent_note=body.get("data_consent_note"), goal_tags=body.get("goal_tags", ""),
               kind=body.get("kind", "physical"))
    db.add(r)
    db.flush()
    audit.write(db, actor=principal.user_id, action="reward.created", entity="reward_items", entity_id=r.id,
                university_id=principal.university_id, after={"title_fa": r.title_fa, "cost": str(r.cost_points)})
    return {"id": r.id}


@router.get("/{reward_id}")
def reward_detail(reward_id: str, principal: Principal = Depends(require("ledger:read_own")),
                  db: Session = Depends(get_db)):
    r = db.get(Reward, reward_id)
    if r is None or str(r.university_id) != principal.university_id:
        raise NotFound("پاداش یافت نشد.")
    return {"id": r.id, "title_fa": r.title_fa, "description_fa": r.description_fa,
            "cost_points": str(D(r.cost_points)), "capacity_total": r.capacity_total,
            "conditions": __import__("json").loads(r.conditions_json or "{}"),
            "delivery": r.delivery, "validity_fa": r.validity_fa,
            "refund_policy_fa": r.refund_policy_fa, "data_consent_note": r.data_consent_note}


class RequestIn(BaseModel):
    reward_id: str


@req_router.post("")
async def create_request(request: Request, principal: Principal = Depends(require("rewards:request")),
                         db: Session = Depends(get_db)):
    """Idempotent command (API-04). Capacity+points reserved in one tx (RWD-05)."""
    body = await request.body()
    data = __import__("json").loads(body.decode() or "{}")
    key = request.headers.get("Idempotency-Key") or f"reward-req:{principal.user_id}:{data.get('reward_id')}"
    if not principal.student_ref_id:
        raise NotFound("پروفایل دانشجویی یافت نشد.")

    def execute():
        sref = db.get(StudentReference, principal.student_ref_id)
        req = rw.request_reward(db, university_id=principal.university_id, student_ref=sref,
                                reward_id=data.get("reward_id", ""), actor=principal.user_id)
        return 201, {"request_id": req.id, "state": req.state, "ttl_expires_at": req.ttl_expires_at.isoformat()}

    return idempotent_response(request, db, actor=principal.user_id, key=key, body=body, execute=execute)


@req_router.get("")
def my_requests(principal: Principal = Depends(require("rewards:request")), db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        return {"items": []}
    rows = db.execute(select(RewardRequest).where(RewardRequest.student_ref_id == principal.student_ref_id)
                      .order_by(RewardRequest.requested_at.desc())).scalars().all()
    out = []
    for r in rows:
        reward = db.get(Reward, r.reward_id)
        receipt = db.execute(select(DeliveryReceipt).where(DeliveryReceipt.request_id == r.id)).scalar_one_or_none()
        out.append({"id": r.id, "reward_title_fa": reward.title_fa if reward else "",
                    "state": r.state, "requested_at": r.requested_at.isoformat(),
                    "ttl_expires_at": r.ttl_expires_at.isoformat() if r.ttl_expires_at else None,
                    "cancel_reason_fa": r.cancel_reason_fa,
                    "has_receipt": receipt is not None})
    return {"items": out}


@req_router.post("/{request_id}/cancel")
def cancel_request(request_id: str, principal: Principal = Depends(require("rewards:request")),
                   db: Session = Depends(get_db)):
    req = db.get(RewardRequest, request_id)
    if req is None or req.student_ref_id != principal.student_ref_id:
        raise NotFound("درخواست یافت نشد.")
    rw.cancel(db, req, actor=principal.user_id)
    return {"state": req.state}


@req_router.post("/{request_id}/approve")
def approve_request(request_id: str, principal: Principal = Depends(require("rewards:approve")),
                    db: Session = Depends(get_db)):
    req = db.get(RewardRequest, request_id)
    if req is None or str(req.university_id) != principal.university_id:
        raise NotFound("درخواست یافت نشد.")
    rw.approve(db, req, principal.user_id)
    audit.write(db, actor=principal.user_id, action="reward.approved", entity="reward_requests",
                entity_id=req.id, university_id=req.university_id)
    return {"state": req.state}


@req_router.post("/{request_id}/deliver")
def deliver_request(request_id: str, principal: Principal = Depends(require("rewards:approve")),
                    db: Session = Depends(get_db)):
    req = db.get(RewardRequest, request_id)
    if req is None:
        raise NotFound("درخواست یافت نشد.")
    rw.start_fulfilling(db, req, principal.user_id)
    code = rw.deliver_in_app(db, req, principal.user_id)
    return {"state": req.state, "one_time_code": code}


@req_router.get("/{request_id}/receipt")
def receipt(request_id: str, principal: Principal = Depends(require("rewards:request")),
            db: Session = Depends(get_db)):
    req = db.get(RewardRequest, request_id)
    if req is None or req.student_ref_id != principal.student_ref_id:
        raise NotFound("درخواست یافت نشد.")
    rec = db.execute(select(DeliveryReceipt).where(DeliveryReceipt.request_id == request_id)).scalar_one_or_none()
    if rec is None:
        raise NotFound("رسیدی برای این درخواست ثبت نشده است.")
    return {"issued_at": rec.issued_at.isoformat(), "receipt": __import__("json").loads(rec.receipt_json or "{}")}


@prov_router.get("/queue")
def provider_queue(principal: Principal = Depends(require("rewards:deliver")), db: Session = Depends(get_db)):
    """ACC-06: provider sees ONLY minimal fields of his own requests."""
    provider = db.execute(select(RewardProvider).where(
        RewardProvider.university_id == principal.university_id)).scalars().first()
    if provider is None:
        raise NotFound("ارائه‌دهندهٔ مرتبط یافت نشد.")
    reward_ids = [r.id for r in db.execute(select(Reward).where(Reward.provider_id == provider.id)).scalars().all()]
    rows = db.execute(select(RewardRequest).where(RewardRequest.reward_id.in_(reward_ids or [""]),
                                                  RewardRequest.state.in_(["approved", "fulfilling"]))).scalars().all()
    return {"items": [{"request_ref": r.id, "state": r.state, "requested_at": r.requested_at.isoformat()}
                      for r in rows]}  # minimal fields only (TST-16)


class CallbackIn(BaseModel):
    request_ref: str
    result: str  # confirmed|failed|unknown
    report: dict = {}


@prov_router.post("/{provider_id}/callback")
def callback(provider_id: str, body: CallbackIn, request: Request,
             db: Session = Depends(get_db), principal: Principal = Depends(get_service_principal)):
    """RWD-06: HMAC-signed callback; unknown ⇒ reconciliation (TST-09)."""
    import json as _json

    from ...core.security import verify_hmac
    from .models import RewardProvider as RP

    prov = db.get(RP, provider_id)
    if prov is None or not prov.callback_secret_ref:
        raise NotFound("ارائه‌دهنده یافت نشد.")
    raw = request.state._raw_body if hasattr(request.state, "_raw_body") else b"{}"
    if not verify_hmac(prov.callback_secret_ref, raw, request.headers.get("X-Signature", "")):
        raise NotFound("امضای Callback نامعتبر است.")
    out = rw.provider_callback(db, provider_id=provider_id, request_ref=body.request_ref,
                               result=body.result, report=body.report)
    audit.write(db, actor=f"provider:{provider_id}", action="provider.callback", entity="reward_requests",
                entity_id=body.request_ref, university_id=prov.university_id, after={"result": body.result})
    return out


@prov_router.get("/reconciliation")
def recon_list(principal: Principal = Depends(require("rewards:approve")), db: Session = Depends(get_db)):
    rows = db.execute(select(ReconciliationCase).where(
        ReconciliationCase.university_id == principal.university_id,
        ReconciliationCase.resolution.is_(None))).scalars().all()
    return {"items": [{"id": c.id, "request_id": c.request_id, "detected_at": c.detected_at.isoformat(),
                       "provider_report": c.provider_report} for c in rows]}


@prov_router.post("/reconciliation/{case_id}/resolve")
def recon_resolve(case_id: str, body: dict, principal: Principal = Depends(require("rewards:approve")),
                  db: Session = Depends(get_db)):
    case = db.get(ReconciliationCase, case_id)
    if case is None:
        raise NotFound("پرونده یافت نشد.")
    rw.reconcile(db, case, str(body.get("resolution")), principal.user_id)
    return {"resolution": case.resolution}


@req_router.get("/attempts")
def attempts(principal: Principal = Depends(require("rewards:manage")), db: Session = Depends(get_db)):
    rows = db.execute(select(FulfillmentAttempt).where(
        FulfillmentAttempt.university_id == principal.university_id).order_by(FulfillmentAttempt.created_at.desc()).limit(100)).scalars().all()
    return {"items": [{"id": a.id, "request_id": a.request_id, "state": a.state, "attempt_no": a.attempt_no}
                      for a in rows]}
