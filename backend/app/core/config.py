"""Core configuration — all values overridable via environment / .env (TECH-06, CFG)."""
from __future__ import annotations

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "باشگاه۳۶۰"
    environment: str = "development"  # development | test | production
    seed_label: str = "demo"  # label shown in UI for sample data
    secret_key: str = "dev-only-change-me-in-production-32bytes"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    require_mfa: bool = False  # ACC-14 — must be enabled for operational deployments
    require_policy_signoff: bool = False  # CFG-03 — block real operation until essential policies approved
    database_url: str = ""  # empty => resolved dynamically (dev fallback: local pgserver socket)
    redis_url: str = ""  # empty => inline job runner (dev); in prod set redis://redis:6379/0
    queue_backend: str = "auto"  # auto | celery | inline
    enable_simulators: bool = True  # ARC-05 — false removes simulator adapters from runtime
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    rate_limit_per_minute: int = 240
    default_reservation_ttl_minutes: int = 30
    k_anonymity_threshold: int = 5  # ANA-03
    webhook_ts_window_seconds: int = 300
    cookie_secure: bool = False  # set true behind TLS in production

    # ---- SSO (ورود یکپارچه با هویت دانشجو۳۶۰) — OIDC Authorization Code ----
    sso_enabled: bool = True
    sso_issuer: str = "http://188.212.96.235:8086"  # سامانهٔ مرکزی دانشجو۳۶۰
    sso_client_id: str = "club360"
    sso_client_secret: str = ""  # via env in real deployment
    sso_scopes: str = "openid profile email"
    sso_discovery: bool = True  # try {issuer}/.well-known/openid-configuration first
    sso_authorize_url: str = ""  # manual overrides (used when discovery is off/unreachable)
    sso_token_url: str = ""
    sso_userinfo_url: str = ""
    sso_redirect_uri: str = ""  # default: computed from the incoming request
    sso_default_university_code: str = "UNI-A"
    sso_default_role: str = "student"
    sso_timeout_seconds: int = 8
    sso_state_ttl_seconds: int = 600

    @property
    def is_prod(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_database_url() -> str:
    """DATABASE_URL env wins. Dev fallback: embedded local PostgreSQL (pgserver) socket.

    In docker-compose the DATABASE_URL env is always provided, so the fallback is
    only active in this sandbox / local dev — documented in docs/03.
    """
    s = get_settings()
    if s.database_url:
        return s.database_url
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url
    try:  # dev-only fallback — never used in production compose
        import pgserver  # type: ignore

        uri = pgserver.get_server(os.environ.get("LOCAL_PGDATA", "/home/z/my-project/.pgdata")).get_uri()
        return uri.replace("/postgres", "/club360_dev")
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("DATABASE_URL is not configured and local pg fallback failed") from exc


def resolve_test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if url:
        return url
    return resolve_database_url().replace("club360_dev", "club360_test")
