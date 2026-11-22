"""identity_access models: University, User, Role, UserRoleScope, StudentReference, Session, AuthAudit."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.db import Base, utcnow


def uid() -> str:
    return str(uuid.uuid4())


class University(Base):
    __tablename__ = "universities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name_fa: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Tehran")
    settings_json: Mapped[str] = mapped_column(Text, default="{}")


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(120), unique=True)  # for local dev login
    display_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)  # local mode only
    identity_mode: Mapped[str] = mapped_column(String(20), default="local")  # local|sso_sim|oidc
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)  # ACC-14 (flag-gated)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)  # SEED-12 label


class UserRoleScope(Base):
    __tablename__ = "user_role_scopes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role_code: Mapped[str] = mapped_column(String(40))
    university_id: Mapped[str] = mapped_column(ForeignKey("universities.id"), index=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False)  # ACC-12
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)


class StudentReference(Base):
    """Minimal local snapshot of the S360 identity — source & freshness are kept (S360-10)."""
    __tablename__ = "student_references"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    university_id: Mapped[str] = mapped_column(ForeignKey("universities.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    external_student_id: Mapped[str] = mapped_column(String(60))
    program: Mapped[str | None] = mapped_column(String(120), nullable=True)
    entry_year: Mapped[int | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(60), default="s360_sim")
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("university_id", "external_student_id", name="uq_studentref_uni_ext"),
        {"comment": "minimal S360 snapshot"},
    )


class ExternalIdentity(Base):
    """SSO/OIDC subject → local user mapping (provisioning on first login)."""
    __tablename__ = "external_identities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(60), default="s360_oidc")
    subject: Mapped[str] = mapped_column(String(255))  # `sub` claim — stable id at the IdP
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    username_at_provider: Mapped[str | None] = mapped_column(String(200), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_extid_provider_subject"),
        {"comment": "OIDC subject mapping (SSO)"},
    )


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_masked: Mapped[str | None] = mapped_column(String(60), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)


class AuthAudit(Base):
    __tablename__ = "auth_audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(40))
    ip_masked: Mapped[str | None] = mapped_column(String(60), nullable=True)
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SsoSystemSettings(Base):
    """ثبت این سامانه (باشگاه دانشجو۳۶۰) در پورتال ورود یکپارچهٔ دانشجو۳۶۰ — تک‌ردیفی.

    قرینهٔ فرم «افزودن/ویرایش سامانه» در پورتال مرکزی: کلید سامانه (appKey)، نام،
    آدرس ورود (نقطهٔ شروع جریان OIDC)، توضیح، Client ID در SSO، ترتیب، آیکن (emoji) و فعال.
    راز Client (client_secret) هرگز در این جدول ذخیره نمی‌شود — فقط از طریق env/.env (SEC).
    """
    __tablename__ = "sso_system_settings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    app_key: Mapped[str] = mapped_column(String(80), unique=True)  # کلید سامانه (appKey در پورتال)
    display_name_fa: Mapped[str] = mapped_column(String(200))  # نام سامانه
    entry_url: Mapped[str] = mapped_column(String(400))  # آدرس ورود — نقطهٔ شروع جریان OIDC این سامانه
    description_fa: Mapped[str] = mapped_column(String(300), default="")  # توضیح
    client_id: Mapped[str] = mapped_column(String(120))  # Client ID در SSO
    sort_order: Mapped[int] = mapped_column(default=0)  # ترتیب نمایش در پورتال
    icon_emoji: Mapped[str] = mapped_column(String(16), default="🎓")  # آیکن (emoji)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # فعال
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
