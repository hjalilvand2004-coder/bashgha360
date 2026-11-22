"""Transactional Outbox (ARC-04): reliable in-DB event publication, at-least-once dispatch.

Consumers must be idempotent — effects are deduplicated by Inbox/unique keys/Idempotency.
"""
from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.db import Base, utcnow
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger("app.outbox")

# handler registry: aggregate+kind -> callable(session, payload) ; handlers must be idempotent
HANDLERS: dict[str, Callable[[Session, dict], None]] = {}


def handler(kind: str):
    def deco(fn):
        HANDLERS[kind] = fn
        return fn
    return deco


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    university_id: Mapped[str | None] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(Text)  # JSON text; minimal, no sensitive data
    state: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|dispatched|failed|dead
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    available_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)


def emit(db: Session, kind: str, payload: dict, university_id: str | None = None, message_id: str | None = None) -> None:
    import json
    import uuid

    db.add(OutboxMessage(id=message_id or str(uuid.uuid4()), university_id=university_id,
                         kind=kind, payload=json.dumps(payload, ensure_ascii=False, default=str)))


def process_pending(db: Session, limit: int = 50) -> int:
    """Dispatch due messages. At-least-once; errors recorded with backoff, dead-letter after cap."""
    import json
    from datetime import timedelta

    rows = db.execute(
        select(OutboxMessage).where(OutboxMessage.state.in_(["pending", "failed"]))
        .order_by(OutboxMessage.created_at.asc()).limit(limit)
    ).scalars().all()
    processed = 0
    for msg in rows:
        if msg.available_at and msg.available_at > utcnow():
            continue
        fn = HANDLERS.get(msg.kind)
        try:
            if fn is None:
                raise LookupError(f"no handler for kind={msg.kind}")
            fn(db, json.loads(msg.payload))
            msg.state = "dispatched"
            msg.last_error = None
        except Exception as exc:  # noqa: BLE001 — record and backoff
            db.rollback()
            msg = db.get(OutboxMessage, msg.id)
            msg.attempts = (msg.attempts or 0) + 1
            msg.last_error = str(exc)[:500]
            if msg.attempts >= 5:
                msg.state = "dead"
            else:
                msg.state = "failed"
                msg.available_at = utcnow() + timedelta(seconds=2 ** msg.attempts)
            log.warning("outbox dispatch failed kind=%s err=%s", msg.kind, exc)
        processed += 1
    db.commit()
    return processed
