"""Shared: UoW with bounded retry for serialization failures (LED-09), pagination helper."""
from __future__ import annotations

import random
import time
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.db import TestingSession
from ..core.errors import Conflict


@contextmanager
def uow(session_factory=TestingSession, retries: int = 3) -> Iterator[Session]:
    """A transactional unit; retries bounded on deadlock/serialization (LED-09)."""
    attempt = 0
    while True:
        s = session_factory()
        try:
            yield s
            s.commit()
            return
        except Exception as exc:
            s.rollback()
            is_retryable = isinstance(getattr(exc, "orig", None), Exception) and any(
                k in str(getattr(exc, "orig", "")).lower()
                for k in ("deadlock detected", "could not serialize", "40001", "40P01")
            )
            if is_retryable and attempt < retries - 1:
                attempt += 1
                time.sleep(0.05 * attempt + random.random() * 0.05)
                continue
            raise
        finally:
            s.close()


class Page:
    def __init__(self, items, total: int, page: int, page_size: int):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size

    def as_dict(self):
        return {"items": self.items, "total": self.total, "page": self.page, "page_size": self.page_size}


def paginate(query, page: int = 1, page_size: int = 20):
    page = max(1, min(int(page), 10_000))
    page_size = max(1, min(int(page_size), 100))  # API-02: bounded
    total = query.session.execute(query.statement.with_only_columns(func.count()).order_by(None)).scalar() or 0
    rows = query.limit(page_size).offset((page - 1) * page_size).all()
    return Page(rows, int(total), page, page_size)
