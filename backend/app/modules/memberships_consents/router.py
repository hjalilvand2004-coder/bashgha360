"""Memberships + consents endpoints (CLUB-01..07)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...core.errors import NotFound
from ...core.rbac import Principal, require
from ...modules.audit import service as audit
from ..identity_access.models import StudentReference
from .models import Membership
from .service import change_state, current_terms, export_personal_data, join, latest_consents, set_consent

router = APIRouter(prefix="/memberships", tags=["memberships"])
consents_router = APIRouter(prefix="/consents", tags=["consents"])


class JoinIn(BaseModel):
    terms_version_id: str
    consents: dict[str, bool] = Field(default_factory=dict)


@router.get("/terms")
def get_terms(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    terms = current_terms(db, principal.university_id)
    if terms is None:
        raise NotFound("نسخهٔ شرایط فعلی یافت نشد.")
    return {"id": terms.id, "version_no": terms.version_no, "title_fa": terms.title_fa,
            "content_fa": terms.content_fa, "data_policy_fa": terms.data_policy_fa}


@router.post("/join")
def do_join(body: JoinIn, principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        raise NotFound("پروفایل دانشجوی شما یافت نشد.")
    sref = db.get(StudentReference, principal.student_ref_id)
    m = join(db, university_id=principal.university_id, student_ref=sref,
             terms_version_id=body.terms_version_id, consents=body.consents)
    audit.write(db, actor=principal.user_id, action="membership.join", entity="memberships",
                entity_id=m.id, university_id=principal.university_id, after={"state": m.state})
    return {"state": m.state, "membership_no": m.membership_no}


@router.get("/me")
def my_membership(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        return {"state": None}
    m = db.execute(select(Membership).where(Membership.student_ref_id == principal.student_ref_id)).scalar_one_or_none()
    if m is None:
        return {"state": None}
    return {"state": m.state, "membership_no": m.membership_no, "joined_at": m.joined_at,
            "consents": latest_consents(db, m.student_ref_id)}


@router.post("/exit")
def exit_club(body: dict, principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """PRN-04: exit never limits base educational services (TST-10)."""
    m = db.execute(select(Membership).where(Membership.student_ref_id == principal.student_ref_id)).scalar_one_or_none()
    if m is None:
        raise NotFound("عضویتی یافت نشد.")
    change_state(db, m, "left_voluntary", reason_fa=str(body.get("reason_fa", "خروج داوطلبانه")))
    audit.write(db, actor=principal.user_id, action="membership.exit", entity="memberships",
                entity_id=m.id, university_id=principal.university_id)
    return {"state": m.state}


@router.get("/export")
def export_me(principal: Principal = Depends(require("data:export_own")), db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        raise NotFound("پروفایل یافت نشد.")
    return export_personal_data(db, student_ref=db.get(StudentReference, principal.student_ref_id))


class ConsentIn(BaseModel):
    value: bool


@consents_router.patch("/{consent_type}")
def patch_consent(consent_type: str, body: ConsentIn,
                  principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        raise NotFound("پروفایل یافت نشد.")
    rec = set_consent(db, university_id=principal.university_id,
                      student_ref=db.get(StudentReference, principal.student_ref_id),
                      consent_type=consent_type, value=body.value)
    audit.write(db, actor=principal.user_id, action="consent.change", entity="consent_records",
                entity_id=rec.id, after={"type": consent_type, "value": body.value},
                university_id=principal.university_id)
    return {"consent_type": consent_type, "value": rec.value, "decided_at": rec.decided_at}


@consents_router.get("")
def my_consents(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        return {}
    return latest_consents(db, principal.student_ref_id)
