# ۱۱ — راهنمای عملیات، Backup/Restore و Runbook

## ۱. اجرا

### توسعهٔ محلی (بدون Docker — همان الگوی سندباکس)
```bash
cp .env.example .env   # مقادیر را تنظیم کنید
python scripts/reset_db.py --seed     # بازنشانی و دادهٔ نمونه (فقط dev)
bash scripts/dev.sh                   # migration + uvicorn + vite
# backend: http://127.0.0.1:8000  (OpenAPI: /api/docs)
# frontend: http://127.0.0.1:3000
```

### استقرار با Docker Compose
```bash
docker compose up --build       # db + redis + backend + worker + beat + frontend + nginx
docker compose exec backend python -m app.seed   # فقط غیر-Production!
```

### Production checklist (CFG-03)
- [ ] `COOKIE_SECURE=true`, `REQUIRE_MFA=true`, `REQUIRE_POLICY_SIGNOFF=true`, `ENABLE_SIMULATORS=false`
- [ ] Secrets از Vault/مدیر Secret — نه ریپو (SEC-01)
- [ ] TLS در Edge (Nginx/LB) + HSTS
- [ ] نسخهٔ سیاست‌های ضروری منتشر و تأیید دوم شده باشد (PNT)
- [ ] Backup روزانه + یک آزمون Restore مستند (SEC-14)

## ۲. Health / Readiness / Metrics
- `GET /api/v1/healthz` — liveness
- `GET /api/v1/readyz` — DB
- `GET /api/v1/metrics` — outbox/inbox/dead-letter/jobs depth (Prometheus متن)
- `GET /api/v1/system/info` — شفافیت حالت (simulator/inline/celery)

## ۳. سیاست Backup / Restore (SEC-14)

| داده | روش | بازه | نگهداری |
| --- | --- | --- | --- |
| PostgreSQL (دفترکل/حسابرسی) | `pg_dump --format=custom` + WAL archiving در Prod | روزانه + پیوسته | ۳۰ روز رمزی‌شده |
| فایل‌های خصوصی (MinIO/S3) | versioning + replication | پیوسته | ۹۰ روز |
| Redis | بدون نیاز (cache/صف) — بازیابی = بازپردازش Outbox/Inbox | — | — |

**Restore Runbook (خلاصه):**
1. سرور اپ را از گردش خارج کنید (maintenance page در Nginx).
2. `pg_restore -d club360_dev backup.dump` روی محیط موازی.
3. صحت‌سنجی: `SELECT Σdebit=Σcredit` روی ledger (اسکریپت apply/accont reconcile)، تست `/readyz`.
4. Redis پاک — صف‌ها از Outbox/Inbox بازپردازش می‌شوند (at-least-once).
5. سوئیچ ترافیک. گزارش رخداد و زمان RTO ثبت شود. (اجرای واقعی این Runbook در سندباکس: **اجرا نشده**)

## ۴. Runbook اختلال‌ها

| سناریو | تشخیص | اقدام |
| --- | --- | --- |
| قطع LMS | توقف رویدادها؛ `/admin/health` | هیچ اقدام penalize نکنید (TST-14)؛ پس از وصل، رویدادهای دیررس درون پنجرهٔ سیاست پردازش می‌شوند |
| قطع Redis | `/system/info` → inline؛ خطای worker | سامانه با InlineRunner ادامه می‌دهد؛ سلولی worker/beat را ری‌استارت کنید |
| توقف Worker | `bashgah_jobs_pending` بالا | `POST /api/v1/jobs` ران دستی؛ بررسی `background_jobs.last_error` |
| Dead-letter رویداد | `bashgah_inbox_quarantined` | `/admin/health` → بازپردازش پس از اصلاح منبع (EVT-08) |
| رزرو ناموفق ارائه‌دهنده | `reconciliation_cases` باز | تصمیم انسانی در `/admin/catalog` — استرداد خودکار ممنوع |
| مغایرت دفترکل | Job تطبیق + هشدار | `POST /jobs/replay` (حالت مجزا) → تفاوت را با سند جبرانی اصلاح کنید، هرگز دستی |
| خرابی DB | readyz fail | Runbook Restore بالا؛ RPO/RTO پس از تصویب و آزمون (PERF) |

## ۵. نگهداری دوره‌ای
- Job انقضا رزروها (TTL) — هر دقیقه در Prod (celery beat)
- SLA sweep پرونده‌ها — روزانه
- Retention: پاک‌سازی ناشناس‌سازی طبق `retention_policies` (DM-05)
- چرخش Secrets و کلید HMAC منابع
