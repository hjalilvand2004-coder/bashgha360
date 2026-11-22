"""ورود یکپارچه (SSO) با هویت دانشجو۳۶۰ — OIDC Authorization Code flow.

قرارداد:
  GET /api/v1/auth/sso/login     → 302 به صفحهٔ ورود سامانهٔ مرکزی (S360)
  GET /api/v1/auth/sso/callback  → تبادل code با token endpoint، تأمین کاربر، صدور نشست

نکات امنیتی:
  - state امضاشدهٔ بی‌حافظه (HMAC-SHA256 با secret_key، TTL محدود) — ضد CSRF.
  - هویت کاربر فقط از userinfo endpoint با access_token خوانده می‌شود؛
    در نبود discovery و userinfo، id_token بدون بررسی امضا فقط به‌عنوان آخرین
    راه‌حل استفاده و در گزارش ثبت می‌شود (مستند در docs/06).
  - تأمین کاربر (provisioning): نقش پیش‌فرض student در دانشگاه پیش‌فرض؛ ارتقای نقش
    فقط به‌صورت دستی توسط مدیر — هیچ نقشی از توکن معتبر دانسته نمی‌شود.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.db import utcnow
from ...modules.audit import service as audit
from .models import AuthAudit, ExternalIdentity, SsoSystemSettings, User, UserRoleScope, University

log = logging.getLogger("app.sso")

STATE_HMAC_PREFIX = "sso-state:"

# ---------------------------------------------------------------- registration ----
# مقادیر پیش‌فرض ثبت این سامانه در پورتال ورود یکپارچهٔ دانشجو۳۶۰ — هم‌سان با تنظیمات
# پورتال مرکزی (فرم افزودن/ویرایش سامانه): کلید، نام، آدرس ورود OIDC، توضیح،
# Client ID، ترتیب، آیکن و فعال. آدرس ورود = نقطهٔ شروع جریان OIDC این سامانه.
SSO_REGISTER_DEFAULTS: dict = {
    "app_key": "daneshjooclub",
    "display_name_fa": "باشگاه دانشجو۳۶۰",
    "entry_url": "http://188.212.96.235:8089/api/v1/auth/sso/login",
    "description_fa": "امتیاز، کارت خدمات و امکانات دانشجویی",
    "client_id": "daneshjooclub360",
    "sort_order": 14,
    "icon_emoji": "🥇",
    "is_active": True,
}


def get_sso_registration(db: Session, create: bool = True) -> SsoSystemSettings | None:
    """ردیف ثبت سامانه را برمی‌گرداند؛ در نبود آن، با مقادیر پیش‌فرض پورتال می‌سازد."""
    row = db.execute(select(SsoSystemSettings).limit(1)).scalar_one_or_none()
    if row is None and create:
        row = SsoSystemSettings(**SSO_REGISTER_DEFAULTS)
        db.add(row)
        db.flush()
    return row


def registration_payload(db: Session, redirect_uri: str) -> dict:
    """خروجی نمایشی تنظیمات ثبت سامانه (بدون هیچ رازی)."""
    s = get_settings()
    row = get_sso_registration(db)
    return {
        "enabled": bool(s.sso_enabled),
        "issuer": s.sso_issuer,
        "redirect_uri": redirect_uri,
        "app_key": row.app_key,
        "display_name_fa": row.display_name_fa,
        "entry_url": row.entry_url,
        "description_fa": row.description_fa,
        "client_id": row.client_id,
        "sort_order": row.sort_order,
        "icon_emoji": row.icon_emoji,
        "is_active": row.is_active,
        "client_secret_in_env": bool(s.sso_client_secret),
        "updated_at": row.updated_at.isoformat(),
    }

# discovery cache (short-lived; portable/prod both fine)
_disc_cache: dict = {"at": 0.0, "endpoints": None}


class SsoError(Exception):
    """نقشهٔ خطا → پیام فارسی در صفحهٔ ورود (کد در ?sso_error=)."""

    def __init__(self, code: str, status: int = 302):
        self.code = code
        super().__init__(code)


def _http() -> httpx.Client:
    s = get_settings()
    return httpx.Client(timeout=s.sso_timeout_seconds, follow_redirects=True)


# ---------------------------------------------------------------- state ----
def make_state() -> str:
    s = get_settings()
    nonce = hmac.new(s.secret_key.encode(), str(time.time_ns()).encode(), hashlib.sha256).hexdigest()[:24]
    exp = int(time.time()) + s.sso_state_ttl_seconds
    payload = f"{nonce}.{exp}"
    sig = hmac.new(s.secret_key.encode(), (STATE_HMAC_PREFIX + payload).encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def verify_state(state: str) -> bool:
    if not state or state.count(".") != 2:
        return False
    payload, sig = state.rsplit(".", 1)
    s = get_settings()
    expected = hmac.new(s.secret_key.encode(), (STATE_HMAC_PREFIX + payload).encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        exp = int(payload.rsplit(".", 1)[1])
    except ValueError:
        return False
    return time.time() <= exp


# ------------------------------------------------------------ endpoints ----
def _fallback_endpoints() -> dict:
    """وقتی discovery در دسترس نیست — الگوی Keycloak سامانهٔ مرکزی (مستند در docs/06)."""
    s = get_settings()
    base = s.sso_issuer.rstrip("/")
    return {
        "authorization_endpoint": s.sso_authorize_url or f"{base}/protocol/openid-connect/auth",
        "token_endpoint": s.sso_token_url or f"{base}/protocol/openid-connect/token",
        "userinfo_endpoint": s.sso_userinfo_url or f"{base}/protocol/openid-connect/userinfo",
        "source": "manual",
    }


def resolve_endpoints() -> dict:
    """Discovery اول، سپس مقادیر دستی/پیش‌فرض. خطای شبکهٔ discovery را نادیده می‌گیرد."""
    if not _disc_cache["endpoints"] or time.time() - _disc_cache["at"] > 300:
        s = get_settings()
        eps: dict | None = None
        if s.sso_discovery:
            try:
                with _http() as c:
                    r = c.get(s.sso_issuer.rstrip("/") + "/.well-known/openid-configuration")
                    if r.status_code == 200:
                        doc = r.json()
                        eps = {k: doc[k] for k in ("authorization_endpoint", "token_endpoint", "userinfo_endpoint") if k in doc}
                        eps["source"] = "discovery"
            except Exception as exc:  # noqa: BLE001 — network unreachable is a normal fallback path
                log.warning("SSO discovery failed, using manual endpoints: %s", exc)
        if not eps:
            eps = _fallback_endpoints()
        _disc_cache["at"] = time.time()
        _disc_cache["endpoints"] = eps
    return _disc_cache["endpoints"]


def reset_endpoint_cache() -> None:
    _disc_cache["at"] = 0.0
    _disc_cache["endpoints"] = None


def redirect_uri_for(request) -> str:
    s = get_settings()
    if s.sso_redirect_uri:
        return s.sso_redirect_uri
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/auth/sso/callback"


def build_authorize_url(redirect_uri: str, state: str) -> str:
    s = get_settings()
    eps = resolve_endpoints()
    q = urlencode({
        "response_type": "code",
        "client_id": s.sso_client_id,
        "redirect_uri": redirect_uri,
        "scope": s.sso_scopes,
        "state": state,
    })
    return f"{eps['authorization_endpoint']}?{q}"


# ----------------------------------------------------------- token flow ----
def exchange_code(code: str, redirect_uri: str) -> dict:
    s = get_settings()
    eps = resolve_endpoints()
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": s.sso_client_id,
    }
    auth = None
    if s.sso_client_secret:
        form["client_secret"] = s.sso_client_secret
    try:
        with _http() as c:
            r = c.post(eps["token_endpoint"], data=form, headers={"Accept": "application/json"})
            if r.status_code == 401 and s.sso_client_secret:
                # some providers require HTTP Basic client auth instead of form field
                r = c.post(eps["token_endpoint"], data={k: v for k, v in form.items() if k != "client_secret"},
                           auth=(s.sso_client_id, s.sso_client_secret), headers={"Accept": "application/json"})
            if r.status_code != 200:
                log.warning("SSO token exchange failed status=%s body=%.200s", r.status_code, r.text)
                raise SsoError("token")
            return r.json()
    except httpx.HTTPError:
        raise SsoError("upstream") from None


def fetch_userinfo(tokens: dict) -> dict:
    eps = resolve_endpoints()
    userinfo_url = eps.get("userinfo_endpoint")
    access = tokens.get("access_token", "")
    if userinfo_url and access:
        try:
            with _http() as c:
                r = c.get(userinfo_url, headers={"Authorization": f"Bearer {access}"})
                if r.status_code == 200:
                    return r.json()
                log.warning("SSO userinfo failed status=%s", r.status_code)
        except httpx.HTTPError:
            log.warning("SSO userinfo unreachable")
    # آخرین راه‌حل مستند: payload شناسهٔ id_token بدون بررسی امضا (فقط وقتی userinfo در دسترس نیست)
    id_token = tokens.get("id_token", "")
    if id_token and id_token.count(".") == 2:
        try:
            payload_b64 = id_token.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload_b64))
            log.warning("SSO: id_token used unverified (no userinfo endpoint) — documented fallback")
            return claims
        except Exception:  # noqa: BLE001
            raise SsoError("userinfo") from None
    raise SsoError("userinfo")


# -------------------------------------------------------- provisioning ----
def _ensure_university(db: Session, code: str):
    uni = db.execute(select(University).where(University.code == code)).scalar_one_or_none()
    if uni is None:
        uni = University(code=code, name_fa=f"دانشگاه {code} (از SSO)")
        db.add(uni)
        db.flush()
    return uni


def provision_user(db: Session, claims: dict) -> User:
    """کاربر موجود را برمی‌گرداند یا بر اساس sub سامانهٔ مرکزی می‌سازد/پیوند می‌زند."""
    s = get_settings()
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise SsoError("userinfo")
    provider = "s360_oidc"

    ident = db.execute(select(ExternalIdentity).where(
        ExternalIdentity.provider == provider, ExternalIdentity.subject == subject)).scalar_one_or_none()
    if ident:
        user = db.get(User, ident.user_id)
        if user and user.is_active:
            return user
        raise SsoError("disabled")

    # پیوند با کاربر محلی — فقط حساب‌های بدون رمز (هرگز حساب‌های رمزدار: ریسک تصاحب حساب).
    # ارتقای نقش حساب‌های موجود فقط به‌صورت دستی توسط مدیر انجام می‌شود.
    candidate_name = str(claims.get("preferred_username") or claims.get("email") or "").strip().lower()
    user = None
    if candidate_name:
        cand = db.execute(select(User).where(User.username == candidate_name)).scalar_one_or_none()
        if cand is not None and not cand.password_hash:  # passwordless → safe to link
            user = cand
        elif cand is not None:
            candidate_name = ""  # name collision with a protected account → new distinct username
    if user is None and claims.get("email"):
        cand = db.execute(select(User).where(User.email == claims["email"])).scalar_one_or_none()
        if cand is not None and not cand.password_hash:
            user = cand

    if user is None:
        username = candidate_name or f"sso-{subject[:24]}"
        if db.execute(select(User).where(User.username == username)).scalar_one_or_none() is not None:
            username = f"sso-{subject[:24]}"
        if db.execute(select(User).where(User.username == username)).scalar_one_or_none() is not None:
            username = f"sso-{subject[:24]}-{int(utcnow().timestamp())}"
        user = User(username=username, display_name=str(claims.get("name") or username),
                    email=claims.get("email") or None, identity_mode="oidc", is_demo=False)
        db.add(user)
        db.flush()
        uni = _ensure_university(db, s.sso_default_university_code)
        db.add(UserRoleScope(user_id=user.id, role_code=s.sso_default_role, university_id=uni.id,
                             note="تأمین خودکار حساب از طریق ورود یکپارچهٔ SSO"))
    db.add(ExternalIdentity(provider=provider, subject=subject, user_id=user.id,
                            username_at_provider=candidate_name or None))
    db.flush()
    return user


# ------------------------------------------------------------ top flow ----
def handle_callback(db: Session, code: str, state: str, redirect_uri: str) -> User:
    s = get_settings()
    if not s.sso_enabled:
        raise SsoError("disabled")
    if not verify_state(state):
        raise SsoError("state")
    if not code:
        raise SsoError("token")
    tokens = exchange_code(code, redirect_uri)
    claims = fetch_userinfo(tokens)
    user = provision_user(db, claims)
    db.add(AuthAudit(user_id=user.id, event="sso_login_ok", detail_json=json.dumps(
        {"provider": "s360_oidc", "sub": str(claims.get("sub", ""))[:64]}, ensure_ascii=False)))
    return user
