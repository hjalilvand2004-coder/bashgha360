"""rewards_fulfillment service — catalog + request state machine (RWD-01..11).

Key guarantees:
- capacity + points reserved in ONE local transaction (RWD-05, TST-03)
- TTL release by sweeper (RWD-07, TST-20)
- unknown delivery => reconciliation first; NO auto refund (RWD-08, TST-09)
- no double delivery (one receipt per request)
"""
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.db import utcnow
from ...core.errors import Conflict, CapacityExhausted, Forbidden, InsufficientPoints, NotFound
from ...core.money import D, ZERO
from ..points_ledger import service as ledger
from ..memberships_consents.models import Membership
from ..identity_access.models import StudentReference
from .models import (ACTIVE_REQUEST_STATES, DeliveryReceipt, FulfillmentAttempt, ReconciliationCase,
                     Reward, RewardCapacity, RewardProvider, RewardRequest, RewardReservation)

STATE_TRANSITIONS = {
    "requested": {"reserved", "rejected", "cancelled"},
    "reserved": {"approved", "rejected", "cancelled", "expired"},
    "approved": {"fulfilling", "rejected", "cancelled"},
    "fulfilling": {"delivered", "failed", "unknown", "cancelled"},
    "delivered": {"refunded"},
    "failed": {"refunded"},
    "unknown": {"delivered", "failed"},
    "rejected": set(), "cancelled": set(), "expired": set(), "refunded": set(),
}


def transition(request: RewardRequest, new_state: str) -> RewardRequest:
    if new_state not in STATE_TRANSITIONS.get(request.state, set()):
        raise Conflict(f"گذار «{request.state} → {new_state}» مجاز نیست.")
    request.state = new_state
    if new_state in STATE_TRANSITIONS and new_state not in ACTIVE_REQUEST_STATES:
        request.active_group = "0"
    return request


def check_conditions(db: Session, reward: Reward, student_ref: StudentReference) -> bool:
    cond = json.loads(reward.conditions_json or "{}")
    programs = cond.get("programs")
    if programs and student_ref.program not in programs:
        return False
    return True


def request_reward(db: Session, *, university_id: str, student_ref: StudentReference, reward_id: str,
                   actor: str, idempotency_key: str | None = None) -> RewardRequest:
    """Single-tx reserve of capacity + points (RWD-05)."""
    reward = db.get(Reward, reward_id)
    if reward is None or str(reward.university_id) != str(university_id) or reward.state != "active":
        raise NotFound("پاداش یافت نشد یا فعال نیست.")
    membership = db.execute(select(Membership).where(Membership.student_ref_id == student_ref.id)).scalar_one_or_none()
    if membership is None or membership.state not in ("active", "paused"):
        raise Forbidden("برای درخواست پاداش باید عضو باشگاه باشید.")
    if not check_conditions(db, reward, student_ref):
        raise Forbidden("شرایط این پاداش (رشته/مهارت/زمان) برای شما برآورده نیست.")

    dup = db.execute(select(RewardRequest).where(
        RewardRequest.student_ref_id == student_ref.id, RewardRequest.reward_id == reward.id,
        RewardRequest.active_group == "1")).scalar_one_or_none()
    if dup is not None:
        raise Conflict("شما یک درخواست فعال برای همین پاداش دارید.")

    ttl = timedelta(minutes=get_settings().default_reservation_ttl_minutes)
    req = RewardRequest(id=str(uuid.uuid4()), university_id=university_id, student_ref_id=student_ref.id,
                        reward_id=reward.id, state="requested", requested_at=utcnow(),
                        ttl_expires_at=utcnow() + ttl, active_group="1")
    db.add(req)
    db.flush()

    cost = D(reward.cost_points)
    points_tx = None
    if cost > 0:
        points_tx, _ = ledger.reserve(
            db, university_id, student_ref.id, cost,
            idempotency_key=idempotency_key or f"reward:{req.id}:reserve",
            reward_request_id=req.id, reason_fa=f"رزرو امتیاز برای پاداش «{reward.title_fa}»", actor=actor)

    capacity = None
    if reward.capacity_total is not None:
        cap = db.execute(select(RewardCapacity).where(
            RewardCapacity.reward_id == reward.id).with_for_update()).scalar_one_or_none()
        if cap is None:
            cap = RewardCapacity(id=str(uuid.uuid4()), university_id=university_id, reward_id=reward.id,
                                 total=int(reward.capacity_total), reserved_count=0, final_count=0)
            try:
                with db.begin_nested():
                    db.add(cap)
                    db.flush()
            except Exception:  # noqa: BLE001 — concurrent create: unique constraint wins, re-lock
                cap = db.execute(select(RewardCapacity).where(
                    RewardCapacity.reward_id == reward.id).with_for_update()).scalar_one()
        if cap.reserved_count >= cap.total:
            raise CapacityExhausted("ظرفیت این پاداش تکمیل شده است.")  # TST-03: exactly one winner
        cap.reserved_count += 1
        capacity = cap

    db.add(RewardReservation(id=str(uuid.uuid4()), university_id=university_id, request_id=req.id,
                             capacity_id=capacity.id if capacity else None,
                             points_tx_id=points_tx.id if points_tx else "",
                             expires_at=req.ttl_expires_at))
    db.flush()
    transition(req, "reserved")
    return req


