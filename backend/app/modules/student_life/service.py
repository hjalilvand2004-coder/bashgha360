"""student_life service — منطق چهار وعدهٔ v1.5.

قواعد کلیدی (ارزیابی v1.5):
  - ارزش فوری بدون امتیاز: هیچ مسیر این ماژول امتیاز نمی‌دهد و امتیاز نمی‌گیرد.
  - هم‌پایه: تطبیق با علاقه/زمان اعلام‌شده، بدون برچسب شخصیت؛ خروج امن و گزارش محرمانه.
  - فرصت‌های زنده: پر شدن ظرفیت = صف انتظار شفاف، نه مزیت «امتیاز بیشتر» یا «زودتر کلیک»
    (صف، نخستین گام BL-01؛ قرعه‌کشی شفاف در نوبت بعد).
  - بستهٔ ساخت: صندلی محفوظ تازه‌وارد (cumulative_progress < ۵۰ = زیر سطح «پویا»).
  - صدای دانشجو: رأی برابر؛ مسیر وضعیت دریافت←بررسی←پذیرش/رد←اجرا.
"""
from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.db import utcnow
from ...core.errors import ApiError
from ...core.rbac import Principal
from ..points_ledger.models import PointAccount
from .models import (
    BundleEnrollment,
    Opportunity,
    OpportunityReg,
    PeerActivity,
    PeerParticipant,
    PeerReport,
    PortfolioBundle,
    ProposalVote,
    StudentProposal,
)

NEWCOMER_MAX_PROGRESS = 50.0  # زیر سطح ۲ مسیر یادگیری («پویا») = تازه‌وارد
PEER_KINDS = ("language", "study", "outing", "games", "presentation", "other")
OPP_KINDS = ("visit", "workshop", "game", "talk", "volunteer", "tour", "other")
PROPOSAL_KINDS = ("program", "space", "improvement", "other")
VOICE_FLOW = ("received", "in_review", "accepted", "rejected", "executed")


def _now() -> "datetime":  # noqa: F821
    return utcnow()


# ---------------------------------------------------------------- هم‌پایه

def _peer_active_count(db: Session, activity_id: str) -> int:
    return db.execute(select(func.count()).select_from(PeerParticipant).where(
        PeerParticipant.activity_id == activity_id, PeerParticipant.state == "joined")).scalar_one()


def list_peer_activities(db: Session, university_id: str, sref_id: str | None) -> list[dict]:
    acts = db.execute(select(PeerActivity).where(
        PeerActivity.university_id == university_id,
        PeerActivity.state.in_(("open", "closed"))).order_by(PeerActivity.created_at.desc())).scalars().all()
    mine = {}
    if sref_id:
        for p in db.execute(select(PeerParticipant).where(
                PeerParticipant.student_ref_id == sref_id)).scalars().all():
            mine[p.activity_id] = p
    out = []
    for a in acts:
        active = _peer_active_count(db, a.id)
        p = mine.get(a.id)
        out.append({
            "id": a.id, "title_fa": a.title_fa, "activity_kind": a.activity_kind,
            "time_label_fa": a.time_label_fa, "starts_at": a.starts_at.isoformat() if a.starts_at else None,
            "location_fa": a.location_fa, "capacity": a.capacity, "trial_ok": a.trial_ok,
            "interest_tags": [t for t in a.interest_tags.split(",") if t],
            "state": a.state, "active_count": active, "seats_left": max(0, a.capacity - active),
            "my_state": p.state if p else None, "my_mode": p.mode if p else None,
            "is_host": a.host_student_ref_id == sref_id,
        })
    return out


