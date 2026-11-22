"""system endpoints: info (mode transparency), healthz, readyz, metrics (OBS)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text as sqltext
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.db import engine, get_db

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info")
def system_info():
    s = get_settings()
    return {
        "app_name": s.app_name,
        "environment": s.environment,
        "integration_mode": "simulator" if s.enable_simulators else "oidc_pending_approval",
        "queue_backend": "celery" if s.redis_url else "inline_runner_dev",
        "seed_label": s.seed_label,
        "require_mfa": s.require_mfa,
        "policy_signoff_required": s.require_policy_signoff,
        "notes": [
            "اتصال هویت/LMS در این محیط «آزمایشی» است؛ ادعای اتصال واقعی نمی‌شود.",
            "اعداد سیاست‌ها نمونهٔ Demo برچسب‌خورده است، نه مصوبهٔ دانشگاه.",
        ],
    }


health_router = APIRouter(tags=["ops"])


@health_router.get("/healthz")
def healthz():
    return {"status": "ok"}


@health_router.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(sqltext("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}


@health_router.get("/metrics")
def metrics():
    from ...core.db import TestingSession

    s = TestingSession()
    try:
        pend = s.execute(sqltext("SELECT count(*) FROM outbox_messages WHERE state='pending'")).scalar() or 0
        dead = s.execute(sqltext("SELECT count(*) FROM outbox_messages WHERE state='dead'")).scalar() or 0
        inbox = s.execute(sqltext("SELECT count(*) FROM event_inbox WHERE state='received'")).scalar() or 0
        quar = s.execute(sqltext("SELECT count(*) FROM event_inbox WHERE state='quarantined'")).scalar() or 0
        jobs = s.execute(sqltext("SELECT count(*) FROM background_jobs WHERE state IN ('queued','failed')")).scalar() or 0
        return Response(content=(
            f"# HELP bashgah_queue_depth outbox/inbox depth\n"
            f"# TYPE bashgah_queue_depth gauge\n"
            f"bashgah_outbox_pending {pend}\n"
            f"bashgah_outbox_dead {dead}\n"
            f"bashgah_inbox_pending {inbox}\n"
            f"bashgah_inbox_quarantined {quar}\n"
            f"bashgah_jobs_pending {jobs}\n"), media_type="text/plain")
    finally:
        s.close()
