"""event_ingestion service — contract validation, auth, dedup, quarantine, corrections (EVT-01..11)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.db import utcnow
from ...core.errors import Conflict, Unauthorized, ValidationError
from ...core.security import verify_hmac
from ..identity_access.models import University
from ..integrations.adapters import EVENT_TYPES
from ..identity_access.models import StudentReference
from .models import EducationalEvent, EventCorrection, EventInbox, IntegrationSource

REQUIRED_FIELDS = [
    "event_id", "schema_version", "source_id", "university_id", "student_reference", "event_type",
    "occurred_at", "received_at", "activity_reference", "verification_status", "correlation_id",
]
ALLOWED_PAYLOAD_KEYS = {
    "duration_minutes", "quality", "course_code", "score", "skill_code", "content_ref",
    "peer_ref", "contribution_ref", "progress_level", "session_kind",
}


def parse_ts(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"فیلد {field} باید ISO-8601 با منطقهٔ زمانی باشد.") from exc


def authenticate_source(db: Session, source_id: str, university_id: str) -> IntegrationSource:
    src = db.execute(select(IntegrationSource).where(IntegrationSource.id == source_id)).scalar_one_or_none()
    if src is None or not src.is_active:
        raise Unauthorized("منبع ارسال نامعتبر یا غیرفعال است.")
    if str(src.university_id) != str(university_id):
        raise Unauthorized("منبع برای این دانشگاه مجاز نیست.")  # scope control (EVT-03)
    return src


def validate_event_payload(body: dict) -> None:
    missing = [f for f in REQUIRED_FIELDS if not body.get(f)]
    if missing:
        raise ValidationError(f"فیلدهای الزامی رویداد غایب‌اند: {', '.join(missing)}")
    if body["event_type"] not in EVENT_TYPES:
        raise ValidationError(f"نوع رویداد «{body['event_type']}» در قرارداد نیست.")
    parse_ts(body["occurred_at"], "occurred_at")
    parse_ts(body["received_at"], "received_at")
    payload = body.get("payload") or {}
    if not isinstance(payload, dict):
        raise ValidationError("payload باید شیء باشد.")
    unknown = set(payload) - ALLOWED_PAYLOAD_KEYS
    if unknown:
        raise ValidationError(f"کلیدهای payload مجاز نیستند: {', '.join(sorted(unknown))}")
    if len(json.dumps(payload)) > 65536:
        raise ValidationError("حجم payload بیش از حد مجاز است.")  # ASM-07


def _rate_ok(db: Session, source: IntegrationSource) -> bool:
    """Per-source rate limit (DB counter — Redis in production)."""
    since = utcnow() - timedelta(minutes=1)
    n = db.execute(select(func.count()).select_from(EducationalEvent).where(
        EducationalEvent.source_id == source.id, EducationalEvent.received_at >= since)).scalar()
    return int(n or 0) < int(source.rate_limit_per_min)


def ingest(db: Session, body: dict, *, raw_body: bytes = b"", signature: str = "", integration_source_id: str | None = None) -> dict:
    """Main ingestion entry. Returns inbox-level result; duplicate => no second effect (TST-01)."""
    validate_event_payload(body)
    src = db.get(IntegrationSource, integration_source_id) if integration_source_id else authenticate_source(
        db, str(body["source_id"]), str(body["university_id"]))
    if src is None:
        raise Unauthorized("منبع نامعتبر است.")
    if src.hmac_secret_ref:
        if not verify_hmac(src.hmac_secret_ref, raw_body, signature):
            raise Unauthorized("امضای پیام نامعتبر است.")  # T1/T3
    if not _rate_ok(db, src):
        raise Conflict("نرخ ارسال این منبع بیش از حد مجاز است.")

    occurred = parse_ts(body["occurred_at"], "occurred_at")
    received = parse_ts(body["received_at"], "received_at")
    now = utcnow()
    uni = db.get(University, str(body["university_id"]))

    # future events are invalid (EVT-07)
    if occurred > now + timedelta(minutes=5):
        return _quarantine(db, body, src, reason="occurred_at در آینده است.")
    # late events outside the policy window are quarantined per policy
    late_window = timedelta(hours=72)
    if now - occurred > late_window:
        return _quarantine(db, body, src, reason="رویداد دیررس خارج از پنجرهٔ سیاست است.")

    # dedup by composite key (EVT-05): (university, source, event_id)
    dup = db.execute(select(EducationalEvent).where(
        EducationalEvent.university_id == str(body["university_id"]),
        EducationalEvent.source_id == src.id,
        EducationalEvent.event_id == str(body["event_id"]),
    )).scalar_one_or_none()
    if dup is not None:
        inbox = db.execute(select(EventInbox).where(EventInbox.event_id == dup.id)).scalars().first()
        return {"duplicate": True, "inbox_state": inbox.state if inbox else "applied", "event_db_id": dup.id}

    ev = EducationalEvent(
        university_id=str(body["university_id"]), event_id=str(body["event_id"]),
        schema_version=str(body["schema_version"]), source_id=src.id,
        student_reference=str(body["student_reference"]), event_type=str(body["event_type"]),
        occurred_at=occurred, received_at=received,
        activity_reference=str(body["activity_reference"]),
        evidence_reference=body.get("evidence_reference"),
        verification_status=str(body.get("verification_status") or "verified"),
        correlation_id=str(body.get("correlation_id") or ""),
        revision=int(body.get("revision") or 1),
        reference_to_corrected_event=body.get("reference_to_corrected_event"),
        payload_json=json.dumps(body.get("payload") or {}, ensure_ascii=False),
    )
    try:
        with db.begin_nested():
            db.add(ev)
            db.flush()
    except Exception:  # unique race → treat as duplicate (TST-01)
        dup = db.execute(select(EducationalEvent).where(
            EducationalEvent.university_id == str(body["university_id"]),
            EducationalEvent.source_id == src.id,
            EducationalEvent.event_id == str(body["event_id"]))).scalar_one()
        return {"duplicate": True, "inbox_state": "applied", "event_db_id": dup.id}

    inbox = EventInbox(university_id=ev.university_id,
                       message_id=f"{src.code}:{ev.event_id}:r{ev.revision}",
                       event_id=ev.id, state="received")
    try:
        with db.begin_nested():
            db.add(inbox)
            db.flush()
    except Exception:
        return {"duplicate": True, "inbox_state": "applied", "event_db_id": ev.id}

    return {"duplicate": False, "inbox_state": "received", "event_db_id": ev.id, "inbox_id": inbox.id}


def _quarantine(db: Session, body: dict, src: IntegrationSource, reason: str) -> dict:
    db.add(EventInbox(university_id=str(body["university_id"]),
                      message_id=f"{src.code}:{body.get('event_id')}:q:{utcnow().timestamp()}",
                      event_id=None, state="quarantined", quarantined_reason=reason))
    return {"duplicate": False, "inbox_state": "quarantined", "reason": reason}


def resolve_student(db: Session, university_id: str, student_reference: str) -> StudentReference | None:
    """Local minimal snapshot lookup (S360-10) — unknown students are not invented."""
    return db.execute(select(StudentReference).where(
        StudentReference.university_id == university_id,
        StudentReference.external_student_id == student_reference)).scalar_one_or_none()


def process_inbox_message(db: Session, inbox: EventInbox) -> str:
    """Called by worker (at-least-once). Effect-dedup is guaranteed downstream (idempotent award)."""
    from ..policy_engine import service as policy
    from ..integrations.adapters import LMS_EVENT_MAP

    if inbox.state in ("applied", "rejected"):
        return inbox.state  # idempotent no-op (TST-05)
    ev = db.get(EducationalEvent, inbox.event_id)
    if ev is None:
        inbox.state, inbox.quarantined_reason = "rejected", "رویداد مرجع یافت نشد."
        return inbox.state
    sref = resolve_student(db, ev.university_id, ev.student_reference)
    if sref is None:
        inbox.state, inbox.quarantined_reason = "quarantined", "دانشجوی مرجع در Snapshot محلی یافت نشد."
        return inbox.state
    uni = db.get(University, ev.university_id)
    if ev.verification_status == "rejected":
        inbox.state = "applied"  # recorded, no points (PRN-02)
        return inbox.state
    result = policy.process_verified_event(
        db, university_id=ev.university_id, university_tz=uni.timezone if uni else "Asia/Tehran",
        event=ev, student_ref_id=str(sref.id), period_id=None)
    inbox.state = "applied"
    inbox.last_error = None

    # deterministic integrity signals (INT-02) + risk patterns (INT-03) — case only, no verdict
    try:
        from ..integrity_reviews import service as integrity

        integrity.check_event_patterns(db, university_id=ev.university_id, event=ev, student_ref_id=str(sref.id))
    except Exception:  # noqa: BLE001 — integrity checks must never break points
        pass
    return inbox.state


def retry_due_inboxes(db: Session, limit: int = 50) -> int:
    """Retry with backoff + bounded attempts (EVT-08); processed by worker/inline runner."""
    rows = db.execute(select(EventInbox).where(
        EventInbox.state.in_(["received"]),
        (EventInbox.next_retry_at.is_(None)) | (EventInbox.next_retry_at <= utcnow()),
    ).order_by(EventInbox.created_at.asc()).limit(limit)).scalars().all()

    processed = 0
    for inbox in rows:
        try:
            process_inbox_message(db, inbox)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            inbox = db.get(EventInbox, inbox.id)
            inbox.attempts += 1
            inbox.last_error = str(exc)[:400]
            if inbox.attempts >= 5:
                inbox.state, inbox.quarantined_reason = "quarantined", "سقف تلاش پردازش پر شد."
            else:
                inbox.next_retry_at = utcnow() + timedelta(seconds=2 ** inbox.attempts)
        processed += 1
    db.commit()
    return processed
