"""RBAC: permission allowlist, role→permissions, request auth dependencies, university scoping (ACC)."""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db, TestingSession
from .errors import Forbidden, Unauthorized
from .security import decode_access_token

# ---- permission allowlist (nothing outside this set can be granted) ----
P = {
    "events:ingest": "ارسال رویداد آموزشی (سرویس)",
    "events:self_report": "خوداظهاری رویداد",
    "events:manage": "مدیریت رویداد/قرنطینه",
    "approvals:verify": "تأیید فعالیت آموزشی",
    "advisor:read": "مشاهده دانشجویان تخصیص‌یافته",
    "memberships:manage": "مدیریت عضویت‌ها",
    "policies:read": "مشاهده سیاست‌ها",
    "policies:write": "ایجاد/ویرایش سیاست (draft)",
    "policies:approve": "تأیید دوم سیاست",
    "policies:simulate": "اجرای شبیه‌سازی",
    "ledger:read_own": "مشاهده دفترکل خود",
    "ledger:read": "مشاهده دفترکل (سطح دانشگاه)",
    "ledger:adjust": "ثبت سند جبرانی/تعدیل",
    "rewards:request": "درخواست پاداش",
    "rewards:manage": "مدیریت کاتالوگ/ظرفیت",
    "rewards:approve": "تأیید درخواست پاداش",
    "rewards:deliver": "ثبت تحویل ارائه‌دهنده",
    "providers:callback": "فراخوانی Callback ارائه‌دهنده",
    "missions:manage": "مدیریت مأموریت‌ها",
    "badges:manage": "مدیریت نشان‌ها",
    "reviews:handle": "رسیدگی به پرونده سلامت آموزشی",
    "appeals:submit": "ثبت اعتراض",
    "appeals:review": "رسیدگی مستقل به اعتراض",
    "notifications:read_own": "مشاهده اعلان‌های خود",
    "notifications:manage": "مدیریت اعلان‌ها",
    "analytics:read": "گزارش‌های تجمیعی",
    "analytics:sensitive": "داده حساس فقط برای ارزیابی انصاف",
    "audit:read": "مشاهده Audit Trail",
    "tech:admin": "عملیات فنی (بدون داده آموزشی)",
    "data:export_own": "دریافت خروجی اطلاعات شخصی",
}

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "student": ["ledger:read_own", "rewards:request", "appeals:submit", "notifications:read_own", "data:export_own", "events:self_report"],
    "professor": ["approvals:verify"],
    "advisor": ["advisor:read"],
    "club_manager": ["memberships:manage", "policies:read", "policies:write", "policies:simulate", "rewards:manage", "rewards:approve", "missions:manage", "badges:manage", "events:manage", "ledger:read", "analytics:read", "notifications:manage"],
    "policy_officer": ["policies:read", "policies:approve", "analytics:read"],
    "reward_provider": ["rewards:deliver"],
    "edtech_specialist": ["reviews:handle", "ledger:read"],
    "appeal_referee": ["appeals:review", "ledger:read"],
    "tech_admin": ["tech:admin"],
    "auditor": ["audit:read", "analytics:sensitive"],
}


@dataclass
class Principal:
    user_id: str
    university_id: str | None
    roles: list[str] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)
    student_ref_id: str | None = None
    is_service: bool = False


def build_principal(db: Session, user_id: str) -> Principal:
    from app.modules.identity_access.models import User, UserRoleScope
    from app.modules.identity_access.models import StudentReference

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise Unauthorized("کاربر یافت نشد یا غیرفعال است.")
    scopes = db.execute(select(UserRoleScope).where(UserRoleScope.user_id == user.id)).scalars().all()
    roles: list[str] = []
    perms: set[str] = set()
    unis: set[str] = set()
    for sc in scopes:
        if sc.expires_at is not None:
            from .db import utcnow

            if sc.expires_at < utcnow():
                continue
        perms.update(ROLE_PERMISSIONS.get(sc.role_code, []))
        if sc.role_code not in roles:
            roles.append(sc.role_code)
        if sc.university_id:
            unis.add(sc.university_id)
    stu = db.execute(select(StudentReference).where(StudentReference.user_id == user.id)).scalars().first()
    if stu:
        unis.add(stu.university_id)
    return Principal(user_id=str(user.id), university_id=next(iter(unis), None), roles=roles, permissions=perms,
                     student_ref_id=str(stu.id) if stu else None)


def get_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise Unauthorized("توکن ارائه نشده است.")
    payload = decode_access_token(auth.removeprefix("Bearer "))
    return build_principal(db, payload["sub"])


def get_service_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    """Service authentication for integration endpoints (events:ingest / providers:callback)."""
    from app.modules.event_ingestion.models import IntegrationSource

    key = request.headers.get("X-Integration-Key", "")
    if not key:
        raise Unauthorized("کلید یکپارچه‌سازی ارائه نشده است.")
    src = db.execute(select(IntegrationSource).where(IntegrationSource.auth_key_hash == key)).scalars().first()
    if src is None or not src.is_active:
        raise Unauthorized("منبع یکپارچه‌سازی نامعتبر است.")
    p = Principal(user_id="", university_id=str(src.university_id), roles=["service"], permissions={"events:ingest", "providers:callback"}, is_service=True)
    request.state.integration_source_id = str(src.id)
    return p


def require(perm: str):
    def dep(principal: Principal = Depends(get_principal)) -> Principal:
        if perm not in principal.permissions:
            raise Forbidden(f"دسترسی لازم («{P.get(perm, perm)}») را ندارید.")
        return principal
    return dep


def make_principal_for_tests(user_id: str, university_id: str, roles: list[str], student_ref_id: str | None = None) -> Principal:
    perms: set[str] = set()
    for r in roles:
        perms.update(ROLE_PERMISSIONS.get(r, []))
    return Principal(user_id=user_id, university_id=university_id, roles=roles, permissions=perms, student_ref_id=student_ref_id)