def approve(db: Session, request: RewardRequest, approver: str) -> RewardRequest:
    transition(request, "approved")
    request.decided_by, request.decided_at = approver, utcnow()
    reward = db.get(Reward, request.reward_id)
    if reward and reward.delivery == "external" and reward.provider_id:
        db.add(FulfillmentAttempt(id=str(uuid.uuid4()), university_id=request.university_id,
                                  request_id=request.id, attempt_no=1, state="created",
                                  detail_json=json.dumps({"provider_id": reward.provider_id})))
    return request


def start_fulfilling(db: Session, request: RewardRequest, actor: str) -> RewardRequest:
    return transition(request, "fulfilling")


def deliver_in_app(db: Session, request: RewardRequest, actor: str) -> str:
    """Generate one-time code + receipt; reserved → spent. Code returned once (RWD-07)."""
    if db.execute(select(DeliveryReceipt).where(DeliveryReceipt.request_id == request.id)).scalar_one_or_none():
        raise Conflict("این درخواست قبلاً رسید تحویل دارد.")  # no double delivery
    reward = db.get(Reward, request.reward_id)
    transition(request, "delivered")
    request.decided_by, request.decided_at = actor, utcnow()
    if reward and D(reward.cost_points) > 0:
        ledger.spend(db, request.university_id, request.student_ref_id, D(reward.cost_points),
                     idempotency_key=f"reward:{request.id}:spend", reward_request_id=request.id,
                     reason_fa=f"تحویل پاداش «{reward.title_fa}»", actor=actor)
    code = secrets.token_urlsafe(18)
    db.add(DeliveryReceipt(id=str(uuid.uuid4()), university_id=request.university_id, request_id=request.id,
                           one_time_code_hash=hashlib.sha256(code.encode()).hexdigest(),
                           issued_at=utcnow(), receipt_json=json.dumps(
                               {"title_fa": reward.title_fa if reward else "", "delivered_at": utcnow().isoformat()})))
    _capacity_final(db, request, +1)
    if reward and reward.provider_id:
        _notify_provider_and_student(db, request, "delivered")
    else:
        _notify_student(db, request, "پاداش شما تحویل شد.")
    return code


def _capacity_final(db: Session, request: RewardRequest, delta: int) -> None:
    res = db.execute(select(RewardReservation).where(RewardReservation.request_id == request.id)).scalar_one_or_none()
    if res and res.capacity_id:
        cap = db.get(RewardCapacity, res.capacity_id)
        if cap:
            cap.final_count = max(0, cap.final_count + delta)


def mark_failed(db: Session, request: RewardRequest, reason_fa: str, actor: str) -> RewardRequest:
    """failed → release reservation (points + capacity)."""
    transition(request, "failed")
    request.cancel_reason_fa = reason_fa
    _release_reservation(db, request, idem=f"reward:{request.id}:release-failed", actor=actor)
    _notify_student(db, request, f"تحویل پاداش ناموفق بود: {reason_fa}")
    return request


def cancel(db: Session, request: RewardRequest, actor: str, reason_fa: str = "لغو توسط دانشجو") -> RewardRequest:
    if request.state in ("delivered", "refunded"):
        raise Conflict("درخواست تحویل‌شده قابل لغو نیست؛ مسیر استرداد طبق سیاست جداگانه است.")
    transition(request, "cancelled")
    request.cancel_reason_fa = reason_fa
    _release_reservation(db, request, idem=f"reward:{request.id}:release-cancel", actor=actor)
    return request


