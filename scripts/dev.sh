#!/usr/bin/env bash
# توسعهٔ محلی بدون Docker (همان الگوی اجراشده در سندباکس)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "۱) PostgreSQL و Redis باید در دسترس باشند (یا در سندباکس: pgserver محلی)"
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:@/club360_dev?host=$HOME/.pgdata}"

echo "۲) Migration"
(cd backend && alembic upgrade head)

echo "۳) Seed (اختیاری، فقط توسعه) — python -m app.seed"
echo "۴) اجرای سرورها:"
(cd backend && nohup python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/uvicorn.log 2>&1 &)
(cd frontend && npm run dev)
