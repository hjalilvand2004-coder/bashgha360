"""policies + approvals + simulations endpoints (PNT, ACC-09/10)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...core.errors import Conflict, Forbidden, NotFound
from ...core.rbac import Principal, require
from ...modules.audit import service as audit
from .models import Policy, PolicyApproval, PolicyVersion, RuleSimulation
from .service import validate_dsl

router = APIRouter(prefix="/policies", tags=["policies"])
approvals_router = APIRouter(prefix="/policy-approvals", tags=["policy-approvals"])
sim_router = APIRouter(prefix="/simulations", tags=["simulations"])


class PolicyIn(BaseModel):
    code: str
    title_fa: str
    exclusive_group: str | None = None
    priority: int = 100


class VersionIn(BaseModel):
    dsl: dict
    effective_from: str
    effective_to: str | None = None
    late_window_hours: int = 72
    change_note_fa: str | None = None


@router.get("")
def list_policies(principal: Principal = Depends(require("policies:read")), db: Session = Depends(get_db)):
    rows = db.execute(select(Policy).where(Policy.university_id == principal.university_id)).scalars().all()
    out = []
    for p in rows:
        versions = db.execute(select(PolicyVersion).where(PolicyVersion.policy_id == p.id)
                              .order_by(PolicyVersion.version_no.desc())).scalars().all()
        out.append({"id": p.id, "code": p.code, "title_fa": p.title_fa, "exclusive_group": p.exclusive_group,
                    "priority": p.priority,
                    "versions": [{"id": v.id, "version_no": v.version_no, "status": v.status,
                                  "effective_from": v.effective_from.isoformat(),
                                  "approved_by": v.approved_by} for v in versions]})
    return {"items": out}


@router.post("")
def create_policy(body: PolicyIn, principal: Principal = Depends(require("policies:write")),
                  db: Session = Depends(get_db)):
    p = Policy(id=__import__("uuid").uuid4().hex, university_id=principal.university_id, code=body.code,
               title_fa=body.title_fa, exclusive_group=body.exclusive_group, priority=body.priority)
    db.add(p)
    db.flush()
    audit.write(db, actor=principal.user_id, action="policy.created", entity="policies", entity_id=p.id,
                university_id=principal.university_id, after={"code": p.code})
    return {"id": p.id}


@router.post("/{policy_id}/versions")
def create_version(policy_id: str, body: VersionIn, principal: Principal = Depends(require("policies:write")),
                   db: Session = Depends(get_db)):
    policy = db.get(Policy, policy_id)
    if policy is None or str(policy.university_id) != principal.university_id:
        raise NotFound("سیاست یافت نشد.")
    spec = validate_dsl(body.dsl)  # allowlisted validation — no eval (PNT-02)
    max_no = db.execute(select(PolicyVersion.version_no).where(PolicyVersion.policy_id == policy_id)
                        .order_by(PolicyVersion.version_no.desc()).limit(1)).scalar() or 0
    v = PolicyVersion(id=__import__("uuid").uuid4().hex, university_id=principal.university_id,
                      policy_id=policy_id, version_no=int(max_no) + 1, status="draft",
                      dsl_json=json.dumps(body.dsl, ensure_ascii=False),
                      effective_from=__import__("datetime").datetime.fromisoformat(body.effective_from),
                      effective_to=__import__("datetime").datetime.fromisoformat(body.effective_to) if body.effective_to else None,
                      late_window_hours=body.late_window_hours, created_by=principal.user_id,
                      change_note_fa=body.change_note_fa)
    db.add(v)
    db.flush()
    return {"id": v.id, "version_no": v.version_no, "status": v.status, "rule_id": spec.rule_id}


@router.post("/versions/{version_id}/submit")
def submit_for_approval(version_id: str, principal: Principal = Depends(require("policies:write")),
                        db: Session = Depends(get_db)):
    v = db.get(PolicyVersion, version_id)
    if v is None or v.status not in ("draft", "simulated"):
        raise Conflict("نسخه در وضعیت قابل ارسال نیست.")
    v.status = "pending_approval"
    return {"status": v.status}


@router.get("/versions/{version_id}/diff")
def version_diff(version_id: str, principal: Principal = Depends(require("policies:read")), db: Session = Depends(get_db)):
    """History + version diff for the policy officer."""
    v = db.get(PolicyVersion, version_id)
    if v is None:
        raise NotFound("نسخه یافت نشد.")
    prev = db.execute(select(PolicyVersion).where(PolicyVersion.policy_id == v.policy_id,
                                                  PolicyVersion.version_no < v.version_no)
                      .order_by(PolicyVersion.version_no.desc()).limit(1)).scalar_one_or_none()
    def _dsl(x):
        return json.loads(x.dsl_json) if x else {}
    import json as _json

    return {"version": {"no": v.version_no, "status": v.status, "dsl": _json.loads(v.dsl_json)},
            "previous": {"no": prev.version_no if prev else None, "dsl": _dsl(prev)},
            "change_note_fa": v.change_note_fa}


class ApprovalIn(BaseModel):
    decision: str  # approve | reject
    comment_fa: str = ""


@approvals_router.post("")
def approve_version(body: ApprovalIn, principal: Principal = Depends(require("policies:approve")),
                    db: Session = Depends(get_db)):
    """ACC-09/10: second approval; requester cannot approve own request."""
    last = db.execute(select(PolicyVersion).where(PolicyVersion.status == "pending_approval")
                      .order_by(PolicyVersion.created_at.desc()).limit(100)).scalars().all()
    if not body.decision:
        raise Conflict("تصمیم لازم است.")
    # The latest pending version for this university:
    candidates = [v for v in last if v.university_id == principal.university_id]
    if not candidates:
        raise NotFound("نسخه‌ای در انتظار تأیید نیست.")
    v = candidates[0]
    if v.created_by == principal.user_id:
        raise Forbidden("درخواست‌دهنده نمی‌تواند همان درخواست حساس را خودش تأیید کند.")
    exists = db.execute(select(PolicyApproval).where(PolicyApproval.version_id == v.id,
                                                     PolicyApproval.approver_user_id == principal.user_id)).scalar_one_or_none()
    if exists:
        raise Conflict("شما قبلاً دربارهٔ این نسخه تصمیم گرفته‌اید.")
    db.add(PolicyApproval(id=__import__("uuid").uuid4().hex, university_id=principal.university_id,
                          version_id=v.id, approver_user_id=principal.user_id, decision=body.decision,
                          comment_fa=body.comment_fa, decided_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)))
    if body.decision == "reject":
        v.status = "draft"
        v.change_note_fa = (v.change_note_fa or "") + f" | رد توسط تأییدکننده: {body.comment_fa}"
    else:
        v.status = "published"
        v.approved_by, v.approved_at = principal.user_id, __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        v.approval_ref = f"PA-{v.id[:8]}"
    audit.write(db, actor=principal.user_id, action=f"policy.{body.decision}", entity="policy_versions",
                entity_id=v.id, university_id=principal.university_id, after={"status": v.status})
    return {"version_id": v.id, "status": v.status}


@approvals_router.get("/pending")
def pending_list(principal: Principal = Depends(require("policies:approve")), db: Session = Depends(get_db)):
    rows = db.execute(select(PolicyVersion).where(PolicyVersion.status == "pending_approval",
                                                  PolicyVersion.university_id == principal.university_id)).scalars().all()
    return {"items": [{"id": v.id, "version_no": v.version_no, "policy_id": v.policy_id,
                       "dsl": json.loads(v.dsl_json), "created_by": v.created_by,
                       "created_at": v.created_at.isoformat()} for v in rows]}


@sim_router.post("")
def simulate(body: dict, principal: Principal = Depends(require("policies:simulate")), db: Session = Depends(get_db)):
    """PNT-07: simulation must never touch the operational ledger."""
    version = db.get(PolicyVersion, str(body.get("version_id", "")))
    if version is None:
        raise NotFound("نسخهٔ سیاست یافت نشد.")
    spec = validate_dsl(json.loads(version.dsl_json))
    from .service import evaluate

    ctx = {"event": {"event_type": spec.event_type, "activity_reference": body.get("activity_reference", "sim"),
                     "occurred_at": body.get("occurred_at", "2026-01-01T08:00:00Z")},
           "payload": body.get("payload", {})}
    matched, cond_res, effective, candidate = evaluate(spec, ctx)
    out = {"matched": matched, "conditions_result": cond_res, "effective_inputs": effective,
           "candidate_points": str(candidate), "note": "شبیه‌سازی؛ بدون اثر بر دفترکل عملیاتی."}
    db.add(RuleSimulation(id=__import__("uuid").uuid4().hex, university_id=principal.university_id,
                          version_id=version.id, input_json=json.dumps(body, ensure_ascii=False),
                          output_json=json.dumps(out, ensure_ascii=False), ran_by=principal.user_id))
    return out
