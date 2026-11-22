"""Policy engine — versioned JSON DSL rules, no eval (PNT-01..10, PRN-08).

Evaluation is pure/deterministic; caps are enforced concurrency-safe via row-locked
`policy_cap_usage`; calculation trace is stored for every decision.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import utcnow
from ...core.errors import ValidationError
from ...core.money import D, ROUNDING_NAME, ZERO, mul
from ..points_ledger import service as ledger
from .models import Policy, PolicyCapUsage, PolicyVersion, RuleEvaluation

ALLOWED_OPS = {"==", "!=", ">", ">=", "<", "<=", "in", "not_in", "between"}


@dataclass
class RuleSpec:
    rule_id: str
    event_type: str
    base_points: Decimal
    conditions: dict = field(default_factory=dict)
    quality_multiplier: dict = field(default_factory=dict)
    progress_multiplier: dict = field(default_factory=dict)
    repeat_policy: dict = field(default_factory=dict)
    caps: dict = field(default_factory=dict)
    exclusive_group: str | None = None
    late_policy: dict = field(default_factory=dict)
    path: str = "learning"  # learning | skill | collaboration
    evidence_required: bool = False
    human_reason_template: str = "دستاورد تأییدشده ثبت شد"


def validate_dsl(dsl: dict) -> RuleSpec:
    """Strict allowlisted validation — no eval / python / arbitrary SQL (PNT-02)."""
    try:
        rule_id = str(dsl["rule_id"])
        event_type = str(dsl["event_type"])
        base = D(dsl["base_points"])
    except (KeyError, TypeError) as exc:
        raise ValidationError(f"DSL نامعتبر: فیلد الزامی {exc}") from exc
    if not rule_id or not event_type:
        raise ValidationError("DSL نامعتبر: rule_id/event_type خالی است.")
    if base < 0:
        raise ValidationError("امتیاز پایه نمی‌تواند منفی باشد.")

    def check_conditions(c: dict, where: str) -> None:
        if not isinstance(c, dict):
            raise ValidationError(f"شرط نامعتبر در {where}")
        if "all" in c:
            for item in c["all"]:
                check_conditions(item, where)
            return
        op = c.get("op")
        if op not in ALLOWED_OPS:
            raise ValidationError(f"عملگر «{op}» مجاز نیست. عملگرهای مجاز: {sorted(ALLOWED_OPS)}")
        if not isinstance(c.get("field"), str):
            raise ValidationError("فیلد شرط باید رشته باشد.")

    check_conditions(dsl.get("conditions", {}), "conditions")
    rp = dsl.get("repeat_policy") or {}
    if rp and not isinstance(rp.get("diminishing", []), list):
        raise ValidationError("diminishing باید آرایه باشد.")
    caps = dsl.get("caps") or {}
    for k in caps:
        if k not in ("per_day", "per_period", "per_activity"):
            raise ValidationError(f"نوع سقف «{k}» پشتیبانی نمی‌شود.")
    return RuleSpec(
        rule_id=rule_id, event_type=event_type, base_points=base,
        conditions=dsl.get("conditions") or {},
        quality_multiplier=dsl.get("quality_multiplier") or {"default": "1.00"},
        progress_multiplier=dsl.get("progress_multiplier") or {"default": "1.00"},
        repeat_policy=rp, caps=caps, exclusive_group=dsl.get("exclusive_group"),
        late_policy=dsl.get("late_policy") or {}, path=dsl.get("path", "learning"),
        evidence_required=bool(dsl.get("evidence_required", False)),
        human_reason_template=dsl.get("human_reason_template", "دستاورد تأییدشده ثبت شد"),
    )


def _resolve(field_path: str, ctx: dict):
    cur = ctx
    for part in field_path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _eval_condition(cond: dict, ctx: dict) -> bool:
    if "all" in cond:
        return all(_eval_condition(c, ctx) for c in cond["all"])
    if "any" in cond:
        return any(_eval_condition(c, ctx) for c in cond["any"])
    val = _resolve(cond["field"], ctx)
    op, target = cond["op"], cond.get("value")
    try:
        if op == "==":
            return val == target
        if op == "!=":
            return val != target
        v = D(val) if val is not None else None
        t = D(target)
        if op == ">":
            return v is not None and v > t
        if op == ">=":
            return v is not None and v >= t
        if op == "<":
            return v is not None and v < t
        if op == "<=":
            return v is not None and v <= t
        if op == "in":
            return val in (target or [])
        if op == "not_in":
            return val not in (target or [])
        if op == "between":
            lo, hi = target or [0, 0]
            return v is not None and D(lo) <= v <= D(hi)
    except Exception:  # noqa: BLE001 — malformed comparison = not matched
        return False
    return False


def evaluate(spec: RuleSpec, ctx: dict) -> tuple[bool, dict, dict, Decimal]:
    """Pure evaluation → (matched, conditions_result, effective_inputs, candidate_points)."""
    cond_res = {"all": [_eval_condition(c, ctx) for c in spec.conditions.get("all", [])]}
    matched = all(cond_res["all"]) if cond_res["all"] else True
    effective = {"base_points": str(spec.base_points)}
    q = spec.quality_multiplier or {}
    quality = _resolve(q.get("field", ""), ctx) if q.get("field") else None
    q_val = D((q.get("map") or {}).get(str(quality), q.get("default", "1.00")))
    p_val = D((spec.progress_multiplier or {}).get("default", "1.00"))
    candidate = spec.base_points
    for factor, name in ((q_val, "quality"), (p_val, "progress")):
        candidate = mul(candidate, factor)
        effective[f"{name}_multiplier"] = str(factor)
    effective["candidate_before_repeat"] = str(candidate)
    return matched, cond_res, effective, candidate


def select_versions_for_event(db: Session, university_id: str, event_type: str, occurred_at: datetime) -> list[tuple[Policy, PolicyVersion, RuleSpec]]:
    """Published versions whose window covers occurred_at (TST-02: out-of-order by event time)."""
    rows = db.execute(
        select(Policy, PolicyVersion)
        .join(PolicyVersion, PolicyVersion.policy_id == Policy.id)
        .where(Policy.university_id == university_id)
        .where(PolicyVersion.status == "published")
        .where(PolicyVersion.effective_from <= occurred_at)
    ).all()
    out = []
    for policy, version in rows:
        if version.effective_to and occurred_at > version.effective_to:
            continue
        try:
            spec = validate_dsl(json.loads(version.dsl_json))
        except ValidationError:
            continue
        if spec.event_type != event_type:
            continue
        out.append((policy, version, spec))
    # A policy's versions supersede each other: the one in force at occurred_at
    # (latest effective_from, then highest version_no) is the only candidate (PNT-06, TST-02).
    best: dict[str, tuple[Policy, PolicyVersion, RuleSpec]] = {}
    for policy, version, spec in out:
        key = str(policy.id)
        cur = best.get(key)
        if cur is None or (version.effective_from, version.version_no) > (cur[1].effective_from, cur[1].version_no):
            best[key] = (policy, version, spec)
    return list(best.values())


def _window_key(university_tz: str, occurred_at: datetime, kind: str, period_id: str | None) -> str:
    tz = ZoneInfo(university_tz or "Asia/Tehran")
    local = occurred_at.astimezone(tz)
    if kind == "day":
        return f"day:{local.date().isoformat()}"
    if kind == "period":
        return f"period:{period_id or 'none'}"
    return f"activity:{period_id or 'none'}"


def apply_caps_and_repeat(db: Session, *, university_tz: str, student_ref_id: str, version: PolicyVersion,
                          spec: RuleSpec, candidate: Decimal, occurred_at: datetime,
                          period_id: str | None) -> tuple[Decimal, dict, str | None]:
    """Diminishing returns + caps, concurrency-safe (PNT-09 / TST-19)."""
    caps_applied: dict = {}
    final = candidate

    repeat = spec.repeat_policy or {}
    if repeat.get("window_days"):
        since = occurred_at - timedelta(days=int(repeat["window_days"]))
        prior = db.execute(select(RuleEvaluation).where(
            RuleEvaluation.student_ref_id == student_ref_id,
            RuleEvaluation.version_id == version.id,
            RuleEvaluation.matched.is_(True),
            RuleEvaluation.created_at >= since,
        )).scalars().all()
        idx = len(prior)
        dim = repeat.get("diminishing") or ["1.00"]
        factor = D(dim[idx]) if idx < len(dim) else D(repeat.get("beyond", "0"))
        final = mul(final, factor)
        caps_applied["repeat_index"] = idx
        caps_applied["repeat_factor"] = str(factor)

    for cap_kind in ("per_day", "per_period"):
        cap_val = (spec.caps or {}).get(cap_kind)
        if not cap_val:
            continue
        key = _window_key(university_tz, occurred_at, "day" if cap_kind == "per_day" else "period", period_id)
        usage = db.execute(select(PolicyCapUsage).where(
            PolicyCapUsage.student_ref_id == student_ref_id,
            PolicyCapUsage.version_id == version.id,
            PolicyCapUsage.window_key == key,
        ).with_for_update()).scalar_one_or_none()
        if usage is None:
            usage = PolicyCapUsage(id=str(__import__("uuid").uuid4()), university_id=version.university_id,
                                   student_ref_id=student_ref_id, version_id=version.id, window_key=key, used=ZERO)
            try:
                with db.begin_nested():
                    db.add(usage)
                    db.flush()
            except Exception:  # noqa: BLE001 — concurrent insert, re-lock
                usage = db.execute(select(PolicyCapUsage).where(
                    PolicyCapUsage.student_ref_id == student_ref_id,
                    PolicyCapUsage.version_id == version.id,
                    PolicyCapUsage.window_key == key).with_for_update()).scalar_one()
        cap = D(cap_val)
        room = cap - D(usage.used)
        if room <= 0:
            caps_applied[cap_kind] = {"cap": str(cap), "used": str(usage.used), "granted": "0.00", "cut": True}
            final = ZERO
            continue
        if final > room:
            caps_applied[cap_kind] = {"cap": str(cap), "used": str(usage.used), "granted_before_cut": str(final),
                                      "cut": True}
            final = room
        else:
            caps_applied[cap_kind] = {"cap": str(cap), "used": str(usage.used), "cut": False}
        if final > 0:
            usage.used = D(usage.used) + final

    return final, caps_applied, ROUNDING_NAME


def process_verified_event(db: Session, *, university_id: str, university_tz: str, event, student_ref_id: str,
                           period_id: str | None) -> dict:
    """Full path: rule selection → evaluation → exclusive group → caps → ledger award → trace."""
    versions = select_versions_for_event(db, university_id, event.event_type, event.occurred_at)
    if not versions:
        return {"status": "no_rule", "reason": "قاعدهٔ منتشرشده‌ای برای این رویداد وجود ندارد."}

    ctx = {"event": {"event_type": event.event_type, "activity_reference": event.activity_reference,
                     "occurred_at": event.occurred_at.isoformat(), "verification_status": event.verification_status},
           "payload": json.loads(event.payload_json or "{}")}

    candidates = []
    for policy, version, spec in versions:
        matched, cond_res, effective, candidate = evaluate(spec, ctx)
        ev = RuleEvaluation(id=str(__import__("uuid").uuid4()), university_id=university_id,
                            event_id=event.id, version_id=version.id, student_ref_id=student_ref_id,
                            matched=matched, conditions_result=json.dumps(cond_res, ensure_ascii=False),
                            effective_inputs=json.dumps(effective, ensure_ascii=False))
        db.add(ev)
        if matched:
            candidates.append((policy, version, spec, candidate, ev))
    if not candidates:
        return {"status": "not_matched", "reason": "شرایط هیچ قاعده‌ای برآورده نشد."}

    # exclusive groups: keep the best-priority rule per group (PNT-08)
    best: dict[str, tuple] = {}
    standalone = []
    for item in candidates:
        policy, version, spec, candidate, ev = item
        if spec.exclusive_group:
            cur = best.get(spec.exclusive_group)
            if cur is None or policy.priority < cur[0].priority:
                if cur is not None:
                    cur[4].excluded_reason_fa = "مشمول گروه انحصاری — قاعدهٔ دارای تقدم بالاتر اعمال شد."
                best[spec.exclusive_group] = item
            else:
                ev.excluded_reason_fa = "مشمول گروه انحصاری — قاعدهٔ دارای تقدم بالاتر اعمال شد."
        else:
            standalone.append(item)

    results = []
    for policy, version, spec, candidate, ev in [*best.values(), *standalone]:
        final, caps_applied, rounding = apply_caps_and_repeat(
            db, university_tz=university_tz, student_ref_id=student_ref_id, version=version,
            spec=spec, candidate=candidate, occurred_at=event.occurred_at, period_id=period_id)
        reason = spec.human_reason_template.format(
            activity_reference=event.activity_reference) if "{activity_reference}" in spec.human_reason_template else spec.human_reason_template
        ev.final_points, ev.caps_applied, ev.rounding, ev.human_reason_fa = final, json.dumps(caps_applied, ensure_ascii=False), rounding, reason
        if final > 0:
            tx, created = ledger.award(
                db, university_id, student_ref_id, final,
                to_bucket="available" if event.verification_status == "verified" else "pending",
                idempotency_key=f"event:{event.university_id}:{event.event_id}:{version.id}",
                event_id=event.id, rule_version_id=version.id, reason_fa=reason, actor="system:policy_engine",
                reference=event.activity_reference)
            ev.tx_id = tx.id
            results.append({"rule": spec.rule_id, "version": version.id, "points": str(final),
                            "tx_id": tx.id, "created": created, "caps": caps_applied})
        else:
            ev.excluded_reason_fa = ev.excluded_reason_fa or "بر اساس سقف مصوب، امتیازی تخصیص نیافت."
            results.append({"rule": spec.rule_id, "version": version.id, "points": "0.00", "caps": caps_applied})
    return {"status": "awarded", "results": results}
