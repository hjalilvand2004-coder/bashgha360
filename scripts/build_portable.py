#!/usr/bin/env python3
"""Build Club360 portable bundles (Windows + Linux) — fully self-contained.

Windows: python.org embeddable runtime + wheels (win_amd64/cp312) + app/ + web/
Linux:   python-build-standalone runtime + wheels + app/ + web/

Root-cause fix for «ModuleNotFoundError: No module named 'app'»:
  the bundle keeps app/ at the SAME root as runtime/ and start.bat sets
  `cd /d "%~dp0"` + CLUB360_BASE; python312._pth gets ..\.. and app/ is also copied into site-packages (embedded-python isolated mode ignores PYTHONPATH).

Usage:  python3 scripts/build_portable.py [--platform win|linux|both] [--out DIR]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"
BUILD = REPO / "build" / "portable"
TOOLS = REPO / "build" / "tools"

PY_VERSION = "3.12.8"
PBS_RELEASE = "20250115"  # python-build-standalone release tag
PBS_ASSET = f"cpython-{PY_VERSION}+{PBS_RELEASE}-x86_64-unknown-linux-gnu-install_only.tar.gz"

WIN_NAME = "club360-portable-windows-x64"
LINUX_NAME = "club360-portable-linux-x64"


def bundle_version() -> str:
    """نسخهٔ بسته — از env یا تگ گیت؛ نهایی: مقدار پیش‌فرض فعلی."""
    import os
    env = os.environ.get("CLUB360_VERSION") or os.environ.get("GITHUB_REF_NAME")
    if env and env.startswith("v"):
        return env
    try:
        t = subprocess.run(["git", "describe", "--tags", "--abbrev=0"],
                           capture_output=True, text=True, cwd=REPO)
        if t.returncode == 0 and t.stdout.strip().startswith("v"):
            return t.stdout.strip()
    except Exception:
        pass
    return "v1.3.0"

ENV_FILE = """\
# ============================================================
#  باشگاه دانشجو۳۶۰ — پیکربندی نسخهٔ قابل‌حمل
#  این فایل کنار start.bat است؛ تغییر دهید و دوباره اجرا کنید.
# ============================================================

# ---- Web ----
CLUB360_PORT=8089
CLUB360_HOST=0.0.0.0
ENVIRONMENT=development

# ---- SSO (ورود یکپارچه با سامانهٔ مرکزی دانشجو۳۶۰) ----
SSO_ISSUER=http://188.212.96.235:8086
SSO_CLIENT_ID=club360
SSO_CLIENT_SECRET=
SSO_SCOPES=openid profile email
SSO_REDIRECT_URI=
SSO_DEFAULT_ROLE=student
SSO_DEFAULT_UNIVERSITY_CODE=UNI-A

# ---- CORS (اگر UI از دامنهٔ دیگری سرو شود) ----
CORS_ORIGINS=http://localhost:8089,http://127.0.0.1:8089,http://188.212.96.235:8089
"""

START_BAT = r"""@echo off
setlocal
title Bashgah 360 Student Club (portable)

rem ---- ALWAYS work from the bundle root ----
cd /d "%~dp0"

rem Embedded python uses python312._pth (isolated mode): PYTHONPATH is IGNORED
rem and "." in _pth means the python.exe folder - NOT this bundle root. The app
rem package is therefore also placed inside Lib\site-packages, and the bundle
rem root is passed explicitly so data/web/.env resolve correctly.
set "CLUB360_BASE=%~dp0"

if not exist "runtime\python\python.exe" (
    echo [ERROR] runtime\python\python.exe not found - bundle is incomplete.
    pause
    exit /b 1
)
if not exist "runtime\python\Lib\site-packages\app\portable.py" (
    echo [ERROR] runtime\python\Lib\site-packages\app\portable.py not found - bundle is incomplete.
    pause
    exit /b 1
)

set "CLUB360_PORT=8089"
runtime\python\python.exe -m app.portable

