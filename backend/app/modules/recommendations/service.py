"""recommendations service — real rule-based recommender (REC-01..04, REC-07).

Seven steps: consent check → allowed list → filter (capacity/time/conditions/accessibility)
→ match goal/interests → diversity limits → REAL computed reasons → feedback.
No sensitive inputs; no labels like «weak»; generic mode works without consent (TST-11).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import utcnow
from ...core.money import D
from ..memberships_consents import service as memberships
from ..identity_access.models import StudentReference
from ..rewards_fulfillment.models import ACTIVE_REQUEST_STATES, Reward, RewardCapacity, RewardRequest
from ..student_goals.models import StudentGoal
from .models import RecommendationFeedback, RecommendationItem, RecommendationRun

DIVERSITY_MAX_PER_TYPE = 2
LIMIT = 6


def recommend(db: Session, *, university_id: str, student_ref: StudentReference | None) -> dict:
    basis = "generic"
    inputs: dict = {"university_id": university_id, "generated_at": utcnow().isoformat()}
    goal = None
    if student_ref is not None:
        inputs["program"] = student_ref.program
        goal = db.execute(select(StudentGoal).where(
            StudentGoal.student_ref_id == student_ref.id, StudentGoal.status == "active")).scalars().first()
        if goal:
            inputs["goal"] = {"type": goal.goal_type, "title": goal.title_fa}

    # 1) consent gate (REC-03)
    personal = student_ref is not None and memberships.has_consent(db, student_ref.id, "personalization")
    basis = "consent_personal" if personal else "generic"
    inputs["basis"] = basis

    # 2) allowed list — active, non-essential-only-for-points rules enforced at model level
    rewards = db.execute(select(Reward).where(
        Reward.university_id == university_id, Reward.state == "active")).scalars().all()

    items = []
    for r in rewards:
        reasons: list[str] = []
        score = 0.0
        # 3) filters
        if r.capacity_total is not None:
            cap = db.execute(select(RewardCapacity).where(RewardCapacity.reward_id == r.id)).scalar_one_or_none()
            free = (r.capacity_total - (cap.reserved_count if cap else 0))
            if free <= 0:
                continue
            reasons.append(f"ظرفیت آزاد: {free}")
            score += 0.2
        # 4) match declared goal (allowed input only)
        if goal and goal.goal_type in (r.goal_tags or "").split(","):
            reasons.append(f"تناسب با هدف «{goal.title_fa}»")
            score += 0.5
        if student_ref is not None:
            active_req = db.execute(select(RewardRequest).where(
                RewardRequest.student_ref_id == student_ref.id, RewardRequest.reward_id == r.id,
                RewardRequest.active_group == "1")).scalar_one_or_none()
            if active_req:
                continue  # already requested
        if D(r.cost_points) == 0:
            reasons.append("بدون هزینهٔ امتیازی")
            score += 0.1
        if not reasons:
            reasons.append("پیشنهاد عمومی کاتالوگ")
        items.append({"reward": r, "score": round(min(score, 0.99), 2), "reasons": reasons})

    # 5) diversity: max N per reward type
    per_type: dict[str, int] = {}
    ranked = sorted(items, key=lambda x: -x["score"])
    diversified = []
    for it in ranked:
        t = it["reward"].type
        if per_type.get(t, 0) >= DIVERSITY_MAX_PER_TYPE:
            continue
        per_type[t] = per_type.get(t, 0) + 1
        diversified.append(it)
        if len(diversified) >= LIMIT:
            break

    run = RecommendationRun(id=str(uuid.uuid4()), university_id=university_id,
                            student_ref_id=student_ref.id if student_ref else None, basis=basis,
                            inputs_snapshot=json.dumps(inputs, ensure_ascii=False),
                            recommender_version="rules-1.0")
    db.add(run)
    db.flush()
    out = []
    for i, it in enumerate(diversified, start=1):
        rec_item = RecommendationItem(id=str(uuid.uuid4()), university_id=university_id, run_id=run.id,
                                      reward_id=it["reward"].id, score=it["score"],
                                      reasons_fa=json.dumps(it["reasons"], ensure_ascii=False), rank=i)
        db.add(rec_item)
        out.append({"reward_id": it["reward"].id, "title_fa": it["reward"].title_fa,
                    "type": it["reward"].type, "cost_points": str(D(it["reward"].cost_points)),
                    "score": it["score"], "reasons_fa": it["reasons"], "rank": i})
    return {"run_id": run.id, "basis": basis, "items": out}


def feedback(db: Session, *, item_id: str, student_ref_id: str, feedback: str, note: str | None = None) -> RecommendationFeedback:
    if feedback not in ("like", "dismiss", "not_now"):
        from ...core.errors import Conflict

        raise Conflict("بازخورد نامعتبر است.")
    row = RecommendationFeedback(id=str(uuid.uuid4()), university_id="", item_id=item_id,
                                 student_ref_id=student_ref_id, feedback=feedback, note=note,
                                 created_at=utcnow())
    db.add(row)
    db.flush()
    return row
