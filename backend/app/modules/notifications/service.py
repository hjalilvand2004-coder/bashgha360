"""notifications service — preference-aware, quiet hours, daily cap, dedupe, no sensitive data (NTF)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.db import utcnow
from .models import Notification, NotificationPreference

TRANSACTIONAL_KINDS = {"case_result", "reward_delivery", "points_adjusted", "expiry_notice", "appeal_result"}


def get_prefs(db: Session, user_id: str) -> NotificationPreference:
    prefs = db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id)).scalar_one_or_none()
    if prefs is None:
        prefs = NotificationPreference(id=str(__import__("uuid").uuid4()), university_id="", user_id=user_id)
        db.add(prefs)
        db.flush()
    return prefs


def _in_quiet_hours(prefs: NotificationPreference, at: datetime, tz: str) -> bool:
    if not prefs.quiet_start or not prefs.quiet_end:
        return False
    local = at.astimezone(ZoneInfo(tz or "Asia/Tehran")).time()
    start = dtime.fromisoformat(prefs.quiet_start)
    end = dtime.fromisoformat(prefs.quiet_end)
    if start <= end:
        return start <= local < end
    return local >= start or local < end


def notify(db: Session, *, university_id: str, user_id: str, kind: str, title_fa: str, body_fa: str,
           transactional: bool = False, dedupe_key: str | None = None) -> Notification | None:
    """Transactional notifications always send; optional ones respect quiet/cap/mute/dedupe (NTF)."""
    prefs = get_prefs(db, user_id)
    if dedupe_key:
        dup = db.execute(select(Notification).where(
            Notification.user_id == user_id, Notification.dedupe_key == dedupe_key,
            Notification.created_at >= utcnow() - timedelta(hours=24))).scalar_one_or_none()
        if dup is not None:
            return None
    now = utcnow()
    scheduled = now
    channels = json.loads(prefs.channels_json or "{}")
    if not transactional:
        if prefs.mute_until and prefs.mute_until > now:
            return None
        uni_tz = "Asia/Tehran"
        if _in_quiet_hours(prefs, now, uni_tz):
            scheduled = now + timedelta(hours=8)  # schedule after quiet window
        cap = int(prefs.daily_cap or 10)
        sent_today = db.execute(select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id, Notification.transactional.is_(False),
            Notification.created_at >= now - timedelta(hours=24))).scalar() or 0
        if sent_today >= cap:
            return None
        if kind == "periodic_digest" and not channels.get("email", False):
            return None
    n = Notification(id=str(__import__("uuid").uuid4()), university_id=university_id, user_id=user_id,
                     kind=kind, transactional=transactional or kind in TRANSACTIONAL_KINDS,
                     channel="in_app", title_fa=title_fa[:200], body_fa=body_fa[:500],
                     dedupe_key=dedupe_key, state="queued", scheduled_at=scheduled)
    db.add(n)
    db.flush()
    dispatch(db, n)
    return n


def dispatch(db: Session, n: Notification) -> None:
    """In-app delivery; email/SMS in production go through providers with retry — nothing external is claimed here."""
    n.state, n.sent_at = "sent", utcnow()


def retry_failed(db: Session) -> int:
    rows = db.execute(select(Notification).where(Notification.state.in_(["queued", "failed"]),
                                                 Notification.scheduled_at <= utcnow())).scalars().all()
    for n in rows:
        n.attempts += 1
        try:
            dispatch(db, n)
        except Exception as exc:  # noqa: BLE001
            n.state = "dead" if n.attempts >= 5 else "failed"
            n.last_error = str(exc)[:300]
    return len(rows)