echo.
echo Server stopped.
pause
"""

STOP_BAT = r"""@echo off
rem Stop the Bashgah360 server listening on port 8089
set PORT=8089
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    echo Stopping PID %%a ...
    taskkill /PID %%a /F >nul 2>&1
)
echo Done.
pause
"""

START_SH = r"""#!/usr/bin/env bash
# باشگاه دانشجو۳۶۰ — اجرای نسخهٔ قابل‌حمل (پورت ۸۰۸۹)
cd "$(dirname "$0")" || exit 1
export PYTHONPATH="$(pwd)"
export CLUB360_PORT="${CLUB360_PORT:-8089}"
exec runtime/python/bin/python3 -m app.portable
"""

README_FA = """\
باشگاه دانشجو۳۶۰ — نسخهٔ قابل‌حمل (Portable)  نسخهٔ ۱٫۱٫۱
============================================================

۱) اجرا:
   - ویندوز: روی start.bat دوبار کلیک کنید. پنجرهٔ سیاه (سرور) باز می‌ماند.
   - لینوکس:  chmod +x start.sh && ./start.sh
   سپس در مرورگر:  http://localhost:8089

۲) دسترسی از شبکه (مثلاً  http://188.212.96.235:8089):
   - پورت ۸۰۸۹ در فایروال ویندوز باز باشد (Inbound Rule → TCP 8089).
   - نشانی در فایل .env: CLUB360_PORT=8089

۳) ورود یکپارچه (SSO):
   - در صفحهٔ ورود، دکمهٔ «ورود یکپارچه با سامانهٔ دانشجو۳۶۰ (SSO)» را بزنید.
   - آدرس سامانه در .env: SSO_ISSUER=http://188.212.96.235:8086
   - SSO_CLIENT_ID / SSO_CLIENT_SECRET را مطابق Client ثبت‌شده در سامانهٔ
     مرکزی تنظیم کنید (اگر لازم شد؛ الان discovery خودکار انجام می‌شود).
   - Redirect URI ثبت‌شده در سامانهٔ مرکزی باید این باشد:
       http://188.212.96.235:8089/api/v1/auth/sso/callback
     (برای دسترسی از localhost هم به‌صورت خودکار همان نشانی درخواست‌کننده
     استفاده می‌شود.)

۴) ورود محلی (حساب‌های نمونه):
   دانشجو:  st1@u1.demo / 12345678
   مدیر باشگاه:  mgr1@u1.demo · حسابرس: aud1@u1.demo

۵) داده‌ها:
   - پایگاه‌دادهٔ سبک SQLite در مسیر data/club360.db (نسخهٔ پشتیبان بگیرید).
   - در استقرار عملیاتی، PostgreSQL مرجع رسمی است (docker-compose در مخزن).

۶) توقف سرور: stop.bat (ویندوز) یا Ctrl+C در پنجرهٔ سرور.

مشکلات رایج:
   - «Port already in use»: stop.bat را اجرا کنید یا CLUB360_PORT را تغییر دهید.
   - «No module named 'app'»: بسته کامل استخراج نشده — پوشهٔ استخراج‌شده را
     با start.bat داخل همان پوشه اجرا کنید.
