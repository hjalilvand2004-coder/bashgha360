"""club_experience models: OnboardingProfile, MissionInvite, ShowcaseStory (v1.3 تجربهٔ باشگاه)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class OnboardingProfile(Base):
    """شروع فوری (۱۵ دقیقه): مسیر انتخابی + علاقه‌ها + اولین دستاورد (نشان «اولین قدم»).

    persona مسیر انتخابی دانشجو است و به یکی از سه مسیر سطح وصل می‌شود:
    creator→skill، explorer→learning، helper→collaboration، specialist→skill، leader→collaboration.
    """
    __tablename__ = "onboarding_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_onboarding_user"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    student_ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    persona: Mapped[str] = mapped_column(String(20))  # creator|explorer|helper|specialist|leader
    interests_json: Mapped[str] = mapped_column(Text, default="[]")
    first_mission_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    first_badge_awarded: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MissionInvite(Base):
    """«دوستت را دعوت کن» — دعوت برای مأموریتِ مشترک، نه مسابقهٔ جذب.

    ساخت دعوت هیچ امتیازی ندارد؛ پاداش فقط به مشارکت واقعی تیم وابسته است
    (پیشرفت مأموریت از طریق رویدادهای تأییدشدهٔ همان سیاست‌های مصوب محاسبه می‌شود).
    """
    __tablename__ = "mission_invites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id"), index=True)
    inviter_student_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    invitee_contact: Mapped[str] = mapped_column(String(200), default="")  # ایمیل/شمارهٔ دوست (اختیاری)
    invite_code: Mapped[str] = mapped_column(String(24), unique=True)
    state: Mapped[str] = mapped_column(String(20), default="pending")  # pending|joined|expired
    joined_student_ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note_fa: Mapped[str] = mapped_column(String(300), default="پاداش این دعوت به مشارکت مشترک شماست، نه تعداد دعوت‌ها.")


class ShowcaseStory(Base):
    """فضای دستاوردها — روایت‌های کوتاه به‌جای رتبه‌بندی دانشجویان.

    انتشار فقط با رضایت (has_consent) و بدون هیچ جدول امتیازی/رتبه‌ای؛
    نام افراد فقط وقتی ذکر می‌شود که رضایت جداگانه (public_badge) ثبت شده باشد.
    """
    __tablename__ = "showcase_stories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    title_fa: Mapped[str] = mapped_column(String(200))
    body_fa: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(20), default="build")  # build|help|skill|event
    has_consent: Mapped[bool] = mapped_column(Boolean, default=False)  # رضایت نمایش
    subject_label_fa: Mapped[str] = mapped_column(String(200), default="")  # «تیم ...» / نام با رضایت
    group_id: Mapped[str | None] = mapped_column(ForeignKey("learning_groups.id"), nullable=True)
    mission_id: Mapped[str | None] = mapped_column(ForeignKey("missions.id"), nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="published")  # published|hidden
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
