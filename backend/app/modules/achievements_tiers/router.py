"""tiers + badges + missions + groups endpoints (ACH, MIS/CLUB-05)."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...core.errors import Conflict, NotFound
from ...core.rbac import Principal, require
from ...modules.memberships_consents import service as memberships
from ...modules.identity_access.models import StudentReference
from ..club_experience import service as cx_service
from . import service as ach
from .models import BadgeAward, BadgeDefinition, BadgeShare, TierAward, TierDefinition
from ..missions_groups.models import (GroupContribution, GroupMember, LearningGroup, Mission,
                                      MissionParticipation)

router = APIRouter(prefix="/tiers", tags=["tiers"])
badges_router = APIRouter(prefix="/badges", tags=["badges"])
missions_router = APIRouter(prefix="/missions", tags=["missions"])
groups_router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("/me")
def my_tiers(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        return {"paths": []}
    out = []
    for path in ("learning", "skill", "collaboration"):
        tds = db.execute(select(TierDefinition).where(
            TierDefinition.university_id == principal.university_id, TierDefinition.path == path)
            .order_by(TierDefinition.level_no)).scalars().all()
        awards = db.execute(select(TierAward).where(TierAward.student_ref_id == principal.student_ref_id)).scalars().all()
        have = {a.tier_id for a in awards}
        progress = ach.progress_for_path(db, principal.student_ref_id, path)
        out.append({"path": path, "progress": progress,
                    "tiers": [{"level_no": t.level_no, "title_fa": t.title_fa,
                               "min_progress": float(t.min_progress), "achieved": t.id in have} for t in tds]})
    return {"paths": out}


@badges_router.get("/me")
def my_badges(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        return {"items": []}
    rows = db.execute(select(BadgeAward).where(BadgeAward.student_ref_id == principal.student_ref_id)
                      .order_by(BadgeAward.issued_at.desc())).scalars().all()
    out = []
    for a in rows:
        b = db.get(BadgeDefinition, a.badge_id)
        share = db.execute(select(BadgeShare).where(BadgeShare.badge_award_id == a.id,
                                                    BadgeShare.revoked_at.is_(None))).scalar_one_or_none()
        out.append({"id": a.id, "title_fa": b.title_fa if b else "", "svg_id": b.svg_id if b else "badge-learning",
                    "path": b.path if b else "learning", "issuer_fa": b.issuer_fa if b else "",
                    "story_fa": b.story_fa if b else "",
                    "issued_at": a.issued_at.isoformat(), "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                    "state": a.state, "reason_fa": a.reason_fa,
                    "share_token": share.share_token if share else None,
                    "note": "نشان باشگاه مدرک رسمی مهارت نیست."})
    return {"items": out}


class ShareIn(BaseModel):
    badge_award_id: str
    hours: int = 720


@badges_router.post("/share")
def share_badge(body: ShareIn, principal: Principal = Depends(require("ledger:read_own")),
                db: Session = Depends(get_db)):
    """ACH-03: requires explicit public_badge consent; token revocable & expirable."""
    award = db.get(BadgeAward, body.badge_award_id)
    if award is None or award.student_ref_id != principal.student_ref_id:
        raise NotFound("نشان یافت نشد.")
    consent_ok = memberships.has_consent(db, principal.student_ref_id, "public_badge")
    share = ach.create_share(db, award=award, by_user=principal.user_id, consent_ok=consent_ok)
    return {"share_token": share.share_token, "expires_at": share.expires_at.isoformat()}


@badges_router.post("/{badge_award_id}/revoke-share")
def revoke_share(badge_award_id: str, principal: Principal = Depends(require("ledger:read_own")),
                 db: Session = Depends(get_db)):
    shares = db.execute(select(BadgeShare).where(BadgeShare.badge_award_id == badge_award_id,
                                                 BadgeShare.revoked_at.is_(None))).scalars().all()
    for s in shares:
        s.revoked_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    return {"revoked": len(shares)}


class MissionIn(BaseModel):
    title_fa: str
    description_fa: str = ""
    goal_type: str = "skill"
    activities: list = []
    starts_at: str
    ends_at: str
    max_points: str = "0"
    is_group: bool = False
    mission_kind: str = "standard"
    output_fa: str = ""
    duration_label_fa: str = ""
    team_size_hint: str = ""
    interest_tags: str = ""


@missions_router.get("")
def list_missions(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    rows = db.execute(select(Mission).where(Mission.university_id == principal.university_id,
                                            Mission.state == "active")).scalars().all()
    parts = []
    if principal.student_ref_id:
        parts = db.execute(select(MissionParticipation).where(
            MissionParticipation.student_ref_id == principal.student_ref_id)).scalars().all()
    joined = {p.mission_id: p.state for p in parts}
    return {"items": [{"id": m.id, "title_fa": m.title_fa, "description_fa": m.description_fa,
                       "goal_type": m.goal_type, "activities": json.loads(m.activities_json or "[]"),
                       "starts_at": m.starts_at.isoformat(), "ends_at": m.ends_at.isoformat(),
                       "is_group": m.is_group, "my_state": joined.get(m.id),
                       "mission_kind": m.mission_kind,
                       "kind_label_fa": cx_service.MISSION_KIND_LABELS.get(m.mission_kind, "مأموریت"),
                       "output_fa": m.output_fa, "duration_label_fa": m.duration_label_fa,
                       "team_size_hint": m.team_size_hint, "interest_tags": m.interest_tags} for m in rows]}


@missions_router.post("")
def create_mission(body: MissionIn, principal: Principal = Depends(require("missions:manage")),
                   db: Session = Depends(get_db)):
    m = Mission(id=str(uuid.uuid4()), university_id=principal.university_id, title_fa=body.title_fa,
                description_fa=body.description_fa, goal_type=body.goal_type,
                activities_json=json.dumps(body.activities, ensure_ascii=False),
                starts_at=__import__("datetime").datetime.fromisoformat(body.starts_at),
                ends_at=__import__("datetime").datetime.fromisoformat(body.ends_at),
                max_points=body.max_points, is_group=body.is_group,
                mission_kind=body.mission_kind, output_fa=body.output_fa[:300],
                duration_label_fa=body.duration_label_fa[:40], team_size_hint=body.team_size_hint[:40],
                interest_tags=body.interest_tags[:200])
    db.add(m)
    db.flush()
    return {"id": m.id}


@missions_router.post("/{mission_id}/join")
def join_mission(mission_id: str, principal: Principal = Depends(require("ledger:read_own")),
                 db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        raise NotFound("پروفایل یافت نشد.")
    m = db.get(Mission, mission_id)
    if m is None:
        raise NotFound("مأموریت یافت نشد.")
    exists = db.execute(select(MissionParticipation).where(
        MissionParticipation.mission_id == mission_id,
        MissionParticipation.student_ref_id == principal.student_ref_id)).scalar_one_or_none()
    if exists:
        raise Conflict("قبلاً به این مأموریت پیوسته‌اید.")
    p = MissionParticipation(id=str(uuid.uuid4()), university_id=principal.university_id,
                             mission_id=mission_id, student_ref_id=principal.student_ref_id,
                             state="active", joined_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    db.add(p)
    db.flush()
    return {"state": p.state}


@missions_router.post("/{mission_id}/quit")
def quit_mission(mission_id: str, principal: Principal = Depends(require("ledger:read_own")),
                 db: Session = Depends(get_db)):
    """CLUB-05: leaving a mission has NO penalty."""
    p = db.execute(select(MissionParticipation).where(
        MissionParticipation.mission_id == mission_id,
        MissionParticipation.student_ref_id == principal.student_ref_id)).scalar_one_or_none()
    if p is None:
        raise NotFound("مشارکتی یافت نشد.")
    p.state, p.ended_at = "quit", __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    return {"state": p.state, "note": "خروج از مأموریت بدون هیچ تنبیهی است."}


@groups_router.get("")
def list_groups(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """گروه‌های علاقه‌ای با هدف/زمان/خروجی روشن — «یک هفته، سه نفر، یک ایدهٔ قابل‌ارائه»."""
    rows = db.execute(select(LearningGroup).where(LearningGroup.university_id == principal.university_id,
                                                  LearningGroup.state == "active")).scalars().all()
    mine: set[str] = set()
    if principal.student_ref_id:
        mine = {gm.group_id for gm in db.execute(select(GroupMember).where(
            GroupMember.student_ref_id == principal.student_ref_id)).scalars().all()}
    out = []
    for g in rows:
        members = db.execute(select(GroupMember).where(GroupMember.group_id == g.id)).scalars().all()
        mission = db.get(Mission, g.mission_id) if g.mission_id else None
        out.append({"id": g.id, "title_fa": g.title_fa, "capacity": g.capacity,
                    "member_count": len(members), "my_state": "member" if g.id in mine else None,
                    "interest_tag": g.interest_tag, "goal_fa": g.goal_fa,
                    "expected_output_fa": g.expected_output_fa, "duration_label_fa": g.duration_label_fa,
                    "mission_title_fa": mission.title_fa if mission else None})
    return {"items": out}


@groups_router.post("")
def create_group(body: dict, principal: Principal = Depends(require("missions:manage")), db: Session = Depends(get_db)):
    g = LearningGroup(id=str(uuid.uuid4()), university_id=principal.university_id,
                      mission_id=body.get("mission_id"), title_fa=body["title_fa"],
                      capacity=body.get("capacity"), interest_tag=body.get("interest_tag", "")[:60],
                      goal_fa=body.get("goal_fa", "")[:300], expected_output_fa=body.get("expected_output_fa", "")[:300],
                      duration_label_fa=body.get("duration_label_fa", "")[:60])
    db.add(g)
    db.flush()
    return {"id": g.id}


@groups_router.post("/{group_id}/members")
def join_group(group_id: str, principal: Principal = Depends(require("ledger:read_own")),
               db: Session = Depends(get_db)):
    """ACH-06: group membership requires the member's consent timestamp."""
    g = db.get(LearningGroup, group_id)
    if g is None:
        raise NotFound("گروه یافت نشد.")
    gm = GroupMember(id=str(uuid.uuid4()), university_id=principal.university_id, group_id=group_id,
                     student_ref_id=principal.student_ref_id,
                     consent_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    db.add(gm)
    db.flush()
    return {"joined": True}


@groups_router.post("/{group_id}/contributions")
def add_contribution(group_id: str, body: dict, principal: Principal = Depends(require("approvals:verify")),
                     db: Session = Depends(get_db)):
    """Approved contribution with dedupe key (ACH-06: no repeated points)."""
    c = GroupContribution(id=str(uuid.uuid4()), university_id=principal.university_id, group_id=group_id,
                          student_ref_id=body["student_ref_id"], activity_key=body["activity_key"],
                          share_note_fa=body.get("share_note_fa", ""), approved_by=principal.user_id)
    db.add(c)
    db.flush()
    return {"id": c.id}
