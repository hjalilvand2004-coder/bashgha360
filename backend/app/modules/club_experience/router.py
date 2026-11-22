"""club_experience endpoints — onboarding (شروع ۱۵ دقیقه‌ای)، دعوت دوست، فضای دستاوردها (v1.3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...core.rbac import Principal, require
from . import service as cx

router = APIRouter(prefix="/club-experience", tags=["club-experience"])


class OnboardingIn(BaseModel):
    persona: str
    interests: list[str] = Field(default_factory=list)


class InviteIn(BaseModel):
    mission_id: str
    invitee_contact: str = ""


class StoryIn(BaseModel):
    title_fa: str
    body_fa: str = ""
    kind: str = "build"
    subject_label_fa: str = ""
    has_consent: bool = False
    group_id: str | None = None
    mission_id: str | None = None


@router.get("/onboarding")
def onboarding_state(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """وضعیت شروع فوری: مسیر انتخابی، مأموریت پیشنهادی اول و نشان «اولین قدم»."""
    return cx.get_onboarding_state(db, principal)


@router.post("/onboarding")
def save_onboarding(body: OnboardingIn, principal: Principal = Depends(require("ledger:read_own")),
                    db: Session = Depends(get_db)):
    """ثبت مسیر انتخابی و علاقه‌ها + پیوستن خودکار به مأموریت اول + نشان «اولین قدم»."""
    return cx.save_onboarding(db, principal, body.persona, body.interests)


@router.get("/invites/mine")
def invites_mine(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    return cx.my_invites(db, principal)


@router.post("/invites")
def create_invite(body: InviteIn, principal: Principal = Depends(require("ledger:read_own")),
                  db: Session = Depends(get_db)):
    """دعوت دوست به مأموریت مشترک — فقط برای عضو مأموریت؛ بدون امتیاز جذب."""
    return cx.create_invite(db, principal, body.mission_id, body.invitee_contact)


@router.post("/invites/{code}/accept")
def accept_invite(code: str, principal: Principal = Depends(require("ledger:read_own")),
                  db: Session = Depends(get_db)):
    return cx.accept_invite(db, principal, code)


@router.get("/showcase")
def showcase(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """فضای دستاوردها — روایت‌های کوتاه با رضایت، بدون رتبه‌بندی."""
    return cx.list_stories(db, str(principal.university_id))


@router.post("/showcase")
def create_story(body: StoryIn, principal: Principal = Depends(require("missions:manage")),
                 db: Session = Depends(get_db)):
    return cx.create_story(db, principal, body.title_fa, body.body_fa, body.kind,
                           body.subject_label_fa, body.has_consent, body.group_id, body.mission_id)