def create_peer_activity(db: Session, p: Principal, sref_id: str, title_fa: str, activity_kind: str,
                         time_label_fa: str, location_fa: str, capacity: int,
                         trial_ok: bool, interest_tags: list[str], starts_at=None) -> dict:
    if activity_kind not in PEER_KINDS:
        raise ApiError("نوع فعالیت نامعتبر است", status_code=422)
    if capacity < 2 or capacity > 8:
        raise ApiError("جمع کوچک باید بین ۲ تا ۸ نفر باشد", status_code=422)
    open_count = db.execute(select(func.count()).select_from(PeerActivity).where(
        PeerActivity.host_student_ref_id == sref_id, PeerActivity.state == "open")).scalar_one()
    if open_count >= 3:
        raise ApiError("در هر لحظه حداکثر ۳ جمع باز می‌توانید میزبانی کنید", status_code=422)
    a = PeerActivity(university_id=p.university_id, host_student_ref_id=sref_id, title_fa=title_fa,
                     activity_kind=activity_kind, time_label_fa=time_label_fa, starts_at=starts_at,
                     location_fa=location_fa, capacity=capacity, trial_ok=trial_ok,
                     interest_tags=",".join(t.strip() for t in interest_tags if t.strip())[:200],
                     state="open", created_at=_now())
    db.add(a)
    db.flush()
    return {"id": a.id, "state": "open"}


def join_peer_activity(db: Session, p: Principal, sref_id: str, activity_id: str, mode: str) -> dict:
    a = db.execute(select(PeerActivity).where(PeerActivity.id == activity_id,
                                              PeerActivity.university_id == p.university_id)).scalar_one_or_none()
    if a is None or a.state != "open":
        raise ApiError("این جمع باز نیست", status_code=404)
    if mode not in ("trial", "committed"):
        raise ApiError("حالت مشارکت نامعتبر است", status_code=422)
    if mode == "trial" and not a.trial_ok:
        raise ApiError("این جمع امکان شرکت آزمایشی ندارد", status_code=422)
    existing = db.execute(select(PeerParticipant).where(
        PeerParticipant.activity_id == activity_id, PeerParticipant.student_ref_id == sref_id)).scalar_one_or_none()
    if existing and existing.state == "joined":
        raise ApiError("شما قبلاً به این جمع پیوسته‌اید", status_code=409)
    active = _peer_active_count(db, activity_id)
    if active >= a.capacity:
        raise ApiError("ظرفیت این جمع پر است — جمع کوچک‌تر را امتحان کنید", status_code=409)
    if existing:
        existing.state, existing.mode, existing.joined_at = "joined", mode, _now()
        db.flush()
        return {"state": "joined", "mode": mode, "seats_left": max(0, a.capacity - active - 1)}
    db.add(PeerParticipant(university_id=p.university_id, activity_id=activity_id,
                           student_ref_id=sref_id, mode=mode, state="joined", joined_at=_now()))
    db.flush()
    return {"state": "joined", "mode": mode, "seats_left": max(0, a.capacity - active - 1)}


def leave_peer_activity(db: Session, p: Principal, sref_id: str, activity_id: str) -> dict:
    """خروج امن — بدون جریمه، بدون توضیح اجباری؛ میزبانِ فعالیتی که میزبانش است، جمع را می‌بندد."""
    a = db.execute(select(PeerActivity).where(PeerActivity.id == activity_id)).scalar_one_or_none()
    if a is None:
        raise ApiError("جمع یافت نشد", status_code=404)
    part = db.execute(select(PeerParticipant).where(
        PeerParticipant.activity_id == activity_id, PeerParticipant.student_ref_id == sref_id,
        PeerParticipant.state == "joined")).scalar_one_or_none()
    if part is None:
        raise ApiError("عضویت فعالی در این جمع ندارید", status_code=404)
    part.state = "left"
    if a.host_student_ref_id == sref_id:
        a.state = "closed"
    db.flush()
    return {"state": "left"}


def report_peer_activity(db: Session, p: Principal, sref_id: str, activity_id: str, reason_fa: str) -> dict:
    a = db.execute(select(PeerActivity).where(PeerActivity.id == activity_id)).scalar_one_or_none()
    if a is None:
        raise ApiError("جمع یافت نشد", status_code=404)
    r = PeerReport(university_id=p.university_id, activity_id=activity_id,
                   reporter_student_ref_id=sref_id, reason_fa=reason_fa, state="open", created_at=_now())
    db.add(r)
    db.flush()
    return {"id": r.id, "state": "open",
            "note_fa": "گزارش شما فقط برای مدیر باشگاه دیده می‌شود و محرمانه است."}


