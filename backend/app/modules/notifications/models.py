"""notifications models: NotificationPreference, Notification + NTF rules."""
from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base
from ..identity_access.models import uid


class NotificationPreference(Base):
    __tablename__ = "notification_prefs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    channels_json: Mapped[str] = mapped_column(Text, default='{"in_app": true, "email": true, "sms": false}')
    quiet_start: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "22:00"
    quiet_end: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "07:00"
    daily_cap: Mapped[int] = mapped_column(default=10)  # optional notifications only
    mute_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pause_personalization: Mapped[bool] = mapped_column(Boolean, default=False)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(40))  # points_awarded|badge_earned|reward_delivery|reward_failed|points_adjusted|case_result|expiry_notice|periodic_digest
    transactional: Mapped[bool] = mapped_column(Boolean, default=False)  # legal/transactional vs optional (NTF)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    title_fa: Mapped[str] = mapped_column(String(200))
    body_fa: Mapped[str] = mapped_column(String(500))  # polite, no sensitive data (NTF)
    dedupe_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued|sending|sent|failed|dead|muted
    attempts: Mapped[int] = mapped_column(default=0)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