"""


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def run(cmd: list[str], **kw) -> None:
    subprocess.run(cmd, check=True, **kw)


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log(f"cached: {dest.name}")
        return dest
    log(f"downloading {url}")
    urllib.request.urlretrieve(url, dest)
    return dest


def clean_copy(src: Path, dst: Path, skip_pyc: bool = True) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc") if skip_pyc else None)


def portable_requirements() -> Path:
    """Deps for portable bundles — celery/redis/psycopg2 NOT needed (inline runner + SQLite)."""
    f = TOOLS / "requirements-portable.txt"
    f.write_text(
        "fastapi==0.115.6\n"
        "uvicorn==0.34.0\n"
        "sqlalchemy==2.0.36\n"
        "pydantic==2.10.4\n"
        "pydantic-settings==2.7.0\n"
        "python-jose[cryptography]==3.3.0\n"
        "bcrypt==4.2.1\n"
        "httpx==0.28.1\n"
        "python-multipart==0.0.20\n"
        "email-validator==2.2.0\n",
        encoding="utf-8",
    )
    return f


# ----------------------------------------------------------------- win ----
def build_win(out: Path) -> Path:
    name = WIN_NAME
    root = out / name
    if root.exists():
        shutil.rmtree(root)
    (root / "data").mkdir(parents=True)

    log("WIN: runtime python (embeddable) …")
    emb = download(f"https://www.python.org/ftp/python/{PY_VERSION}/python-{PY_VERSION}-embed-amd64.zip",
                   TOOLS / f"python-{PY_VERSION}-embed-amd64.zip")
    runtime = root / "runtime" / "python"
    runtime.mkdir(parents=True)
    with zipfile.ZipFile(emb) as z:
        z.extractall(runtime)
    # ._pth semantics (isolated mode): PYTHONPATH ignored; "." = this python dir.
    # `..\..` puts the BUNDLE ROOT on sys.path so `app/` beside start.bat imports;
    # site-packages is enabled for the wheels.
    pth = runtime / "python312._pth"
    pth.write_text("python312.zip\n.\nLib\\site-packages\n..\\..\nimport site\n", encoding="ascii")
    # binaries kept next to python.exe so DLLs resolve
    site = runtime / "Lib" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)

    log("WIN: wheels (win_amd64 / cp312) …")
    wheelhouse = download_wheels("win_amd64", "3.12")
    for whl in sorted(wheelhouse.glob("*.whl")):
        with zipfile.ZipFile(whl) as z:
            z.extractall(site)
    log(f"WIN: {len(list(wheelhouse.glob('*.whl')))} wheels extracted")

    stage_common(root)
    # belt & braces: a second copy of app/ INSIDE site-packages — guaranteed
    # importable regardless of any ._pth relative-path behaviour on Windows.
    clean_copy(BACKEND / "app", site / "app")
    write_launchers(root)

    log("WIN: zipping …")
    zip_path = out / f"{name}-{bundle_version()}.zip"
    if zip_path.exists():
        zip_path.unlink()
    run(["zip", "-r", "-X", "-q", str(zip_path), name], cwd=out)
    log(f"WIN: {zip_path} ({zip_path.stat().st_size/1_000_000:.1f} MB)")
    return zip_path


def download_wheels(platform: str, pyver: str) -> Path:
    wh = TOOLS / f"wheelhouse-{platform}"
    wh.mkdir(parents=True, exist_ok=True)
    run([sys.executable, "-m", "pip", "download", "-q", "-r", str(portable_requirements()),
         "--platform", platform, "--python-version", pyver, "--implementation", "cp",
         "--only-binary=:all:", "-d", str(wh)])
    return wh


# --------------------------------------------------------------- linux ----
def build_linux(out: Path) -> Path:
    name = LINUX_NAME
    root = out / name
    if root.exists():
        shutil.rmtree(root)
    (root / "data").mkdir(parents=True)

    log("LINUX: runtime python (python-build-standalone) …")
    pbs = download(f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_RELEASE}/{PBS_ASSET}",
                   TOOLS / PBS_ASSET)
    runtime = root / "runtime" / "python"
    runtime.mkdir(parents=True)
    run(["tar", "-xzf", str(pbs), "-C", str(runtime), "--strip-components=1"])

    log("LINUX: pip install into runtime …")
    run([str(runtime / "bin" / "python3"), "-m", "pip", "install", "-q", "--no-compile",
         "-r", str(portable_requirements())])
    # trim caches
    for pyc in runtime.rglob("__pycache__"):
        shutil.rmtree(pyc, ignore_errors=True)

    stage_common(root)
    write_launchers(root)

    log("LINUX: tar.gz …")
    tgz = out / f"{name}-{bundle_version()}.tar.gz"
    if tgz.exists():
        tgz.unlink()
    run(["tar", "-czf", str(tgz), name], cwd=out)
    log(f"LINUX: {tgz} ({tgz.stat().st_size/1_000_000:.1f} MB)")
    return tgz


# --------------------------------------------------------------- common ----
def stage_common(root: Path) -> None:
    log("staging app/ (backend source)")
    clean_copy(BACKEND / "app", root / "app")
    log("staging web/ (built SPA)")
    dist = FRONTEND / "dist"
    assert (dist / "index.html").exists(), "frontend/dist missing — run `npm run build` first"
    _assets = dist / "assets"
    assert _assets.is_dir() and any(_assets.glob("*.js")), \
        "frontend/dist/assets empty/incomplete — stale dist; run `npm run build` first"
    web = root / "web"
    if web.exists():
        shutil.rmtree(web)
    shutil.copytree(dist, web)
    env = root / ".env"
    env.write_text(ENV_FILE, encoding="utf-8")


def write_launchers(root: Path) -> None:
    (root / "start.bat").write_bytes(START_BAT.replace("\n", "\r\n").encode("ascii"))
    (root / "stop.bat").write_bytes(STOP_BAT.replace("\n", "\r\n").encode("ascii"))
    sh = root / "start.sh"
    sh.write_text(START_SH, encoding="utf-8")
    sh.chmod(0o755)
    (root / "README-FA.txt").write_text(README_FA, encoding="utf-8")


# ------------------------------------------------------------ verify ----
def verify_win_structure(zip_path: Path) -> None:
    log("VERIFY: windows bundle structure")
    import posixpath

    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        must = [f"{WIN_NAME}/start.bat", f"{WIN_NAME}/app/portable.py", f"{WIN_NAME}/app/__init__.py",
                f"{WIN_NAME}/web/index.html", f"{WIN_NAME}/runtime/python/python.exe",
                f"{WIN_NAME}/runtime/python/python312._pth", f"{WIN_NAME}/README-FA.txt",
                f"{WIN_NAME}/.env"]
        for m in must:
            assert m in names, f"MISSING in zip: {m}"
        start_bat = z.read(f"{WIN_NAME}/start.bat").decode("ascii")
        assert 'cd /d "%~dp0"' in start_bat and 'set "CLUB360_BASE=%~dp0"' in start_bat
        assert "app.portable" in start_bat
        pth = z.read(f"{WIN_NAME}/runtime/python/python312._pth").decode()
        assert "Lib\\site-packages" in pth and "import site" in pth
        assert "..\\.." in pth, "bundle root missing from python312._pth"
        assert f"{WIN_NAME}/runtime/python/Lib/site-packages/app/portable.py" in names, \
            "app package missing inside site-packages"
        site_top = set()
        for n in names:
            parts = n.split("/")
            if len(parts) > 5 and parts[1] == "runtime" and parts[2] == "python" \
                    and parts[3] == "Lib" and parts[4] == "site-packages":
                entry = parts[5].lower()
                site_top.add(entry)
                if entry.endswith(".py"):
                    site_top.add(entry[:-3])  # single-module dists (typing_extensions.py, …)
        for di in [x for x in site_top if x.endswith(".dist-info")]:
            site_top.discard(di)
        log(f"  site-packages top-level entries: {len(site_top)}")
        for pkg in ("fastapi", "uvicorn", "sqlalchemy", "pydantic", "jose", "bcrypt",
                    "httpx", "multipart", "python_multipart", "email_validator", "starlette",
                    "anyio", "pydantic_core", "cryptography", "cffi", "dns", "greenlet",
                    "dotenv", "certifi", "httpcore", "h11", "click", "idna",
                    "typing_extensions", "annotated_types", "ecdsa", "pyasn1"):
            assert pkg in site_top, f"MISSING package in runtime: {pkg}"
        # no stale launcher mistake: app must be at bundle root, not elsewhere
        assert f"{WIN_NAME}/app/modules/identity_access/router.py" in names
    log("  windows structure OK")


def verify_import_closure() -> None:
    """Every top-level import of app/** must exist in the bundled runtime or stdlib."""
    import ast

    app_dir = BUILD / WIN_NAME / "app"
    site_dir = BUILD / WIN_NAME / "runtime" / "python" / "Lib" / "site-packages"
    stdlib = set(sys.stdlib_module_names)
    site_top = {p.name.lower() for p in site_dir.iterdir()}
    site_top |= {p.stem.lower().split("-")[0] for p in site_dir.glob("*.dist-info")}
    local = {"app"}
    # گاردشده‌ها: importهای اختیاری داخل try/except — نبودشان مانع اجرا نیست
    guarded_optional = {"pgserver", "celery"}  # config.py try/except · main.py try/except ImportError
    missing = set()
    for py in app_dir.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError as e:
            missing.add(f"SYNTAX ERROR {py.relative_to(app_dir)}: {e}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    top = a.name.split(".")[0]
                    if top.lower() in guarded_optional:
                        continue
                    if top.lower() not in stdlib and top.lower() not in site_top and top not in local:
                        missing.add(f"{py.relative_to(app_dir)} -> import {a.name}")
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                top = node.module.split(".")[0]
                if top.lower() in guarded_optional:
                    continue
                if top.lower() not in stdlib and top.lower() not in site_top and top not in local:
                    missing.add(f"{py.relative_to(app_dir)} -> from {node.module}")
    if missing:
        for m in sorted(missing):
            print("  MISSING:", m)
        raise SystemExit("import closure FAILED")
    log("VERIFY: import closure OK (all app imports resolve in bundled runtime)")


def verify_linux_boot(tgz: Path, port: int = 8090) -> None:
    import json
    import time as _t
    import urllib.error
    import urllib.request

    log(f"VERIFY: linux bundle boot on :{port}")
    ex = BUILD / "verify-linux"
    if ex.exists():
        shutil.rmtree(ex)
    ex.mkdir(parents=True)
    run(["tar", "-xzf", str(tgz), "-C", str(ex)])
    bundle = ex / LINUX_NAME
    run(["chmod", "+x", str(bundle / "start.sh")])
    env_cmd = [str(bundle / "start.sh")]
    import os

    proc = subprocess.Popen(env_cmd, env={**os.environ, "CLUB360_PORT": str(port)},
                            stdout=open(BUILD / "verify-linux.log", "w"), stderr=subprocess.STDOUT)
    ok = False
    try:
        for _ in range(60):
            _t.sleep(1)
            try:
                with urllib.request.urlopen(f"http://localhost:{port}/api/v1/healthz", timeout=2) as r:
                    if r.status == 200:
                        ok = True
                        break
            except (urllib.error.URLError, OSError):
                continue
        assert ok, "bundle did not become healthy"
        with urllib.request.urlopen(f"http://localhost:{port}/") as r:
            body = r.read().decode()
            assert "<title>" in body and "دانشجو" in body, "SPA not served at /"
        with urllib.request.urlopen(f"http://localhost:{port}/api/v1/auth/sso/status") as r:
            st = json.loads(r.read())
            assert st["enabled"] is True and "188.212.96.235:8086" in st["issuer"]
        req = urllib.request.Request(f"http://localhost:{port}/api/v1/auth/login", method="POST",
                                     data=json.dumps({"username": "st1@u1.demo", "password": "12345678"}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            assert r.status == 200 and "access_token" in json.loads(r.read())
        log("  linux boot OK (healthz, SPA, SSO status, local login)")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="both", choices=["win", "linux", "both"])
    ap.add_argument("--out", default=str(BUILD))
    ap.add_argument("--skip-boot-test", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    assert (FRONTEND / "dist" / "index.html").exists(), "build the SPA first (npm run build)"

    if args.platform in ("win", "both"):
        verify_win_structure(build_win(out))
        verify_import_closure()
    if args.platform in ("linux", "both"):
        tgz = build_linux(out)
        if not args.skip_boot_test:
            verify_linux_boot(tgz)
    log("ALL DONE")


if __name__ == "__main__":
    main()