def list_open_reports(db: Session, university_id: str) -> list[dict]:
    rows = db.execute(select(PeerReport).where(
        PeerReport.university_id == university_id, PeerReport.state == "open").order_by(PeerReport.created_at)).scalars().all()
    out = []
    for r in rows:
        a = db.get(PeerActivity, r.activity_id)
        out.append({"id": r.id, "activity_title_fa": a.title_fa if a else "—",
                    "reason_fa": r.reason_fa, "activity_id": r.activity_id})
    return out


def resolve_peer_report(db: Session, p: Principal, report_id: str, note_fa: str, hide_activity: bool) -> dict:
    r = db.get(PeerReport, report_id)
    if r is None or r.university_id != p.university_id:
        raise ApiError("گزارش یافت نشد", status_code=404)
    r.state, r.resolution_note_fa = "resolved", note_fa
    if hide_activity:
        a = db.get(PeerActivity, r.activity_id)
        if a:
            a.state = "hidden"
    db.flush()
    return {"id": r.id, "state": "resolved"}


def my_peer_state(db: Session, p: Principal, sref_id: str) -> dict:
    joined = db.execute(select(PeerParticipant).where(
        PeerParticipant.student_ref_id == sref_id, PeerParticipant.state == "joined")).scalars().all()
    items = []
    for part in joined:
        a = db.get(PeerActivity, part.activity_id)
        if a and a.state == "open":
            items.append({"activity_id": a.id, "title_fa": a.title_fa, "time_label_fa": a.time_label_fa,
                          "location_fa": a.location_fa, "mode": part.mode})
    return {"items": items}


# --------------------------------------- همین هفته در دانشگاه

def list_opportunities(db: Session, university_id: str, sref_id: str | None,
                       free_only: bool = False, solo_only: bool = False, short_only: bool = False) -> list[dict]:
    horizon = _now() + timedelta(days=14)
    q = select(Opportunity).where(
        Opportunity.university_id == university_id, Opportunity.state == "published",
        Opportunity.starts_at >= _now(), Opportunity.starts_at <= horizon).order_by(Opportunity.starts_at)
    if free_only:
        q = q.where(Opportunity.is_free.is_(True))
    if solo_only:
        q = q.where(Opportunity.solo_friendly.is_(True))
    if short_only:
        q = q.where(Opportunity.duration_minutes <= 90)  # بین دو کلاس
    regs = {}
    if sref_id:
        for r in db.execute(select(OpportunityReg).where(
                OpportunityReg.student_ref_id == sref_id,
                OpportunityReg.state.in_(("registered", "waitlisted")))).scalars().all():
            regs[r.opportunity_id] = r
    out = []
    for o in db.execute(q).scalars().all():
        confirmed = db.execute(select(func.count()).select_from(OpportunityReg).where(
            OpportunityReg.opportunity_id == o.id, OpportunityReg.state == "registered")).scalar_one()
        waiting = db.execute(select(func.count()).select_from(OpportunityReg).where(
            OpportunityReg.opportunity_id == o.id, OpportunityReg.state == "waitlisted")).scalar_one()
        r = regs.get(o.id)
        out.append({
            "id": o.id, "title_fa": o.title_fa, "what_fa": o.what_fa, "location_fa": o.location_fa,
            "starts_at": o.starts_at.isoformat(), "duration_minutes": o.duration_minutes,
            "cost_label_fa": o.cost_label_fa, "is_free": o.is_free, "prereq_fa": o.prereq_fa,
            "solo_friendly": o.solo_friendly, "kind": o.kind,
            "capacity": o.capacity, "confirmed_count": confirmed, "seats_left": max(0, o.capacity - confirmed),
            "waitlist_count": waiting, "my_state": r.state if r else None,
        })
    return out


