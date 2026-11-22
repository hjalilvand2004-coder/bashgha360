"""club_experience service — شروع فوری ۱۵ دقیقه‌ای، دعوت دوست، فضای دستاوردها (v1.3).

اصول:
  - مسیرهای انتخابی (سازنده/کاوشگر/همیار/متخصص/راهبر) فقط برچسب ملموسِ همان سه مسیر
    سطح‌بندی مصوب (learning/skill/collaboration) هستند — منطق امتیاز دست‌نخورده می‌ماند.
  - اولین دستاورد = نشان «اولین قدم» (تعریف نشان در دانشگاه، criteria ویژهٔ onboarding) —
    یک‌بار و بی‌تکرار؛ هیچ امتیاز دفترکل مستقیمی از onboarding داده نمی‌شود.
  - دعوت دوست برای «مأموریت مشترک» است، نه مسابقهٔ جذب: ساخت دعوت صفر امتیاز دارد.
  - فضای دستاوردها روایت‌محور است و رتبه‌بندی ندارد؛ انتشار فقط با رضایت.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.errors import Conflict, Forbidden, NotFound
from ..achievements_tiers.models import BadgeAward, BadgeDefinition
from ..missions_groups.models import Mission, MissionParticipation
from .models import MissionInvite, OnboardingProfile, ShowcaseStory

# مسیرهای انتخابی ملموس → مسیر سطح مصوب + برچسب‌های علاقهٔ پیشنهادی
PERSONAS: dict[str, dict] = {
    "creator": {"label_fa": "سازنده", "tagline_fa": "پروژه و حل مسئله — چیزی بساز که به آن افتخار کنی",
                "icon": "🛠️", "maps_to": "skill", "interests": ["build", "tech", "problem"]},
    "explorer": {"label_fa": "کاوشگر", "tagline_fa": "تجربهٔ رویدادها و موضوعات تازه",
                 "icon": "🧭", "maps_to": "learning", "interests": ["event", "explore", "skill"]},
    "helper": {"label_fa": "همیار", "tagline_fa": "کمک به هم‌دانشگاهی‌ها",
               "icon": "🤝", "maps_to": "collaboration", "interests": ["help", "guide", "collab"]},
    "specialist": {"label_fa": "متخصص", "tagline_fa": "رشد یک مهارت و ساخت نمونه‌کار",
                   "icon": "🎯", "maps_to": "skill", "interests": ["skill", "portfolio", "tech"]},
    "leader": {"label_fa": "راهبر", "tagline_fa": "هماهنگی تیم و اجرای ایده‌ها",
               "icon": "🚩", "maps_to": "collaboration", "interests": ["team", "event", "problem"]},
}

INTERESTS: dict[str, str] = {
    "build": "ساختن و پروژه", "tech": "فناوری و ابزار", "event": "رویداد و برنامه",
    "help": "کمک به دیگران", "skill": "یادگیری مهارت", "guide": "راهنمایی تازه‌واردها",
    "problem": "حل مسئلهٔ واقعی", "portfolio": "نمونه‌کار", "collab": "کار گروهی", "explore": "کاوش",
    "team": "تیم و رهبری",
}

FIRST_STEP_BADGE_TITLE = "اولین قدم"

# انواع مأموریت از دید تجربهٔ دانشجو (برچسب + توضیح کوتاه)
MISSION_KIND_LABELS: dict[str, str] = {
    "kickoff": "رویداد آغازین", "micro_challenge": "چالش ۲۰ دقیقه‌ای", "one_day": "مأموریت یک‌روزه",
    "trial_workshop": "کارگاه آزمایشی", "skill_evening": "یک عصر، یک مهارت",
    "real_problem": "مسئلهٔ واقعی", "build": "ساخت", "guide": "راهنما", "standard": "مأموریت",
}

STORY_KIND_LABELS: dict[str, str] = {
    "build": "چیزی ساخت", "help": "به کسی کمک کرد", "skill": "مهارتی را تجربه کرد", "event": "رویدادی اجرا کرد",
}


def now() -> datetime:
    return datetime.now(timezone.utc)


def _suggested_mission(db: Session, university_id: str, persona: str | None, interests: list[str]) -> Mission | None:
    """اولین مأموریت پیشنهادی: رویداد آغازین > تطابق علاقه > مأموریت کوتاه فعال."""
    rows = db.execute(select(Mission).where(Mission.university_id == university_id, Mission.state == "active")
                      .order_by(Mission.starts_at)).scalars().all()
    kickoff = next((m for m in rows if m.mission_kind == "kickoff"), None)
    if kickoff is not None:
        return kickoff
    if interests:
        for m in rows:
            tags = set((m.interest_tags or "").split(","))
            if tags & set(interests):
                return m
    short = [m for m in rows if m.mission_kind in ("micro_challenge", "one_day", "skill_evening", "trial_workshop")]
    return short[0] if short else (rows[0] if rows else None)


def _ensure_first_badge(db: Session, university_id: str, student_ref_id: str) -> str | None:
    """نشان «اولین قدم» را یک‌بار صادر می‌کند؛ اگر تعریف نشان در دانشگاه موجود نباشد، کاری نمی‌کند."""
    badge = db.execute(select(BadgeDefinition).where(
        BadgeDefinition.university_id == university_id, BadgeDefinition.title_fa == FIRST_STEP_BADGE_TITLE,
        BadgeDefinition.state == "active")).scalar_one_or_none()
    if badge is None:
        return None
    exists = db.execute(select(BadgeAward).where(
        BadgeAward.student_ref_id == student_ref_id, BadgeAward.badge_id == badge.id,
        BadgeAward.state == "valid")).scalar_one_or_none()
    if exists is not None:
        return exists.id
    award = BadgeAward(university_id=university_id, student_ref_id=student_ref_id, badge_id=badge.id,
                       issued_at=now(), state="valid", criteria_version=badge.criteria_version,
                       evidence_ref="onboarding:first_step")
    db.add(award)
    db.flush()
    return award.id


def get_onboarding_state(db: Session, principal) -> dict:
    profile = db.execute(select(OnboardingProfile).where(
        OnboardingProfile.user_id == principal.user_id)).scalar_one_or_none()
    suggested = _suggested_mission(db, str(principal.university_id), profile.persona if profile else None,
                                   json.loads(profile.interests_json) if profile else [])
    joined = False
    if profile and profile.first_mission_id and principal.student_ref_id:
        joined = db.execute(select(MissionParticipation).where(
            MissionParticipation.mission_id == profile.first_mission_id,
            MissionParticipation.student_ref_id == str(principal.student_ref_id))).scalar_one_or_none() is not None
    return {
        "completed": profile is not None,
        "persona": profile.persona if profile else None,
        "persona_label_fa": PERSONAS[profile.persona]["label_fa"] if profile else None,
        "interests": json.loads(profile.interests_json) if profile else [],
        "first_mission": ({"id": suggested.id, "title_fa": suggested.title_fa,
                           "description_fa": suggested.description_fa,
                           "mission_kind": suggested.mission_kind, "output_fa": suggested.output_fa,
                           "duration_label_fa": suggested.duration_label_fa} if suggested else None),
        "first_mission_joined": joined,
        "first_badge_awarded": bool(profile and profile.first_badge_awarded),
        "personas": [{"key": k, **{kk: vv for kk, vv in v.items() if kk != "interests"}} for k, v in PERSONAS.items()],
        "interest_options": [{"key": k, "label_fa": v} for k, v in INTERESTS.items()],
    }


def save_onboarding(db: Session, principal, persona: str, interests: list[str]) -> dict:
    if persona not in PERSONAS:
        raise Conflict("مسیر انتخابی معتبر نیست.")
    interests = [i for i in interests if i in INTERESTS][:5]
    profile = db.execute(select(OnboardingProfile).where(
        OnboardingProfile.user_id == principal.user_id)).scalar_one_or_none()
    created = profile is None
    if profile is None:
        profile = OnboardingProfile(id=str(secrets.token_hex(16)), university_id=str(principal.university_id),
                                    user_id=str(principal.user_id),
                                    student_ref_id=str(principal.student_ref_id) if principal.student_ref_id else None)
        db.add(profile)
    profile.persona = persona
    profile.interests_json = json.dumps(interests, ensure_ascii=False)
    profile.completed_at = now()

    suggested = _suggested_mission(db, str(principal.university_id), persona, interests)
    if suggested is not None:
        profile.first_mission_id = suggested.id
        if principal.student_ref_id and suggested.mission_kind != "kickoff":
            exists = db.execute(select(MissionParticipation).where(
                MissionParticipation.mission_id == suggested.id,
                MissionParticipation.student_ref_id == str(principal.student_ref_id))).scalar_one_or_none()
            if exists is None:
                db.add(MissionParticipation(university_id=str(principal.university_id), mission_id=suggested.id,
                                            student_ref_id=str(principal.student_ref_id), state="active",
                                            joined_at=now()))
    badge_award_id = None
    if principal.student_ref_id:
        badge_award_id = _ensure_first_badge(db, str(principal.university_id), str(principal.student_ref_id))
        profile.first_badge_awarded = badge_award_id is not None
    db.flush()
    return {"completed": True, "created": created, "persona": persona,
            "persona_label_fa": PERSONAS[persona]["label_fa"],
            "mapped_path": PERSONAS[persona]["maps_to"], "interests": interests,
            "first_mission_id": profile.first_mission_id, "first_badge_awarded": badge_award_id is not None,
            "note": "مسیر انتخابی فقط برچسب تجربهٔ توست؛ امتیاز و سطح همان سه مسیر مصوب می‌ماند."}


# ------------------------------------------------------------ invites ----
def create_invite(db: Session, principal, mission_id: str, invitee_contact: str) -> dict:
    """ساخت دعوت برای مأموریت مشترک — فقط برای عضو فعلی مأموریت؛ بدون هیچ امتیازی."""
    if not principal.student_ref_id:
        raise Forbidden("فقط دانشجویان می‌توانند دعوت بسازند.")
    mission = db.get(Mission, mission_id)
    if mission is None or mission.university_id != str(principal.university_id):
        raise NotFound("مأموریت یافت نشد.")
    joined = db.execute(select(MissionParticipation).where(
        MissionParticipation.mission_id == mission_id,
        MissionParticipation.student_ref_id == str(principal.student_ref_id),
        MissionParticipation.state.in_(("active", "completed")))).scalar_one_or_none()
    if joined is None:
        raise Conflict("اول خودت به مأموریت بپیوند، بعد دوستت را دعوت کن — دعوت برای مأموریت مشترک است.")
    invite = MissionInvite(university_id=str(principal.university_id), mission_id=mission_id,
                           inviter_student_ref_id=str(principal.student_ref_id),
                           invitee_contact=(invitee_contact or "").strip()[:200],
                           invite_code=secrets.token_urlsafe(6).replace("-", "x").replace("_", "y")[:10],
                           state="pending")
    db.add(invite)
    db.flush()
    return {"id": invite.id, "invite_code": invite.invite_code, "mission_id": mission_id,
            "share_text_fa": f"به مأموریت «{mission.title_fa}» دعوتت کردم — با کد {invite.invite_code} در باشگاه۳۶۰ بپیوند.",
            "note_fa": invite.note_fa}


def accept_invite(db: Session, principal, code: str) -> dict:
    """پذیرش دعوت: پیوستن به همان مأموریت + ثبت پیوستن دعوت‌شده. هیچ امتیاز مستقیمی رد و بدل نمی‌شود."""
    if not principal.student_ref_id:
        raise Forbidden("پذیرش دعوت فقط با پروفایل دانشجویی ممکن است.")
    invite = db.execute(select(MissionInvite).where(MissionInvite.invite_code == code)).scalar_one_or_none()
    if invite is None or invite.university_id != str(principal.university_id):
        raise NotFound("دعوت یافت نشد یا منقضی است.")
    if invite.state != "pending":
        raise Conflict("این دعوت قبلاً استفاده شده است.")
    if invite.inviter_student_ref_id == str(principal.student_ref_id):
        raise Conflict("دعوت برای دوست توست، نه خودت!")
    mission = db.get(Mission, invite.mission_id)
    if mission is None or mission.state != "active":
        raise NotFound("مأموریت این دعوت فعال نیست.")
    exists = db.execute(select(MissionParticipation).where(
        MissionParticipation.mission_id == invite.mission_id,
        MissionParticipation.student_ref_id == str(principal.student_ref_id))).scalar_one_or_none()
    if exists is None:
        db.add(MissionParticipation(university_id=invite.university_id, mission_id=invite.mission_id,
                                    student_ref_id=str(principal.student_ref_id), state="active", joined_at=now()))
    invite.state, invite.joined_student_ref_id, invite.joined_at = "joined", str(principal.student_ref_id), now()
    db.flush()
    return {"state": "joined", "mission_id": invite.mission_id, "mission_title_fa": mission.title_fa,
            "note_fa": "به مأموریت مشترک پیوستید — پاداش شما به مشارکت واقعی تیم وابسته است."}


def my_invites(db: Session, principal) -> dict:
    if not principal.student_ref_id:
        return {"items": []}
    rows = db.execute(select(MissionInvite).where(
        MissionInvite.inviter_student_ref_id == str(principal.student_ref_id))
        .order_by(MissionInvite.created_at.desc())).scalars().all()
    out = []
    for inv in rows:
        m = db.get(Mission, inv.mission_id)
        out.append({"id": inv.id, "invite_code": inv.invite_code, "state": inv.state,
                    "mission_title_fa": m.title_fa if m else "", "invitee_contact": inv.invitee_contact,
                    "created_at": inv.created_at.isoformat()})
    return {"items": out}


# ------------------------------------------------------------ showcase ----
def list_stories(db: Session, university_id: str) -> dict:
    """فقط روایت‌های منتشرشده با رضایت — بدون هیچ رتبه یا ترتیب رقابتی (ترتیب زمانی انتشار)."""
    rows = db.execute(select(ShowcaseStory).where(
        ShowcaseStory.university_id == university_id, ShowcaseStory.state == "published",
        ShowcaseStory.has_consent.is_(True))
        .order_by(ShowcaseStory.published_at.desc())).scalars().all()
    return {"items": [{"id": s.id, "title_fa": s.title_fa, "body_fa": s.body_fa, "kind": s.kind,
                       "kind_label_fa": STORY_KIND_LABELS.get(s.kind, s.kind),
                       "subject_label_fa": s.subject_label_fa, "published_at": s.published_at.isoformat()}
                      for s in rows]}


def create_story(db: Session, principal, title_fa: str, body_fa: str, kind: str,
                 subject_label_fa: str, has_consent: bool,
                 group_id: str | None = None, mission_id: str | None = None) -> dict:
    """ثبت روایت دستاورد توسط مدیر باشگاه — انتشار تنها با رضایت ثبت‌شده."""
    if kind not in STORY_KIND_LABELS:
        raise Conflict("نوع روایت معتبر نیست.")
    story = ShowcaseStory(university_id=str(principal.university_id), title_fa=title_fa.strip()[:200],
                          body_fa=body_fa.strip(), kind=kind, has_consent=bool(has_consent),
                          subject_label_fa=(subject_label_fa or "").strip()[:200],
                          group_id=group_id, mission_id=mission_id, state="published", published_at=now())
    db.add(story)
    db.flush()
    return {"id": story.id, "published": bool(has_consent),
            "note": "بدون رضایت، روایت فقط داخلی می‌ماند و در فضای دستاوردها نمایش داده نمی‌شود."}
