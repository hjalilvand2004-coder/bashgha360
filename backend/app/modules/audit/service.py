"""audit service — append-only trail for sensitive actions (SEC-11, DM-03)."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ...core.db import utcnow
from ..audit.models import AuditLog


def write(db: Session, *, actor: str | None, action: str, entity: str, entity_id: str | None = None,
          before: dict | None = None, after: dict | None = None, university_id: str | None = None,
          correlation_id: str | None = None, ip_masked: str | None = None) -> AuditLog:
    row = AuditLog(actor=(actor or "system")[:64], action=action[:80], entity=entity[:60],
                   entity_id=entity_id, before_json=json.dumps(before, ensure_ascii=False, default=str)[:4000] if before else None,
                   after_json=json.dumps(after, ensure_ascii=False, default=str)[:4000] if after else None,
                   university_id=university_id, correlation_id=correlation_id, ip_masked=ip_masked)
    db.add(row)
    db.flush()
    return row