def register_opportunity(db: Session, p: Principal, sref_id: str, opportunity_id: str) -> dict:
    o = db.execute(select(Opportunity).where(Opportunity.id == opportunity_id,
                                             Opportunity.university_id == p.university_id)).scalar_one_or_none()
    if o is None or o.state != "published" or o.starts_at < _now():
        raise ApiError("این فرصت قابل ثبت‌نام نیست", status_code=404)
    existing = db.execute(select(OpportunityReg).where(
        OpportunityReg.opportunity_id == opportunity_id,
        OpportunityReg.student_ref_id == sref_id,
        OpportunityReg.state.in_(("registered", "waitlisted")))).scalar_one_or_none()
    if existing:
        raise ApiError("شما قبلاً برای این فرصت ثبت‌نام کرده‌اید", status_code=409)
    confirmed = db.execute(select(func.count()).select_from(OpportunityReg).where(
        OpportunityReg.opportunity_id == opportunity_id, OpportunityReg.state == "registered")).scalar_one()
    max_pos = db.execute(select(func.max(OpportunityReg.position_no)).where(
        OpportunityReg.opportunity_id == opportunity_id)).scalar_one() or 0
    if confirmed < o.capacity:
        reg = OpportunityReg(university_id=p.university_id, opportunity_id=opportunity_id,
                             student_ref_id=sref_id, position_no=max_pos + 1, state="registered", created_at=_now())
        db.add(reg)
        db.flush()
        return {"state": "registered", "seats_left": max(0, o.capacity - confirmed - 1)}
    reg = OpportunityReg(university_id=p.university_id, opportunity_id=opportunity_id,
                         student_ref_id=sref_id, position_no=max_pos + 1, state="waitlisted", created_at=_now())
    db.add(reg)
    db.flush()
    return {"state": "waitlisted",
            "note_fa": "ظرفیت پر شده است؛ در صف انتظار شفاف قرار گرفتید — اگر جایی باز شود، به‌ترتیب صف جا می‌گیرید."}


def cancel_opportunity_reg(db: Session, p: Principal, sref_id: str, opportunity_id: str) -> dict:
    reg = db.execute(select(OpportunityReg).where(
        OpportunityReg.opportunity_id == opportunity_id, OpportunityReg.student_ref_id == sref_id,
        OpportunityReg.state.in_(("registered", "waitlisted")))).scalar_one_or_none()
    if reg is None:
        raise ApiError("ثبت‌نامی برای لغو وجود ندارد", status_code=404)
    reg.state = "cancelled"
    # ارتقای سرِ صف انتظار — شفاف و به‌ترتیب ورود، بدون هیچ رابطه‌ای به امتیاز
    nxt = db.execute(select(OpportunityReg).where(
        OpportunityReg.opportunity_id == opportunity_id, OpportunityReg.state == "waitlisted").order_by(
        OpportunityReg.position_no).limit(1)).scalar_one_or_none()
    promoted = False
    if nxt:
        confirmed = db.execute(select(func.count()).select_from(OpportunityReg).where(
            OpportunityReg.opportunity_id == opportunity_id, OpportunityReg.state == "registered")).scalar_one()
        o = db.get(Opportunity, opportunity_id)
        if o and confirmed < o.capacity:
            nxt.state = "registered"
            promoted = True
    db.flush()
    return {"state": "cancelled", "promoted_next": promoted}


def my_opportunities(db: Session, sref_id: str) -> dict:
    regs = db.execute(select(OpportunityReg).where(
        OpportunityReg.student_ref_id == sref_id,
        OpportunityReg.state.in_(("registered", "waitlisted"))).order_by(OpportunityReg.created_at)).scalars().all()
    items = []
    for r in regs:
        o = db.get(Opportunity, r.opportunity_id)
        if o:
            items.append({"opportunity_id": o.id, "title_fa": o.title_fa, "starts_at": o.starts_at.isoformat(),
                          "location_fa": o.location_fa, "my_state": r.state})
    return {"items": items}


