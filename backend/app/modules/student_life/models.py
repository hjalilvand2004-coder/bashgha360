"""v1.5 پایلوت «زندگی دانشجویی» — چهار وعدهٔ محصول:
آدم‌های من (هم‌پایه)، تجربه‌های من (همین هفته در دانشگاه)،
آیندهٔ من (بستهٔ ساخت نمونه‌کار)، اثر من (صدای دانشجو با پیگیری وضعیت).

اصل طراحی (ارزیابی v1.5): ارزش فوری بدون امتیاز — هیچ‌کدام از این جداول
کلید خارجی به دفترکل امتیاز ندارند؛ امتیاز فقط در «پیشرفت و مزایا» می‌ماند."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class PeerActivity(Base):
    """هم‌پایه پیدا کن — همراهِ یک فعالیت مشخص، بدون الزام به پروژه.

    تطبیق فقط بر پایهٔ علاقه و زمان اعلام‌شده؛ هیچ برچسب شخصیتی («تنها»، «ضعیف»)
    وجود ندارد. محل همیشه عمومی دانشگاه است و شرکت آزمایشی (trial) بدون تعهد است.
    پیام خصوصی درون‌سیستمی وجود ندارد (مدیریت مزاحمت با طراحی، نه ابزار).
    """
    __tablename__ = "peer_activities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    host_student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    title_fa: Mapped[str] = mapped_column(String(200))
    activity_kind: Mapped[str] = mapped_column(String(20), default="other")
    # language|study|outing|games|presentation|other
    time_label_fa: Mapped[str] = mapped_column(String(100))  # «سه‌شنبه ۱۷:۰۰» — زمان اعلام‌شده
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location_fa: Mapped[str] = mapped_column(String(200))  # محل عمومی دانشگاه
    capacity: Mapped[int] = mapped_column(default=4)
    trial_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    interest_tags: Mapped[str] = mapped_column(String(200), default="")
    state: Mapped[str] = mapped_column(String(12), default="open")  # open|closed|hidden
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PeerParticipant(Base):
    __tablename__ = "peer_participants"
    __table_args__ = (UniqueConstraint("activity_id", "student_ref_id", name="uq_peer_participant"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    activity_id: Mapped[str] = mapped_column(ForeignKey("peer_activities.id"), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    mode: Mapped[str] = mapped_column(String(10), default="trial")  # trial|committed
    state: Mapped[str] = mapped_column(String(10), default="joined")  # joined|left|removed
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PeerReport(Base):
    """گزارش مزاحمت/مشکل — فقط مدیر باشگاه می‌بیند؛ مخاطب گزارش هرگز از آن خبره نمی‌شود."""
    __tablename__ = "peer_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    activity_id: Mapped[str] = mapped_column(ForeignKey("peer_activities.id"), index=True)
    reporter_student_ref_id: Mapped[str] = mapped_column(String(36))
    reason_fa: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(10), default="open")  # open|resolved
    resolution_note_fa: Mapped[str] = mapped_column(String(400), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Opportunity(Base):
    """«امروز در دانشگاه چه خبر؟» — فرصت زندهٔ نزدیک با فقط اطلاعات تصمیم‌گیری."""
    __tablename__ = "opportunities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    title_fa: Mapped[str] = mapped_column(String(200))
    what_fa: Mapped[str] = mapped_column(Text, default="")  # چه اتفاقی می‌افتد؟
    location_fa: Mapped[str] = mapped_column(String(200))  # کجا؟
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # چه زمانی؟
    duration_minutes: Mapped[int] = mapped_column(default=60)
    cost_label_fa: Mapped[str] = mapped_column(String(60), default="رایگان")  # چقدر هزینه دارد؟
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    prereq_fa: Mapped[str] = mapped_column(String(200), default="هیچ")  # باید چیزی بلد باشم؟
    solo_friendly: Mapped[bool] = mapped_column(Boolean, default=True)  # تنهایی‌پسند
    capacity: Mapped[int] = mapped_column(default=20)
    kind: Mapped[str] = mapped_column(String(20), default="other")
    # visit|workshop|game|talk|volunteer|tour|other
    state: Mapped[str] = mapped_column(String(12), default="published")  # published|cancelled|hidden
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OpportunityReg(Base):
    """ثبت‌نام بدون امتیاز — پر شدن ظرفیت یعنی صف انتظار، نه مزیت امتیاز بیشتر (BL-01 مسیر آینده)."""
    __tablename__ = "opportunity_regs"
    __table_args__ = (UniqueConstraint("opportunity_id", "student_ref_id", name="uq_opportunity_reg"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    position_no: Mapped[int] = mapped_column(default=1)  # 1..capacity = ثبت‌نام قطعی؛ بیشتر = صف
    state: Mapped[str] = mapped_column(String(12), default="registered")
    # registered|waitlisted|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PortfolioBundle(Base):
    """«از صفر تا چیزی که بتوانم نشان بدهم» — بستهٔ کامل: ابزار + راهنما + بازخورد + خروجی."""
    __tablename__ = "portfolio_bundles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    title_fa: Mapped[str] = mapped_column(String(200))
    output_fa: Mapped[str] = mapped_column(String(300))  # خروجی قابل‌نمایش
    tools_fa: Mapped[str] = mapped_column(String(400), default="")  # ابزار لازم (در اختیار شما)
    guide_fa: Mapped[str] = mapped_column(String(400), default="")  # همراه/راهنما
    feedback_note_fa: Mapped[str] = mapped_column(String(400), default="")  # بازخورد واقعی
    steps_json: Mapped[str] = mapped_column(Text, default="[]")  # [{label_fa}, ...]
    estimated_hours: Mapped[int] = mapped_column(default=4)
    capacity: Mapped[int] = mapped_column(default=10)
    newcomer_seats: Mapped[int] = mapped_column(default=2)  # ظرفیت محفوظ تازه‌وارد (ارزیابی §۷)
    state: Mapped[str] = mapped_column(String(12), default="published")  # published|hidden
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BundleEnrollment(Base):
    __tablename__ = "bundle_enrollments"
    __table_args__ = (UniqueConstraint("bundle_id", "student_ref_id", name="uq_bundle_enrollment"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    bundle_id: Mapped[str] = mapped_column(ForeignKey("portfolio_bundles.id"), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    is_newcomer_seat: Mapped[bool] = mapped_column(Boolean, default=False)
    steps_done_json: Mapped[str] = mapped_column(Text, default="[]")  # [0, 2] اندیس مراحل انجام‌شده
    output_url: Mapped[str | None] = mapped_column(String(400), nullable=True)  # لینک خروجی
    output_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    state: Mapped[str] = mapped_column(String(10), default="active")  # active|completed|left
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StudentProposal(Base):
    """«ایده خودت را اجرا کن» + «صدای دانشجو» — مسیر پیگیری: دریافت ← بررسی ← پذیرش/رد ← اجرا."""
    __tablename__ = "student_proposals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    author_student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    title_fa: Mapped[str] = mapped_column(String(200))
    body_fa: Mapped[str] = mapped_column(Text, default="")
    support_fa: Mapped[str] = mapped_column(String(300), default="")  # چه حمایتی لازم است (فضا/همراه/...)
    kind: Mapped[str] = mapped_column(String(20), default="program")  # program|space|improvement|other
    state: Mapped[str] = mapped_column(String(14), default="received")
    # received|in_review|accepted|rejected|executed
    decision_note_fa: Mapped[str] = mapped_column(String(400), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProposalVote(Base):
    """رأی برابر برای همه — امتیاز بیشتر هرگز صدای قوی‌تر نمی‌سازد (ارزیابی §۹)."""
    __tablename__ = "proposal_votes"
    __table_args__ = (UniqueConstraint("proposal_id", "student_ref_id", name="uq_proposal_vote"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("student_proposals.id"), index=True)
    student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
