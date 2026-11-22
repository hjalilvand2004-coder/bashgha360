"""Auth + system endpoints: local login (dev), SSO (OIDC) — ورود یکپارچه, refresh cookie, me, break-glass."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.db import get_db, utcnow
from ...core.errors import Forbidden, Unauthorized, ValidationError
from ...core.rbac import Principal, build_principal, get_principal, ROLE_PERMISSIONS
from ...core.security import create_access_token, new_refresh_token, verify_password

from ...modules.identity_access.models import AuthAudit, User, UserSession, UserRoleScope
from ...modules.audit import service as audit
from . import sso as sso_svc

router = APIRouter(prefix="/auth", tags=["auth"])
sso_router = APIRouter(prefix="/auth/sso", tags=["auth-sso"])


class LoginIn(BaseModel):
    username: str
    password: str


def _client_ip_masked(request: Request) -> str:
    ip = (request.client.host if request.client else "unknown")
    parts = ip.split(".")
    return ".".join(parts[:2] + ["x", "x"]) if len(parts) == 4 else "masked"


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    """Local login — for development / approved standalone deployment only (ACC-13).

    Production uses OIDC against S360 identity (open question Q1).
    """
    user = db.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        db.add(AuthAudit(user_id=str(user.id) if user else None, event="login_failed", ip_masked=_client_ip_masked(request)))
        raise Unauthorized("نام کاربری یا رمز عبور نادرست است.")
    s = get_settings()
    if s.require_mfa and user.totp_secret is None and user.username != "demo":
        raise Forbidden("برای نقش حساس، MFA الزامی است.")
    raw, h = new_refresh_token()
    db.add(UserSession(user_id=user.id, refresh_hash=h,
                       expires_at=utcnow() + timedelta(days=s.refresh_token_days),
                       ip_masked=_client_ip_masked(request), user_agent=request.headers.get("user-agent", "")[:200]))
    db.add(AuthAudit(user_id=user.id, event="login_ok", ip_masked=_client_ip_masked(request)))
    principal = build_principal(db, user.id)
    token = create_access_token(user.id, principal.university_id)
    response.set_cookie("refresh", raw, httponly=True, samesite="lax", secure=s.cookie_secure,
                        max_age=s.refresh_token_days * 86400, path="/api/v1/auth")
    return {"access_token": token, "token_type": "bearer", "expires_in": s.access_token_minutes * 60,
            "user": {"id": user.id, "display_name": user.display_name, "roles": principal.roles,
                     "university_id": principal.university_id, "is_demo": user.is_demo}}


@router.post("/refresh")
def refresh(request: Request, db: Session = Depends(get_db)):
    import hashlib

    raw = request.cookies.get("refresh", "")
    if not raw:
        raise Unauthorized("نشستی برای تمدید یافت نشد.")
    sess = db.execute(select(UserSession).where(UserSession.refresh_hash == hashlib.sha256(raw.encode()).hexdigest())).scalar_one_or_none()
    if sess is None or sess.revoked_at is not None or sess.expires_at < utcnow():
        raise Unauthorized("نشست منقضی است.")
    principal = build_principal(db, sess.user_id)
    token = create_access_token(sess.user_id, principal.university_id)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    import hashlib

    raw = request.cookies.get("refresh", "")
    if raw:
        sess = db.execute(select(UserSession).where(UserSession.refresh_hash == hashlib.sha256(raw.encode()).hexdigest())).scalar_one_or_none()
        if sess:
            sess.revoked_at = utcnow()
    response = Response(status_code=204)
    response.delete_cookie("refresh", path="/api/v1/auth")
    return response


@router.get("/me")
def me(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    user = db.get(User, principal.user_id)
    return {"id": principal.user_id, "display_name": user.display_name if user else "",
            "roles": principal.roles, "permissions": sorted(principal.permissions),
            "university_id": principal.university_id, "student_ref_id": principal.student_ref_id}


@router.post("/break-glass")
def break_glass(reason: dict, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    """ACC-12: emergency access — temporary, documented, audited."""
    if "tech:admin" not in principal.permissions and "club_manager" not in principal.roles:
        raise Forbidden("فقط مدیر مجاز می‌تواند دسترسی اضطراری صادر کند.")
    target = str(reason.get("user_id", ""))
    role = str(reason.get("role_code", "club_manager"))
    if not target:
        raise Unauthorized("user_id لازم است.")
    ttl_minutes = int(reason.get("ttl_minutes", 30))
    db.add(UserRoleScope(user_id=target, role_code=role, university_id=principal.university_id or "",
                         expires_at=utcnow() + timedelta(minutes=ttl_minutes), is_emergency=True,
                         granted_by=principal.user_id, note=str(reason.get("reason_fa", "دسترسی اضطراری"))[:300]))
    audit.write(db, actor=principal.user_id, action="auth.break_glass", entity="user_role_scopes",
                entity_id=target, after={"role": role, "ttl_minutes": ttl_minutes},
                university_id=principal.university_id)
    return {"granted": True, "ttl_minutes": ttl_minutes}


# ---------------- ورود یکپارچه (SSO) با سامانهٔ مرکزی دانشجو۳۶۰ ----------------
_SSO_ERROR_PAGE = "/login?sso_error="


@sso_router.get("/status")
def sso_status(request: Request, db: Session = Depends(get_db)):
    """آیا ورود یکپارچه فعال است؟ + اطلاعات نمایشی ثبت این سامانه در پورتال (بدون راز)."""
    s = get_settings()
    reg = sso_svc.registration_payload(db, redirect_uri=sso_svc.redirect_uri_for(request))
    return {"enabled": bool(s.sso_enabled), "issuer": s.sso_issuer,
            "app_key": reg["app_key"], "display_name_fa": reg["display_name_fa"],
            "icon_emoji": reg["icon_emoji"], "is_active": reg["is_active"],
            "entry_url": reg["entry_url"]}


@sso_router.get("/login")
def sso_login(request: Request):
    """شروع ورود یکپارچه: 302 به صفحهٔ ورود سامانهٔ مرکزی دانشجو۳۶۰."""
    s = get_settings()
    if not s.sso_enabled:
        return RedirectResponse(_SSO_ERROR_PAGE + "disabled", status_code=302)
    redirect_uri = sso_svc.redirect_uri_for(request)
    url = sso_svc.build_authorize_url(redirect_uri, sso_svc.make_state())
    return RedirectResponse(url, status_code=302)


@sso_router.get("/callback")
def sso_callback(request: Request, code: str = "", state: str = "", db: Session = Depends(get_db)):
    """تبادل code، تأمین کاربر، صدور نشست (refresh cookie) و بازگشت به برنامه."""
    s = get_settings()
    redirect_uri = sso_svc.redirect_uri_for(request)
    try:
        user = sso_svc.handle_callback(db, code, state, redirect_uri)
    except sso_svc.SsoError as exc:
        db.rollback()
        return RedirectResponse(_SSO_ERROR_PAGE + exc.code, status_code=302)
    raw, h = new_refresh_token()
    db.add(UserSession(user_id=user.id, refresh_hash=h,
                       expires_at=utcnow() + timedelta(days=s.refresh_token_days),
                       ip_masked=_client_ip_masked(request),
                       user_agent=request.headers.get("user-agent", "")[:200]))
    db.commit()
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie("refresh", raw, httponly=True, samesite="lax", secure=s.cookie_secure,
                    max_age=s.refresh_token_days * 86400, path="/api/v1/auth")
    return resp


# ------- تنظیمات ورود یکپارچه (ثبت این سامانه در پورتال دانشجو۳۶۰) — مدیر باشگاه/مدیر فنی -------
sso_settings_router = APIRouter(prefix="/admin/sso-settings", tags=["auth-sso"])


class SsoSettingsIn(BaseModel):
    app_key: str
    display_name_fa: str
    entry_url: str
    description_fa: str = ""
    client_id: str
    sort_order: int = 0
    icon_emoji: str = "🎓"
    is_active: bool = True


def _require_sso_admin(principal: Principal) -> None:
    """مدیریت ثبت سامانه: مدیر باشگاه، مدیر فنی یا دسترسی فنی."""
    if ("tech:admin" in principal.permissions or "club_manager" in principal.roles
            or "tech_admin" in principal.roles):
        return
    raise Forbidden("فقط مدیر باشگاه یا مدیر فنی مجاز به تغییر تنظیمات ورود یکپارچه است.")


@sso_settings_router.get("")
def get_sso_settings(request: Request, principal: Principal = Depends(get_principal),
                     db: Session = Depends(get_db)):
    _require_sso_admin(principal)
    return sso_svc.registration_payload(db, redirect_uri=sso_svc.redirect_uri_for(request))


@sso_settings_router.put("")
def put_sso_settings(body: SsoSettingsIn, request: Request,
                     principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    """به‌روزرسانی ثبت این سامانه در پورتال ورود یکپارچه (قرینهٔ فرم پورتال مرکزی)."""
    _require_sso_admin(principal)
    s = get_settings()
    row = sso_svc.get_sso_registration(db)
    errors: dict[str, str] = {}
    if not body.app_key.strip():
        errors["app_key"] = "کلید سامانه لازم است."
    if not body.display_name_fa.strip():
        errors["display_name_fa"] = "نام سامانه لازم است."
    if not body.entry_url.strip().startswith(("http://", "https://")):
        errors["entry_url"] = "آدرس ورود باید با http:// یا https:// شروع شود."
    if not body.client_id.strip():
        errors["client_id"] = "Client ID لازم است."
    if body.sort_order < 0:
        errors["sort_order"] = "ترتیب باید عددی نامنفی باشد."
    if errors:
        raise ValidationError("مقادیر ارسالی معتبر نیست.", details={"fields": errors})
    row.app_key = body.app_key.strip()
    row.display_name_fa = body.display_name_fa.strip()
    row.entry_url = body.entry_url.strip()
    row.description_fa = body.description_fa.strip()[:300]
    row.client_id = body.client_id.strip()
    row.sort_order = body.sort_order
    row.icon_emoji = (body.icon_emoji or "🎓").strip()[:16]
    row.is_active = body.is_active
    row.updated_by = principal.user_id
    db.flush()
    audit.write(db, actor=principal.user_id, action="auth.sso_settings.update", entity="sso_system_settings",
                entity_id=row.id, after={"app_key": row.app_key, "client_id": row.client_id,
                                         "entry_url": row.entry_url, "is_active": row.is_active},
                university_id=principal.university_id)
    return sso_svc.registration_payload(db, redirect_uri=sso_svc.redirect_uri_for(request))