# --------------------------------------- بستهٔ ساخت نمونه‌کار

def _bundle_progress(db: Session, sref_id: str) -> float:
    acc = db.execute(select(PointAccount).where(PointAccount.student_ref_id == sref_id)).scalar_one_or_none()
    return float(acc.cumulative_progress) if acc else 0.0


def _bundle_counts(db: Session, bundle_id: str) -> tuple[int, int]:
    active = db.execute(select(func.count()).select_from(BundleEnrollment).where(
        BundleEnrollment.bundle_id == bundle_id, BundleEnrollment.state.in_(("active", "completed")))).scalar_one()
    newcomer = db.execute(select(func.count()).select_from(BundleEnrollment).where(
        BundleEnrollment.bundle_id == bundle_id, BundleEnrollment.is_newcomer_seat.is_(True),
        BundleEnrollment.state.in_(("active", "completed")))).scalar_one()
    return active, newcomer


def list_bundles(db: Session, university_id: str, sref_id: str | None) -> list[dict]:
    rows = db.execute(select(PortfolioBundle).where(
        PortfolioBundle.university_id == university_id, PortfolioBundle.state == "published").order_by(
        PortfolioBundle.created_at.desc())).scalars().all()
    mine = {}
    if sref_id:
        for e in db.execute(select(BundleEnrollment).where(BundleEnrollment.student_ref_id == sref_id)).scalars().all():
            mine[e.bundle_id] = e
    out = []
    for b in rows:
        active, newcomer = _bundle_counts(db, b.id)
        e = mine.get(b.id)
        out.append({
            "id": b.id, "title_fa": b.title_fa, "output_fa": b.output_fa, "tools_fa": b.tools_fa,
            "guide_fa": b.guide_fa, "feedback_note_fa": b.feedback_note_fa,
            "steps": json.loads(b.steps_json), "estimated_hours": b.estimated_hours,
            "capacity": b.capacity, "seats_left": max(0, b.capacity - active),
            "newcomer_seats_left": max(0, b.newcomer_seats - newcomer),
            "my_state": e.state if e else None, "my_steps_done": json.loads(e.steps_done_json) if e else [],
            "my_output_url": e.output_url if e else None,
            "my_output_verified": e.output_verified if e else False,
        })
    return out


def enroll_bundle(db: Session, p: Principal, sref_id: str, bundle_id: str, use_newcomer_seat: bool) -> dict:
    b = db.execute(select(PortfolioBundle).where(PortfolioBundle.id == bundle_id,
                                                 PortfolioBundle.university_id == p.university_id)).scalar_one_or_none()
    if b is None or b.state != "published":
        raise ApiError("این بسته فعال نیست", status_code=404)
    existing = db.execute(select(BundleEnrollment).where(
        BundleEnrollment.bundle_id == bundle_id, BundleEnrollment.student_ref_id == sref_id)).scalar_one_or_none()
    if existing and existing.state != "left":
        raise ApiError("شما قبلاً در این بسته ثبت‌نام کرده‌اید", status_code=409)
    active, newcomer = _bundle_counts(db, bundle_id)
    if active >= b.capacity:
        raise ApiError("ظرفیت بسته پر است", status_code=409)
    seat = False
    if use_newcomer_seat:
        if newcomer >= b.newcomer_seats:
            raise ApiError("صندلی‌های تازه‌وارد پر شده است", status_code=409)
        if _bundle_progress(db, sref_id) >= NEWCOMER_MAX_PROGRESS:
            raise ApiError("صندلی تازه‌وارد برای دانشجویانی است که هنوز پیشرفت تجمعی کمتری دارند", status_code=403)
        seat = True
    if existing:  # بازگشت بعد از ترک — دوباره با قواعد ظرفیت
        existing.state = "active"
        existing.is_newcomer_seat = seat
        db.flush()
        return {"state": "active", "is_newcomer_seat": seat}
    db.add(BundleEnrollment(university_id=p.university_id, bundle_id=bundle_id, student_ref_id=sref_id,
                            is_newcomer_seat=seat, steps_done_json="[]", state="active", created_at=_now()))
    db.flush()
    return {"state": "active", "is_newcomer_seat": seat}


