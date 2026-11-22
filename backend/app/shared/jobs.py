"""Background jobs registry + inline runner (TECH-03).

Production: Celery workers/beat execute the same `run_job` functions via Redis broker.
Dev/sandbox (no Redis): `start_inline_runner` thread polls due jobs — transparent via /system/info.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, TestingSession, utcnow

log = logging.getLogger("app.jobs")

JOB_FUNCS: dict[str, Callable[..., object]] = {}


def job(name: str):
    def deco(fn):
        JOB_FUNCS[name] = fn
        return fn
    return deco


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    university_id: Mapped[str | None] = mapped_column(String(36), index=True)
    job_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    state: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued|running|done|failed|dead
    run_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)


def enqueue(db, job_type: str, payload: dict, run_at=None, university_id: str | None = None, job_id: str | None = None) -> str:
    import json
    import uuid

    jid = job_id or str(uuid.uuid4())
    db.add(BackgroundJob(id=jid, university_id=university_id, job_type=job_type,
                         payload=json.dumps(payload, ensure_ascii=False, default=str), run_at=run_at or utcnow()))
    return jid


def run_due_jobs(limit: int = 30) -> int:
    """Execute due jobs exactly-once-effect: state claim via UPDATE guard."""
    import json

    s = TestingSession()
    ran = 0
    try:
        rows = s.execute(
            select(BackgroundJob)
            .where(BackgroundJob.state.in_(["queued", "failed"]))
            .where(BackgroundJob.run_at <= utcnow())
            .order_by(BackgroundJob.run_at.asc()).limit(limit)
        ).scalars().all()
        for j in rows:
            fn = JOB_FUNCS.get(j.job_type)
            j.state = "running"
            s.commit()
            try:
                if fn is None:
                    raise LookupError(f"no job func {j.job_type}")
                result = fn(s, json.loads(j.payload))
                j = s.get(BackgroundJob, j.id)
                j.state, j.result = "done", json.dumps(result if result is not None else {}, ensure_ascii=False, default=str)[:2000]
            except Exception as exc:  # noqa: BLE001
                s.rollback()
                j = s.get(BackgroundJob, j.id)
                j.attempts += 1
                j.last_error = str(exc)[:500]
                if j.attempts >= 5:
                    j.state = "dead"
                else:
                    j.state = "failed"
                    from datetime import timedelta

                    j.run_at = utcnow() + timedelta(seconds=2 ** j.attempts)
                log.warning("job failed type=%s err=%s", j.job_type, exc)
            ran += 1
        s.commit()
    finally:
        s.close()
    return ran


_inline_thread: threading.Thread | None = None
_stop = threading.Event()


def start_inline_runner(interval_seconds: float = 3.0) -> None:
    """Dev/sandbox runner. In production use Celery worker+beat instead."""
    global _inline_thread

    def loop():
        from .outbox import process_pending

        while not _stop.is_set():
            try:
                run_due_jobs()
                s = TestingSession()
                try:
                    process_pending(s)
                finally:
                    s.close()
            except Exception:  # noqa: BLE001
                log.exception("inline runner cycle error")
            _stop.wait(interval_seconds)

    if _inline_thread is None or not _inline_thread.is_alive():
        _stop.clear()
        _inline_thread = threading.Thread(target=loop, name="bg-runner", daemon=True)
        _inline_thread.start()
