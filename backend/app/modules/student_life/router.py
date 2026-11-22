"""student_life endpoints — چهار وعدهٔ v1.5: هم‌پایه، همین هفته در دانشگاه،
بستهٔ ساخت نمونه‌کار، صدای دانشجو. همه بدون امتیاز؛ ورود با مجوز پایهٔ دانشجو."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...core.rbac import Principal, require
from . import service as sl

router = APIRouter(prefix="/student-life", tags=["student-life"])


# ---------- هم‌پایه ----------

class PeerActivityIn(BaseModel):
    title_fa: str
    activity_kind: str = "other"
    time_label_fa: str
    location_fa: str
    capacity: int = 4
    trial_ok: bool = True
    interest_tags: list[str] = Field(default_factory=list)
    starts_at: datetime | None = None


class JoinIn(BaseModel):
    mode: str = "trial"  # trial|committed


class ReportIn(BaseModel):
    reason_fa: str


class ResolveIn(BaseModel):
    resolution_note_fa: str
    hide_activity: bool = False


@router.get("/peer-up")
def peer_activities(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """جمع‌های کوچک هم‌علاقه‌ای — همراهِ یک فعالیت مشخص، بدون الزام به پروژه."""
    return {"items": sl.list_peer_activities(db, str(principal.university_id), principal.student_ref_id)}


@router.post("/peer-up")
def create_peer_activity(body: PeerActivityIn, principal: Principal = Depends(require("ledger:read_own")),
                         db: Session = Depends(get_db)):
    """میزبانی یک جمع کوچک — محل عمومی دانشگاه، ۲ تا ۸ نفر، شرکت آزمایشی اختیاری."""
    return sl.create_peer_activity(db, principal, str(principal.student_ref_id), body.title_fa,
                                   body.activity_kind, body.time_label_fa, body.location_fa,
                                   body.capacity, body.trial_ok, body.interest_tags, body.starts_at)


@router.get("/peer-up/mine")
def my_peer_state(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    return sl.my_peer_state(db, principal, str(principal.student_ref_id))


@router.post("/peer-up/{activity_id}/join")
def join_peer_activity(activity_id: str, body: JoinIn,
                       principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    return sl.join_peer_activity(db, principal, str(principal.student_ref_id), activity_id, body.mode)


@router.post("/peer-up/{activity_id}/leave")
def leave_peer_activity(activity_id: str, principal: Principal = Depends(require("ledger:read_own")),
                        db: Session = Depends(get_db)):
    """خروج امن — بدون جریمه و بدون توضیح اجباری."""
    return sl.leave_peer_activity(db, principal, str(principal.student_ref_id), activity_id)


@router.post("/peer-up/{activity_id}/report")
def report_peer_activity(activity_id: str, body: ReportIn,
                         principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """گزارش مزاحمت — فقط مدیر باشگاه می‌بیند؛ هیچ پیام خصوصی‌ای در سامانه وجود ندارد."""
    return sl.report_peer_activity(db, principal, str(principal.student_ref_id), activity_id, body.reason_fa)


@router.get("/peer-reports")
def open_reports(principal: Principal = Depends(require("missions:manage")), db: Session = Depends(get_db)):
    return {"items": sl.list_open_reports(db, str(principal.university_id))}


@router.post("/peer-reports/{report_id}/resolve")
def resolve_report(report_id: str, body: ResolveIn,
                   principal: Principal = Depends(require("missions:manage")), db: Session = Depends(get_db)):
    return sl.resolve_peer_report(db, principal, report_id, body.resolution_note_fa, body.hide_activity)


# ---------- همین هفته در دانشگاه ----------

@router.get("/week")
def opportunities(free: bool = False, solo: bool = False, short: bool = False,
                  principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """فرصت‌های زندهٔ ۱۴ روز آینده — فقط اطلاعات تصمیم‌گیری: چه/کجا/کی/هزینه/پیش‌نیاز."""
    return {"items": sl.list_opportunities(db, str(principal.university_id), principal.student_ref_id,
                                           free_only=free, solo_only=solo, short_only=short)}


@router.get("/week/mine")
def my_opportunities(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    return sl.my_opportunities(db, str(principal.student_ref_id))


@router.post("/week/{opportunity_id}/register")
def register_opportunity(opportunity_id: str,
                         principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """ثبت‌نام بدون امتیاز — پر شدن ظرفیت یعنی صف انتظار شفاف، نه رقابت امتیازی."""
    return sl.register_opportunity(db, principal, str(principal.student_ref_id), opportunity_id)


@router.post("/week/{opportunity_id}/cancel")
def cancel_opportunity_reg(opportunity_id: str,
                           principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    return sl.cancel_opportunity_reg(db, principal, str(principal.student_ref_id), opportunity_id)


# ---------- بستهٔ ساخت نمونه‌کار ----------

@router.get("/bundles")
def bundles(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """«از صفر تا چیزی که بتوانم نشان بدهم» — ابزار + راهنما + بازخورد + خروجی."""
    return {"items": sl.list_bundles(db, str(principal.university_id), principal.student_ref_id)}


@router.get("/bundles/mine")
def my_bundles(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    return sl.my_bundles(db, str(principal.student_ref_id))


class EnrollIn(BaseModel):
    use_newcomer_seat: bool = False


@router.post("/bundles/{bundle_id}/enroll")
def enroll_bundle(bundle_id: str, body: EnrollIn,
                  principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    return sl.enroll_bundle(db, principal, str(principal.student_ref_id), bundle_id, body.use_newcomer_seat)


class StepIn(BaseModel):
    step_index: int


@router.post("/bundles/{bundle_id}/steps")
def toggle_bundle_step(bundle_id: str, body: StepIn,
                       principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    return sl.toggle_bundle_step(db, principal, str(principal.student_ref_id), bundle_id, body.step_index)


class OutputIn(BaseModel):
    output_url: str


@router.post("/bundles/{bundle_id}/output")
def submit_bundle_output(bundle_id: str, body: OutputIn,
                         principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    return sl.submit_bundle_output(db, principal, str(principal.student_ref_id), bundle_id, body.output_url)


@router.post("/bundle-enrollments/{enrollment_id}/verify")
def verify_bundle_output(enrollment_id: str,
                         principal: Principal = Depends(require("missions:manage")), db: Session = Depends(get_db)):
    """تأیید خروجی راهنما/مدیر — نشان «اولین قدم» جدا از این دستاورد نمایش داده می‌شود."""
    return sl.verify_bundle_output(db, principal, enrollment_id)


# ---------- صدای دانشجو ----------

@router.get("/voice")
def proposals(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """پیشنهادها با مسیر قابل‌پیگیری: دریافت←بررسی←پذیرش/رد←اجرا؛ رأی همه برابر."""
    return {"items": sl.list_proposals(db, str(principal.university_id), principal.student_ref_id)}


class ProposalIn(BaseModel):
    title_fa: str
    body_fa: str = ""
    support_fa: str = ""
    kind: str = "program"


@router.post("/voice")
def create_proposal(body: ProposalIn, principal: Principal = Depends(require("ledger:read_own")),
                    db: Session = Depends(get_db)):
    return sl.create_proposal(db, principal, str(principal.student_ref_id), body.title_fa,
                              body.body_fa, body.support_fa, body.kind)


@router.post("/voice/{proposal_id}/vote")
def toggle_proposal_vote(proposal_id: str, principal: Principal = Depends(require("ledger:read_own")),
                         db: Session = Depends(get_db)):
    """رأی برابر — امتیاز بیشتر هرگز صدای قوی‌تر نمی‌سازد."""
    return sl.toggle_proposal_vote(db, principal, str(principal.student_ref_id), proposal_id)


class DecisionIn(BaseModel):
    state: str  # in_review|accepted|rejected|executed
    decision_note_fa: str = ""


@router.post("/voice/{proposal_id}/decision")
def decide_proposal(proposal_id: str, body: DecisionIn,
                    principal: Principal = Depends(require("missions:manage")), db: Session = Depends(get_db)):
    return sl.decide_proposal(db, principal, proposal_id, body.state, body.decision_note_fa)


# ---------- خانهٔ نو ----------

@router.get("/home")
def home_feed(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """سه پیشنهاد مناسب همین هفته + فعالیت‌های در جریان — به‌جای شروع با کارت امتیاز."""
    return sl.home_feed(db, principal, principal.student_ref_id)