def toggle_bundle_step(db: Session, p: Principal, sref_id: str, bundle_id: str, step_index: int) -> dict:
    e = db.execute(select(BundleEnrollment).where(
        BundleEnrollment.bundle_id == bundle_id, BundleEnrollment.student_ref_id == sref_id,
        BundleEnrollment.state == "active")).scalar_one_or_none()
    if e is None:
        raise ApiError("ثبت‌نام فعالی در این بسته ندارید", status_code=404)
    b = db.get(PortfolioBundle, bundle_id)
    steps = json.loads(b.steps_json) if b else []
    if step_index < 0 or step_index >= len(steps):
        raise ApiError("مرحله نامعتبر است", status_code=422)
    done = json.loads(e.steps_done_json)
    if step_index in done:
        done.remove(step_index)
    else:
        done.append(step_index)
    e.steps_done_json = json.dumps(sorted(done))
    db.flush()
    return {"steps_done": sorted(done), "total_steps": len(steps)}


def submit_bundle_output(db: Session, p: Principal, sref_id: str, bundle_id: str, output_url: str) -> dict:
    e = db.execute(select(BundleEnrollment).where(
        BundleEnrollment.bundle_id == bundle_id, BundleEnrollment.student_ref_id == sref_id,
        BundleEnrollment.state == "active")).scalar_one_or_none()
    if e is None:
        raise ApiError("ثبت‌نام فعالی در این بسته ندارید", status_code=404)
    e.output_url = output_url
    db.flush()
    return {"output_url": output_url,
            "note_fa": "خروجی ثبت شد؛ پس از بازخورد راهنما وضعیت «تأییدشده» می‌گیرد."}


def verify_bundle_output(db: Session, p: Principal, enrollment_id: str) -> dict:
    e = db.get(BundleEnrollment, enrollment_id)
    if e is None or e.university_id != p.university_id:
        raise ApiError("ثبت‌نام یافت نشد", status_code=404)
    if not e.output_url:
        raise ApiError("هنوز خروجی‌ای ثبت نشده است", status_code=422)
    e.output_verified = True
    e.state = "completed"
    db.flush()
    return {"id": e.id, "state": "completed", "output_verified": True}


def my_bundles(db: Session, sref_id: str) -> dict:
    rows = db.execute(select(BundleEnrollment).where(
        BundleEnrollment.student_ref_id == sref_id, BundleEnrollment.state.in_(("active", "completed")))).scalars().all()
    items = []
    for e in rows:
        b = db.get(PortfolioBundle, e.bundle_id)
        if b:
            items.append({"bundle_id": b.id, "title_fa": b.title_fa, "output_fa": b.output_fa,
                          "steps_done": json.loads(e.steps_done_json), "total_steps": len(json.loads(b.steps_json)),
                          "output_url": e.output_url, "output_verified": e.output_verified, "state": e.state})
    return {"items": items}


# --------------------------------------- صدای دانشجو

def list_proposals(db: Session, university_id: str, sref_id: str | None) -> list[dict]:
    rows = db.execute(select(StudentProposal).where(
        StudentProposal.university_id == university_id).order_by(StudentProposal.created_at.desc())).scalars().all()
    voted = set()
    if sref_id:
        voted = {v.proposal_id for v in db.execute(select(ProposalVote).where(
            ProposalVote.student_ref_id == sref_id)).scalars().all()}
    out = []
    for pr in rows:
        votes = db.execute(select(func.count()).select_from(ProposalVote).where(
            ProposalVote.proposal_id == pr.id)).scalar_one()
        out.append({"id": pr.id, "title_fa": pr.title_fa, "body_fa": pr.body_fa, "support_fa": pr.support_fa,
                    "kind": pr.kind, "state": pr.state, "decision_note_fa": pr.decision_note_fa,
                    "vote_count": votes, "my_vote": pr.id in voted,
                    "is_mine": pr.author_student_ref_id == sref_id,
                    "created_at": pr.created_at.isoformat()})
    return out


