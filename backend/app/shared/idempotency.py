"""API-level Idempotency for sensitive commands (API-04, LED-06).

First call executes and stores response; same key+payload returns stored response;
same key+different payload => 409 IDEMPOTENCY_CONFLICT.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

from fastapi import Request, Response
from sqlalchemy import DateTime, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, utcnow
from ..core.errors import IdempotencyConflict


class ApiIdempotency(Base):
    __tablename__ = "api_idempotency"
    __table_args__ = (UniqueConstraint("key", name="uq_api_idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    key: Mapped[str] = mapped_column(String(120), index=True)
    actor: Mapped[str] = mapped_column(String(64))
    request_hash: Mapped[str] = mapped_column(String(64))
    status_code: Mapped[str] = mapped_column(String(8))
    response_body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def _body_hash(request: Request, body: bytes) -> str:
    return hashlib.sha256(f"{request.method}|{request.url.path}|{body.decode('utf-8', 'replace')}".encode()).hexdigest()


def idempotent_response(request: Request, db, actor: str, key: str, body: bytes, execute) -> Response:
    """execute() -> (status_code, dict). Uses stored response when key+hash match."""
    rh = _body_hash(request, body)
    existing = db.execute(select(ApiIdempotency).where(ApiIdempotency.key == key)).scalar_one_or_none()
    if existing is not None:
        if existing.request_hash != rh:
            raise IdempotencyConflict("همین کلید Idempotency با محتوای متفاوت قبلاً استفاده شده است.")
        return Response(content=existing.response_body, status_code=int(existing.status_code), media_type="application/json")
    status, payload = execute()
    db.add(ApiIdempotency(id=str(uuid.uuid4()), key=key[:120], actor=actor[:64] or "service", request_hash=rh,
                          status_code=str(status), response_body=json.dumps(payload, ensure_ascii=False, default=str),
                          created_at=utcnow()))
    return Response(content=json.dumps(payload, ensure_ascii=False, default=str), status_code=status, media_type="application/json")
