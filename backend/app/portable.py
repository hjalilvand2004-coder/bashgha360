"""حالت Portable — اجرای کامل باشگاه دانشجو۳۶۰ روی هر سیستم بدون PostgreSQL/Redis/Python.

اجرا:  python -m app.portable   (از ریشهٔ بستهٔ قابل‌حمل)
نشانی:  http://<سرور>:8089   (پیش‌فرض؛ با CLUB360_PORT/CLUB360_HOST تغییر کنید)

تفاوت با استقرار عملیاتی (مستند در docs/12):
  - پایگاه‌داده: SQLite فایلی در data/club360.db به‌جای PostgreSQL —
    PostgreSQL همچنان مرجع رسمی عملیات است (ADR در docs/03)؛ این حالت برای
    اجرای سریع/آزمایش/پایلوت کوچک است.
  - صف کارها: اجرای درون‌خطی (inline) به‌جای Celery+Redis.
  - مهاجرت‌ها: ساخت اسکیما با create_all به‌جای Alembic.
  - ledger_entries.seq در SQLite با شمارندهٔ داخل پردازش جایگزین می‌شود
    (فقط برای ترتیب رکوردها؛ حساب‌ها همچنان از جمع رکوردها بازسازی می‌شوند).
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

# ریشهٔ بستهٔ قابل‌حمل: CLUB360_BASE (از start.bat) بر همه‌چیز مقدم است؛
# وگرنه پدر پکیج app (هم‌جا با runtime/ web/ data/ start.bat).
# دلیل: در پایتونِ جاسازی‌شدهٔ ویندوز (python312._pth) محل فیزیکی app ممکن است
# site-packages باشد؛ پس مبنای data/web/.env را لانچر تعیین می‌کند.
BASE_DIR = Path(os.environ["CLUB360_BASE"]) if os.environ.get("CLUB360_BASE") \
    else Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WEB_DIR = Path(os.environ.get("CLUB360_WEB_DIR", "")) if os.environ.get("CLUB360_WEB_DIR") else BASE_DIR / "web"


def _load_bundle_env() -> None:
    """فایل .env ریشهٔ بسته را می‌خواند (CLUB360_*, SSO_*, CORS_*) — متغیر محیطی از فایل مهم‌تر است."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())
    except Exception:  # noqa: BLE001 — فایل مخدوش نباید اجرا را بشکند
        pass


def _resolve_port_host() -> tuple[int, str]:
    return int(os.environ.get("CLUB360_PORT", "8089")), os.environ.get("CLUB360_HOST", "0.0.0.0")


def _apply_portable_env() -> None:
    """env را قبل از هر import از app تنظیم می‌کند (engine در import ساخته می‌شود)."""
    _load_bundle_env()
    _port, _host = _resolve_port_host()
    DATA_DIR.mkdir(exist_ok=True)
    db_file = DATA_DIR / "club360.db"
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    os.environ.setdefault("ENVIRONMENT", "development")  # اجازهٔ seed نمونه‌های برچسب‌خورده
    os.environ.setdefault("REDIS_URL", "")  # inline runner — بدون Redis

    cors = os.environ.get("CLUB360_CORS", (
        f"http://localhost:{_port},http://127.0.0.1:{_port},"
        "http://188.212.96.235:8089,http://localhost:8089"
    ))
    os.environ.setdefault("CORS_ORIGINS", cors)

    # کلید امضا پایدار بین اجراها (refresh cookie معتبر می‌ماند)
    key_file = DATA_DIR / "secret_key.txt"
    if not key_file.exists():
        key_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    os.environ.setdefault("SECRET_KEY", key_file.read_text(encoding="utf-8").strip())


def _patch_sqlite_compat() -> None:
    """ledger_entries.seq: Identity در SQLite نادیده گرفته می‌شود → شمارندهٔ پردازش."""
    from sqlalchemy import ColumnDefault, text

    from . import models_registry  # noqa: F401 — ثبت همهٔ مدل‌ها
    from .core.db import TestingSession
    from .modules.points_ledger.models import LedgerEntry

    col = LedgerEntry.__table__.c.seq
    if col.identity is not None:
        col.identity = None
        counter = {"n": 0}

        def _next_seq() -> int:
            counter["n"] += 1
            return counter["n"]

        col.default = ColumnDefault(_next_seq)

        def _init_counter() -> None:
            try:
                s = TestingSession()
                try:
                    counter["n"] = int(s.execute(text("SELECT COALESCE(MAX(seq),0) FROM ledger_entries")).scalar() or 0)
                finally:
                    s.close()
            except Exception:  # noqa: BLE001 — جدول هنوز ساخته نشده
                counter["n"] = 0

        _init_counter()


def _prepare_db() -> None:
    """create_all + seed نمونهٔ برچسب‌خورده (SEED-01..12) — مقاوم به اجرای مجدد."""
    from . import models_registry  # noqa: F401
    from .core.db import Base, engine

    Base.metadata.create_all(engine)

    from .core.config import get_settings
    from .core.db import TestingSession

    s = TestingSession()
    try:
        from sqlalchemy import select

        from .modules.identity_access.models import User
        if s.execute(select(User).limit(1)).scalars().first() is None:
            s.rollback()
            from .seed import main as seed_main

            seed_main()
        else:
            s.rollback()
    finally:
        s.close()


def _mount_spa(app) -> None:
    """سرو کردن SPA ساخته‌شدهٔ Vite از web/ — پشت API (مسیرهای /api دست‌نخورده)."""
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    index = WEB_DIR / "index.html"
    if not index.exists():
        print(f"[portable] هشدار: {WEB_DIR} یافت نشد — UI سرو نمی‌شود (فقط API).")
        return

    # JSON معرفی در "/" (main.py) حذف می‌شود تا ریشه هم UI را بدهد؛ /api دست‌نخورده می‌ماند
    app.router.routes = [r for r in app.router.routes
                         if not (getattr(r, "path", None) == "/"
                                 and getattr(r, "methods", None) == {"GET"})]

    app.mount("/assets", StaticFiles(directory=str(WEB_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):  # noqa: ANN202
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path == "openapi.json":
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        f = (WEB_DIR / full_path).resolve()
        if f.is_file() and str(f).startswith(str(WEB_DIR)):
            return FileResponse(f)
        return FileResponse(index)  # client-side routing (/login, /rewards, …)


def main() -> None:
    print("=" * 62)
    print("  باشگاه دانشجو۳۶۰ — نسخهٔ قابل‌حمل (Portable)")
    print("=" * 62)
    _apply_portable_env()
    port, host = _resolve_port_host()

    import uvicorn

    from .core.db import engine  # noqa: E402 — env آماده است
    from .main import app  # noqa: E402

    _patch_sqlite_compat()
    _prepare_db()
    _mount_spa(app)

    print(f"  نشانی برنامه:  http://localhost:{port}   (روی {host} گوش داده می‌شود)")
    print(f"  نمونهٔ آماده:  st1@u1.demo / 12345678  (مدیر: mgr1@u1.demo)")
    print(f"  ریشهٔ بسته:    {BASE_DIR}")
    print(f"  پایگاه‌داده:   {os.environ['DATABASE_URL']}")
    print(f"  SSO:          ورود یکپارچه از سامانهٔ دانشجو۳۶۰ در صفحهٔ ورود")
    print("=" * 62)

    uvicorn.run(app, host=host, port=port, log_level="info", access_log=False)


if __name__ == "__main__":
    sys.exit(main())
