"""points + ledger endpoints (PRN-08, PNT-05, LED)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...core.errors import NotFound
from ...core.money import D
from ...core.rbac import Principal, require
from ...modules.points_ledger.models import LedgerTransaction, PointAccount
from ...modules.points_ledger.service import tx_trace
from ...shared.uow import paginate

router = APIRouter(prefix="/points", tags=["points"])
ledger_router = APIRouter(prefix="/ledger", tags=["ledger"])


def _summary(db: Session, student_ref_id: str) -> dict:
    acc = db.execute(select(PointAccount).where(PointAccount.student_ref_id == student_ref_id)).scalar_one_or_none()
    if acc is None:
        return {"available": "0.00", "pending": "0.00", "reserved": "0.00",
                "cumulative_progress": "0.00", "spent_total": "0.00", "expired_total": "0.00"}
    return {"available": str(D(acc.available)), "pending": str(D(acc.pending)), "reserved": str(D(acc.reserved)),
            "cumulative_progress": str(D(acc.cumulative_progress)), "spent_total": str(D(acc.spent_total)),
            "expired_total": str(D(acc.expired_total))}


@router.get("/summary")
def points_summary(principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """Two independent concepts: spendable balance vs cumulative progress (LED-02)."""
    return _summary(db, principal.student_ref_id)


@ledger_router.get("")
def my_ledger(page: int = 1, page_size: int = 20,
              principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    if not principal.student_ref_id:
        return {"items": [], "total": 0, "page": 1, "page_size": page_size}
    page_obj = paginate(db.query(LedgerTransaction).filter(LedgerTransaction.student_ref_id == principal.student_ref_id)
                        .order_by(LedgerTransaction.created_at.desc()), page, page_size)
    items = [{"id": t.id, "tx_type": t.tx_type, "reason_fa": t.reason_fa, "event_id": t.event_id,
              "rule_version_id": t.rule_version_id, "reward_request_id": t.reward_request_id,
              "correction_of": t.correction_of_tx_id, "created_at": t.created_at.isoformat(),
              "trace_link": f"/api/v1/ledger/{t.id}/trace"} for t in page_obj.items]
    return {"items": items, "total": page_obj.total, "page": page_obj.page, "page_size": page_obj.page_size}


@ledger_router.get("/{tx_id}/trace")
def ledger_trace(tx_id: str, principal: Principal = Depends(require("ledger:read_own")), db: Session = Depends(get_db)):
    """Rules & reasons for allocation / non-allocation / correction — visible & appealable (PRN-08)."""
    tx = db.get(LedgerTransaction, tx_id)
    if tx is None:
        raise NotFound("تراکنش یافت نشد.")
    if "ledger:read" not in principal.permissions and tx.student_ref_id != (principal.student_ref_id or ""):
        raise NotFound("تراکنش یافت نشد.")  # do not leak existence
    return tx_trace(db, tx_id)
