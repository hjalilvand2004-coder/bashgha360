"""Structured errors — every failure is machine-readable: code, message, correlation_id (API-03)."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message_fa: str, code: str | None = None, status_code: int | None = None, details: dict | None = None):
        super().__init__(message_fa)
        self.message_fa = message_fa
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}


class ValidationError(ApiError):
    status_code, code = 422, "VALIDATION_ERROR"


class Unauthorized(ApiError):
    status_code, code = 401, "UNAUTHORIZED"


class Forbidden(ApiError):
    status_code, code = 403, "FORBIDDEN"


class NotFound(ApiError):
    status_code, code = 404, "NOT_FOUND"


class Conflict(ApiError):
    status_code, code = 409, "CONFLICT"


class IdempotencyConflict(ApiError):
    status_code, code = 409, "IDEMPOTENCY_CONFLICT"


class CapacityExhausted(ApiError):
    status_code, code = 409, "CAPACITY_EXHAUSTED"


class InsufficientPoints(ApiError):
    status_code, code = 409, "INSUFFICIENT_POINTS"


def correlation_id_from_request(request: Request) -> str:
    return getattr(request.state, "correlation_id", "-")


def install_error_handlers(app) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message_fa,
                "correlation_id": correlation_id_from_request(request),
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        import logging

        logging.getLogger("app").exception("unhandled_error")
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "خطای داخلی سامانه. شناسه پیگیری خود را نگه دارید.",
                "correlation_id": correlation_id_from_request(request),
                "details": {},
            },
        )