def _release_reservation(db: Session, request: RewardRequest, *, idem: str, actor: str) -> None:
    res = db.execute(select(RewardReservation).where(RewardReservation.request_id == request.id)).scalar_one_or_none()
    if res is None or res.released_at is not None:
        return
    reward = db.get(Reward, request.reward_id)
    if reward and D(reward.cost_points) > 0 and res.points_tx_id:
        ledger.release(db, request.university_id, request.student_ref_id, D(reward.cost_points),
                       idempotency_key=idem, reward_request_id=request.id,
                       reason_fa="آزادسازی رزرو پاداش", actor=actor)
    if res.capacity_id:
        cap = db.get(RewardCapacity, res.capacity_id)
        if cap and cap.reserved_count > 0:
            cap.reserved_count -= 1
    res.released_at = utcnow()


def provider_callback(db: Session, *, provider_id: str, request_ref: str, result: str, report: dict | None = None) -> dict:
    """External delivery callback (RWD-06). unknown ⇒ reconciliation, never auto refund (TST-09)."""
    request = db.execute(select(RewardRequest).where(RewardRequest.id == request_ref)).scalar_one_or_none()
    if request is None:
        raise NotFound("درخواست ارجاع‌شده یافت نشد.")
    reward = db.get(Reward, request.reward_id)
    if reward is None or reward.provider_id != provider_id:
        raise Forbidden("این درخواست متعلق به ارائه‌دهندهٔ شما نیست.")
    if result == "confirmed":
        code = deliver_in_app(db, request, actor=f"provider:{provider_id}")
        return {"state": request.state, "one_time_code": code}
    if result == "failed":
        mark_failed(db, request, "ارائه‌دهنده تحویل را ناموفق اعلام کرد.", actor=f"provider:{provider_id}")
        return {"state": request.state}
    # unknown
    transition(request, "unknown")
    db.add(ReconciliationCase(id=str(uuid.uuid4()), university_id=request.university_id,
                              request_id=request.id, detected_at=utcnow(),
                              provider_report=json.dumps(report or {}, ensure_ascii=False)))
    return {"state": "unknown", "note": "پروندهٔ آشتی‌سازی ایجاد شد؛ تصمیم انسانی لازم است."}


def reconcile(db: Session, case: ReconciliationCase, resolution: str, decided_by: str) -> RewardRequest:
    """Human decision on unknown delivery (RWD-08)."""
    request = db.get(RewardRequest, case.request_id)
    if resolution == "delivered":
        deliver_in_app(db, request, actor=f"reconciliation:{decided_by}")
    elif resolution == "failed":
        mark_failed(db, request, "نتیجهٔ آشتی‌سازی: تحویل ناموفق.", actor=f"reconciliation:{decided_by}")
    else:
        raise Conflict("نتیجهٔ آشتی‌سازی باید delivered یا failed باشد.")
    case.resolution, case.resolved_by, case.resolved_at = resolution, decided_by, utcnow()
    att = db.execute(select(FulfillmentAttempt).where(FulfillmentAttempt.request_id == request.id)
                     .order_by(FulfillmentAttempt.attempt_no.desc())).scalars().first()
    if att:
        att.state, att.result_at = "reconciled", utcnow()
    return request


def sweep_expired(db: Session) -> int:
    """TTL sweeper (TST-20): release expired reservations of points + capacity."""
    rows = db.execute(select(RewardRequest).where(
        RewardRequest.state == "reserved",
        RewardRequest.ttl_expires_at.is_not(None),
        RewardRequest.ttl_expires_at < utcnow(),
    )).scalars().all()
    n = 0
    for req in rows:
        transition(req, "expired")
        req.cancel_reason_fa = "انقضای مهلت تأیید رزرو (TTL)."
        _release_reservation(db, req, idem=f"reward:{req.id}:release-expired", actor="system:sweeper")
        n += 1
    return n


def _notify_student(db: Session, request: RewardRequest, body_fa: str) -> None:
    from ..notifications import service as notif
    from ..identity_access.models import StudentReference

    sref = db.get(StudentReference, request.student_ref_id)
    if sref and sref.user_id:
        notif.notify(db, university_id=request.university_id, user_id=str(sref.user_id),
                     kind="reward_delivery", title_fa="وضعیت پاداش", body_fa=body_fa,
                     transactional=True, dedupe_key=f"reward:{request.id}:{body_fa[:12]}")


def _notify_provider_and_student(db: Session, request: RewardRequest, state: str) -> None:
    _notify_student(db, request, "تحویل پاداش تأیید شد؛ کد مصرف در بخش «درخواست‌ها» است.")
