#!/usr/bin/env python3
"""Reset dev/test database (truncate all domain tables) and optionally re-seed.

Usage: python scripts/reset_db.py [--seed] [--test]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import sqlalchemy  # noqa: E402

if "--test" in sys.argv:
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:@/club360_test?host=/home/z/my-project/.pgdata")
else:
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:@/club360_dev?host=/home/z/my-project/.pgdata")

from app.core.db import engine, Base  # noqa: E402
from app import models_registry  # noqa: E402,F401

tables = [t for t in Base.metadata.tables if t != "alembic_version"]
e = engine
with e.begin() as c:
    c.execute(sqlalchemy.text("SET CONSTRAINTS ALL DEFERRED"))
    quoted = ", ".join(f'"{t}"' for t in sorted(tables))
    c.execute(sqlalchemy.text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
print(f"truncated {len(tables)} tables")
if "--seed" in sys.argv:
    from app.seed import main

    main()
