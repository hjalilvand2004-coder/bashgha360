"""Structured logging with correlation-id middleware and PII masking (SEC-10, DM-06, OBS-01/02)."""
from __future__ import annotations

import json
import logging
import re
import sys
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

SENSITIVE_KEYS = {"password", "token", "access_token", "refresh", "secret", "authorization", "national_ref", "phone", "email"}
MASK = "***"
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+")


def mask_value(key: str, value):
    if isinstance(value, str):
        if "@" in value and key.lower() in SENSITIVE_KEYS:
            return MASK
        if key.lower() in SENSITIVE_KEYS:
            return MASK
    if isinstance(value, dict):
        return mask_dict(value)
    if key.lower() in SENSITIVE_KEYS:
        return MASK
    return value


def mask_dict(d: dict) -> dict:
    return {k: (MASK if k.lower() in SENSITIVE_KEYS else mask_value(k, v)) for k, v in d.items()}


def mask_text(text: str) -> str:
    return _EMAIL_RE.sub(MASK, text or "")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_text(record.getMessage()),
        }
        cid = getattr(record, "correlation_id", None)
        if cid:
            base["correlation_id"] = cid
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns a correlation id to every request; echoes it back (OBS-02)."""

    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex[:16]
        request.state.correlation_id = cid
        import logging

        logging.getLogger("app.request").info(
            "%s %s", request.method, request.url.path, extra={"correlation_id": cid}
        )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