def create_proposal(db: Session, p: Principal, sref_id: str, title_fa: str, body_fa: str,
                    support_fa: str, kind: str) -> dict:
    if kind not in PROPOSAL_KINDS:
        raise ApiError("نوع پیشنهاد نامعتبر است", status_code=422)
    pr = StudentProposal(university_id=p.university_id, author_student_ref_id=sref_id, title_fa=title_fa,
                         body_fa=body_fa, support_fa=support_fa, kind=kind, state="received", created_at=_now())
    db.add(pr)
    db.flush()
    return {"id": pr.id, "state": "received"}


def toggle_proposal_vote(db: Session, p: Principal, sref_id: str, proposal_id: str) -> dict:
    pr = db.execute(select(StudentProposal).where(StudentProposal.id == proposal_id,
                                                  StudentProposal.university_id == p.university_id)).scalar_one_or_none()
    if pr is None:
        raise ApiError("پیشنهاد یافت نشد", status_code=404)
    v = db.execute(select(ProposalVote).where(ProposalVote.proposal_id == proposal_id,
                                              ProposalVote.student_ref_id == sref_id)).scalar_one_or_none()
    if v:
        db.delete(v)
        db.flush()
        votes = db.execute(select(func.count()).select_from(ProposalVote).where(
            ProposalVote.proposal_id == proposal_id)).scalar_one()
        return {"voted": False, "vote_count": votes}
    db.add(ProposalVote(university_id=p.university_id, proposal_id=proposal_id,
                        student_ref_id=sref_id, created_at=_now()))
    db.flush()
    votes = db.execute(select(func.count()).select_from(ProposalVote).where(
        ProposalVote.proposal_id == proposal_id)).scalar_one()
    return {"voted": True, "vote_count": votes}


_DECISION_FLOW = {"received": {"in_review"}, "in_review": {"accepted", "rejected"}, "accepted": {"executed"}}


def decide_proposal(db: Session, p: Principal, proposal_id: str, state: str, note_fa: str) -> dict:
    pr = db.execute(select(StudentProposal).where(StudentProposal.id == proposal_id,
                                                  StudentProposal.university_id == p.university_id)).scalar_one_or_none()
    if pr is None:
        raise ApiError("پیشنهاد یافت نشد", status_code=404)
    if state not in VOICE_FLOW or state not in _DECISION_FLOW.get(pr.state, set()):
        raise ApiError(f"گذار وضعیت مجاز نیست: {pr.state} → {state}", status_code=422)
    pr.state = state
    pr.decision_note_fa = note_fa
    pr.decided_at = _now()
    db.flush()
    return {"id": pr.id, "state": pr.state}


# --------------------------------------- خانهٔ نو (چهار وعده)

def home_feed(db: Session, p: Principal, sref_id: str | None) -> dict:
    """سه پیشنهاد مناسب همین هفته + چیزهایی که شروع کرده‌ای + ایده‌بخشِ اثر من."""
    opps = list_opportunities(db, p.university_id, sref_id)[:3]
    peers = [a for a in list_peer_activities(db, p.university_id, sref_id) if a["state"] == "open"][:3]
    bundles = list_bundles(db, p.university_id, sref_id)[:2]
    return {
        "suggestions": {
            "opportunities": opps, "peer_activities": peers, "bundles": bundles,
        },
        "in_progress": {
            "peer": my_peer_state(db, p, sref_id)["items"] if sref_id else [],
            "bundles": my_bundles(db, sref_id)["items"] if sref_id else [],
            "opportunities": my_opportunities(db, sref_id)["items"] if sref_id else [],
        },
        "voice": {"note_fa": "ایده‌ات را پیشنهاد بده؛ وضعیتش را تا اجرا می‌توانی دنبال کنی."},
    }
