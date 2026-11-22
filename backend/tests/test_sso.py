"""SSO (ورود یکپارچه) tests: state امضاشده، callback تأمین کاربر، خطاهای ساختاریافته.

Real HTTP is mocked at the httpx client boundary (no external IdP needed).
"""
from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app
from app.modules.identity_access import sso as sso_svc
from app.modules.identity_access.models import ExternalIdentity, User, UserRoleScope


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def fake_idp(monkeypatch):
    """Mock the SSO HTTP surface: discovery + token + userinfo."""
    calls = {"token": 0, "userinfo": 0, "discovery": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/.well-known/openid-configuration"):
            calls["discovery"] += 1
            return httpx.Response(200, json={
                "authorization_endpoint": "http://sso.test/authorize",
                "token_endpoint": "http://sso.test/token",
                "userinfo_endpoint": "http://sso.test/userinfo",
            })
        if url == "http://sso.test/token":
            calls["token"] += 1
            assert request.read().decode().startswith("grant_type=authorization_code")
            return httpx.Response(200, json={"access_token": "AT1", "token_type": "bearer", "id_token": "x.y.z"})
        if url == "http://sso.test/userinfo":
            calls["userinfo"] += 1
            assert request.headers["Authorization"] == "Bearer AT1"
            return httpx.Response(200, json={
                "sub": "s360-sub-1", "preferred_username": "ali@s360.demo",
                "email": "ali@s360.demo", "name": "علی دانشجو",
            })
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    sso_svc.reset_endpoint_cache()
    monkeypatch.setattr(sso_svc, "_http", lambda: httpx.Client(transport=transport, timeout=5))
    yield calls
    sso_svc.reset_endpoint_cache()


def test_sso_status(client):
    r = client.get("/api/v1/auth/sso/status")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert "188.212.96.235:8086" in body["issuer"]


def test_sso_login_redirects_to_idp(client, fake_idp):
    r = client.get("/api/v1/auth/sso/login")
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("http://sso.test/authorize?")
    assert "client_id=club360" in loc and "response_type=code" in loc
    assert "state=" in loc


def test_sso_callback_tampered_state_rejected(client, fake_idp, db):
    r = client.get("/api/v1/auth/sso/callback?code=abc&state=dead.beef.00", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].startswith("/login?sso_error=state")
    assert fake_idp["token"] == 0  # never reached the IdP
    # audit trail for failure exists
    from app.modules.identity_access.models import AuthAudit

    assert db.query(AuthAudit).filter(AuthAudit.event == "sso_login_ok").count() == 0


def test_sso_callback_provisions_new_student(client, fake_idp, db, uni):
    state = sso_svc.make_state()
    assert sso_svc.verify_state(state)
    r = client.get(f"/api/v1/auth/sso/callback?code=good&state={state}", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/"
    assert "refresh" in r.headers.get("set-cookie", "")

    user = db.query(User).filter(User.username == "ali@s360.demo").one()
    assert user.identity_mode == "oidc" and user.is_demo is False
    ident = db.query(ExternalIdentity).filter(ExternalIdentity.subject == "s360-sub-1").one()
    assert ident.user_id == user.id
    roles = db.query(UserRoleScope).filter(UserRoleScope.user_id == user.id).all()
    assert [x.role_code for x in roles] == ["student"]

    # refresh cookie round-trip → access token → /me works
    cookie = r.headers["set-cookie"].split(";")[0]
    r2 = client.post("/api/v1/auth/refresh", headers={"Cookie": cookie})
    assert r2.status_code == 200
    r3 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r2.json()['access_token']}"})
    assert r3.status_code == 200
    assert r3.json()["display_name"] == "علی دانشجو"
    assert "student" in r3.json()["roles"]


def test_sso_second_login_links_same_user(client, fake_idp, db, uni):
    s1 = sso_svc.make_state()
    client.get(f"/api/v1/auth/sso/callback?code=good&state={s1}", follow_redirects=False)
    s2 = sso_svc.make_state()
    r2 = client.get(f"/api/v1/auth/sso/callback?code=good&state={s2}", follow_redirects=False)
    assert r2.status_code == 302 and r2.headers["location"] == "/"
    assert db.query(User).filter(User.username == "ali@s360.demo").count() == 1


def test_sso_never_takes_over_password_protected_account(client, fake_idp, db, uni):
    """امنیت: حساب رمزدار محلی با هم‌نامی هرگز از طریق SSO تصاحب نمی‌شود."""
    from app.core.security import hash_password

    db.add(User(username="ali@s360.demo", display_name="علی (محلی)", password_hash=hash_password("pw"),
                identity_mode="local"))
    db.flush()
    state = sso_svc.make_state()
    r = client.get(f"/api/v1/auth/sso/callback?code=good&state={state}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/"
    users = db.query(User).filter(User.username == "ali@s360.demo").all()
    assert len(users) == 1 and users[0].identity_mode == "local"  # untouched
    # a separate SSO user was created with a distinct username
    sso_users = db.query(User).filter(User.identity_mode == "oidc").all()
    assert len(sso_users) == 1 and sso_users[0].username != "ali@s360.demo"
    assert sso_users[0].password_hash is None
    assert db.query(ExternalIdentity).filter(ExternalIdentity.user_id == sso_users[0].id).count() == 1


def test_sso_links_passwordless_account_by_username(client, fake_idp, db, uni):
    """حساب بدون رمز (مثلاً ساخته‌شده قبلی) با هم‌نامی پیوند می‌شود."""
    db.add(User(username="ali@s360.demo", display_name="علی (بدون رمز)", identity_mode="oidc"))
    db.flush()
    state = sso_svc.make_state()
    r = client.get(f"/api/v1/auth/sso/callback?code=good&state={state}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/"
    users = db.query(User).filter(User.username == "ali@s360.demo").all()
    assert len(users) == 1
    assert db.query(ExternalIdentity).filter(ExternalIdentity.user_id == users[0].id).count() == 1


def test_sso_provisioning_never_grants_privileged_roles(client, fake_idp, db, uni):
    """Rec-01/ACC principle: SSO تأمین می‌کند ولی هیچ نقش مدیریتی از توکن نمی‌آید."""
    import httpx as _hx

    def handler(request: _hx.Request) -> _hx.Response:
        if str(request.url).endswith("/userinfo"):
            return _hx.Response(200, json={
                "sub": "s360-admin-claim", "preferred_username": "evil@s360.demo",
                "name": "مدیر ادعایی", "roles": ["club_manager", "tech_admin"],
            })
        if str(request.url).endswith("/token"):
            return _hx.Response(200, json={"access_token": "AT2"})
        return _hx.Response(200, json={
            "authorization_endpoint": "http://sso.test/authorize",
            "token_endpoint": "http://sso.test/token",
            "userinfo_endpoint": "http://sso.test/userinfo",
        })

    transport = _hx.MockTransport(handler)
    old = sso_svc._http
    sso_svc._http = lambda: _hx.Client(transport=transport, timeout=5)
    try:
        state = sso_svc.make_state()
        r = client.get(f"/api/v1/auth/sso/callback?code=good&state={state}", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == "/"
    finally:
        sso_svc._http = old
        sso_svc.reset_endpoint_cache()
    roles = {x.role_code for x in db.query(UserRoleScope).all()}
    assert roles == {"student"}  # privileged claims ignored


# ---------------- تنظیمات ورود یکپارچه (ثبت سامانه در پورتال) ----------------
def _login_as(db, user_id, uni_id, roles):
    """Override get_principal (same pattern as test_api_contract)."""
    from app.core.rbac import get_principal, make_principal_for_tests

    p = make_principal_for_tests(user_id, uni_id, roles)
    app.dependency_overrides[get_principal] = lambda: p
    return p


def test_sso_status_shows_portal_registration_defaults(client, db):
    """پیش‌فرض‌های ثبت سامانه همان مقادیر پورتال مرکزی است (کلید/نام/آیکن/فعال)."""
    r = client.get("/api/v1/auth/sso/status")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["app_key"] == "daneshjooclub"
    assert body["display_name_fa"] == "باشگاه دانشجو۳۶۰"
    assert body["icon_emoji"] == "🥇"
    assert body["is_active"] is True
    assert body["entry_url"].startswith("http://188.212.96.235:8089/")


def test_sso_settings_read_update_roundtrip(client, db, uni):
    """مدیر باشگاه تنظیمات را می‌بیند و تغییر می‌دهد؛ آدیت هم ثبت می‌شود."""
    _login_as(db, "mgr-1", uni.id, ["club_manager"])
    r = client.get("/api/v1/admin/sso-settings")
    assert r.status_code == 200
    body = r.json()
    assert body["client_id"] == "daneshjooclub360"
    assert body["sort_order"] == 14
    assert body["redirect_uri"].endswith("/api/v1/auth/sso/callback")

    r2 = client.put("/api/v1/admin/sso-settings", json={
        "app_key": "daneshjooclub", "display_name_fa": "باشگاه دانشجو۳۶۰",
        "entry_url": "https://club.u1.ir/api/v1/auth/sso/login",
        "description_fa": "امتیاز، کارت خدمات و امکانات دانشجویی",
        "client_id": "daneshjooclub360", "sort_order": 15, "icon_emoji": "🏅", "is_active": True,
    })
    assert r2.status_code == 200
    assert r2.json()["entry_url"] == "https://club.u1.ir/api/v1/auth/sso/login"
    assert r2.json()["sort_order"] == 15 and r2.json()["icon_emoji"] == "🏅"

    from app.modules.audit.models import AuditLog
    assert db.query(AuditLog).filter(AuditLog.action == "auth.sso_settings.update").count() == 1


def test_sso_settings_requires_manager(client, db, uni):
    """دانشجو/ناشناس مجاز به دیدن یا تغییر تنظیمات نیست."""
    r = client.get("/api/v1/admin/sso-settings")
    assert r.status_code == 401
    _login_as(db, "stu-1", uni.id, ["student"])
    r2 = client.get("/api/v1/admin/sso-settings")
    assert r2.status_code == 403
    r3 = client.put("/api/v1/admin/sso-settings", json={
        "app_key": "x", "display_name_fa": "x", "entry_url": "http://x.ir", "client_id": "x"})
    assert r3.status_code == 403


def test_sso_settings_validation(client, db, uni):
    """آدرس ورود باید http/https باشد؛ در غیر این صورت خطای ساختاریافتهٔ 422."""
    _login_as(db, "mgr-1", uni.id, ["club_manager"])
    r = client.put("/api/v1/admin/sso-settings", json={
        "app_key": "daneshjooclub", "display_name_fa": "باشگاه دانشجو۳۶۰",
        "entry_url": "not-a-url", "client_id": "daneshjooclub360"})
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"
