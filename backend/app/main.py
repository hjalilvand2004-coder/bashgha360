"""باشگاه۳۶۰ — FastAPI application (modular monolith entry point)."""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import get_settings
from .core.errors import ApiError, install_error_handlers
from .core.logging import CorrelationIdMiddleware, setup_logging
from .core.security import decode_access_token
from . import models_registry  # noqa: F401 — ensure all models registered

setup_logging()
log = logging.getLogger("app")

settings = get_settings()

app = FastAPI(
    title="باشگاه۳۶۰ (Bashgah360) API",
    version="1.0.0",
    description="زیرسیستم ۱۷ اکوسیستم دانشجو۳۶۰ — باشگاه هوشمند پیشرفت، مشارکت و تجربهٔ دانشجو",
    docs_url="/api/docs", openapi_url="/api/v1/openapi.json",
    redirect_slashes=False,
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)


@app.middleware("http")
async def rate_limit_and_csrf(request: Request, call_next):
    """Simple in-memory rate limit (Redis in prod) + Origin check for cookie-auth unsafe methods (SEC)."""
    from collections import defaultdict

    if not hasattr(app.state, "rl"):
        app.state.rl = defaultdict(list)
    now = time.time()
    key = request.client.host if request.client else "anon"
    window = [t for t in app.state.rl[key] if now - t < 60]
    if len(window) > settings.rate_limit_per_minute:
        return JSONResponse(status_code=429, content={"code": "RATE_LIMITED", "message": "تعداد درخواست بیش از حد مجاز است.",
                                                      "correlation_id": getattr(request.state, "correlation_id", "-"), "details": {}})
    window.append(now)
    app.state.rl[key] = window

    if request.method in ("POST", "PATCH", "PUT", "DELETE"):
        origin = request.headers.get("origin")
        auth = request.headers.get("authorization", "")
        # cookie-based refresh/logout need same-origin; bearer-token calls are CSRF-safe by design
        if origin and not auth and request.url.path.startswith("/api/v1/auth"):
            allowed = [o.strip() for o in settings.cors_origins.split(",")]
            if origin not in allowed:
                return JSONResponse(status_code=403, content={"code": "CSRF_ORIGIN", "message": "منشأ درخواست مجاز نیست.",
                                                              "correlation_id": getattr(request.state, "correlation_id", "-"), "details": {}})
    return await call_next(request)


install_error_handlers(app)

# ---- routers (API-01: /api/v1 prefix, 26 groups) ----
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pathlib import Path  # noqa: E402

from .modules.identity_access.router import router as auth_router, sso_router, sso_settings_router  # noqa: E402
from .modules.memberships_consents.router import router as memberships_router, consents_router  # noqa: E402
from .modules.student_goals.router import goals_extra_router  # noqa: E402
from .modules.event_ingestion.router import router as events_router  # noqa: E402
from .modules.policy_engine.router import (router as policies_router, approvals_router,  # noqa: E402
                                           sim_router)
from .modules.points_ledger.router import router as points_router, ledger_router  # noqa: E402
from .modules.achievements_tiers.router import (router as tiers_router, badges_router,  # noqa: E402
                                                missions_router, groups_router)
from .modules.rewards_fulfillment.router import (router as rewards_router, req_router,  # noqa: E402
                                                 prov_router)
from .modules.recommendations.router import (rec_router, notif_router, analytics_router,  # noqa: E402
                                             audit_router, reviews_router, appeals_router, goals_router, dc_router)
from .modules.integrations.system_router import router as system_router, health_router  # noqa: E402
from .modules.club_experience.router import router as club_experience_router  # noqa: E402
from .modules.student_life.router import router as student_life_router  # noqa: E402

API = "/api/v1"
for r in (auth_router, sso_router, sso_settings_router, memberships_router, consents_router, goals_extra_router, events_router,
          policies_router, approvals_router, sim_router, points_router, ledger_router,
          tiers_router, badges_router, missions_router, groups_router, rewards_router, req_router,
          prov_router, rec_router, notif_router, analytics_router, audit_router, reviews_router,
          appeals_router, goals_router, dc_router, system_router, health_router, club_experience_router,
          student_life_router):
    app.include_router(r, prefix=API)


@app.get("/")
def root():
    return {"app": settings.app_name, "docs": "/api/docs", "system": f"{API}/system/info"}


# private file serving with short-lived signature (SEC-09)
_files_dir = Path(__file__).resolve().parent.parent / "private_files"
_files_dir.mkdir(exist_ok=True)


@app.get("/api/v1/files/{key:path}")
def private_file(key: str, expires: int = 0, signature: str = ""):
    import hashlib
    import time

    from fastapi.responses import FileResponse

    from .core.errors import NotFound

    if expires < time.time() or not signature:
        raise NotFound("لینک نامعتبر یا منقضی است.")
    expected = hashlib.sha256(f"{settings.secret_key}:{key}:{expires}".encode()).hexdigest()[:32]
    if signature != expected:
        raise NotFound("لینک نامعتبر است.")
    path = (_files_dir / key).resolve()
    if not str(path).startswith(str(_files_dir)) or not path.exists():
        raise NotFound("فایل یافت نشد.")
    return FileResponse(path)


@app.on_event("startup")
def on_startup():
    from .shared.jobs import start_inline_runner

    if not settings.redis_url:
        start_inline_runner()  # dev/sandbox; production uses Celery worker+beat (transparent via /system/info)
    log.info("startup complete env=%s queue=%s", settings.environment,
             "celery" if settings.redis_url else "inline")


# Celery app for production (TECH-03) — same job functions, Redis broker
def create_celery():
    from celery import Celery

    from .shared import jobs as jobs_mod
    from .shared.jobs import JOB_FUNCS

    c = Celery("bashgah360", broker=settings.redis_url or "redis://redis:6379/0",
               backend=settings.redis_url or "redis://redis:6379/1")

    c.conf.beat_schedule = {
        "process-events-every-10s": {"task": "bashgah.tick", "schedule": 10.0},
        "sweep-expired-every-60s": {"task": "bashgah.tick", "schedule": 60.0},
    }

    @c.task(name="bashgah.tick")
    def tick():
        from .core.db import TestingSession
        from .modules.event_ingestion.service import retry_due_inboxes
        from .modules.rewards_fulfillment.service import sweep_expired
        from .shared.jobs import run_due_jobs
        from .shared.outbox import process_pending

        s = TestingSession()
        try:
            retry_due_inboxes(s, limit=100)
            process_pending(s)
            run_due_jobs()
            sweep_expired(s)
            s.commit()
        finally:
            s.close()
        return "tick"

    return c


# Celery app for production (TECH-03) — same job functions, Redis broker.
# celery/redis are optional at runtime: portable deployments run the inline runner.
try:
    celery_app = create_celery()
except Exception:  # pragma: no cover — ImportError path (portable bundle without celery)
    celery_app = None
    log.info("celery/redis not installed — inline runner will be used")
