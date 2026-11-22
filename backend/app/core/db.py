"""Database engine/session + declarative Base (ADR-2: SQLAlchemy 2.0 sync)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import resolve_database_url

engine = create_engine(resolve_database_url(), pool_pre_ping=True, pool_size=10, max_overflow=10)
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=True, expire_on_commit=False)

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


def get_db():
    """Request-scoped Unit of Work: one transaction per request, commit on success."""
    db = TestingSession(bind=engine)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
