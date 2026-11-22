# ۰۳ — معماری سامانهٔ باشگاه۳۶۰

نسخهٔ 1.0 — Modular Monolith با مرزهای روشن

## ۱. نمای کلی

```
┌────────────────────────────────────────────────────────────────────┐
│  React 18 + Vite + TS + Tailwind + Radix (RTL) — پورت 5173/3000     │
│  TanStack Query · RHF+Zod · Recharts · Motion(reduced-motion)       │
└───────────────▲────────────────────────────────────────────────────┘
                │ HTTPS (JSON, /api/v1)  — Nginx Reverse Proxy در Prod
┌───────────────┴────────────────────────────────────────────────────┐
│                      FastAPI (Modular Monolith)                     │
│  ┌─ Middleware: CorrelationID · StructuredLog · RateLimit · CSRF    │
│  │                                                                  │
│  │   ┌──────────────── ۱۷ ماژول دامنه (مرزبندی روشن) ─────────────┐  │
│  │   │ identity_access    memberships_consents   student_goals    │  │
│  │   │ event_ingestion    policy_engine           points_ledger   │  │
│  │   │ achievements_tiers missions_groups         rewards_fulfill.│  │
│  │   │ recommendations    integrity_reviews       appeals         │  │
│  │   │ notifications      analytics               audit           │  │
│  │   │ integrations (Adapterهای دانشجو۳۶۰ + LMS)                  │  │
│  │   └────────────────────────────────────────────────────────────┘  │
│  │   Shared Kernel: UoW · Outbox/Inbox · Idempotency · Errors        │
│  │   Service/Domain Layer: منطق کسب‌وکار (Endpoint فقط انتقال)        │
│  └──────────────────────────────────────────────────────────────────┘
        │ SQLAlchemy 2.0 (sync)          │ Celery (Prod) / InlineRunner (Dev)
        ▼                                ▼
┌────────────────────┐        ┌──────────────────────┐
│ PostgreSQL 16      │        │ Redis 7 (cache/broker)│  ◄─ مرجع صحت فقط PG
│ append-only Ledger │        │ «نباید مرجع مانده باشد»│
│ Triggers بی‌ردپا    │        └──────────────────────┘
│ pgvector: فقط در صورت نیاز توصیه‌گر معنایی (فعلاً نصب نیست)          │
└────────────────────┘
```

## ۲. تصمیم‌های کلیدی و دلیل (ADR خلاصه)

| # | تصمیم | دلیل |
| --- | --- | --- |
| ADR-1 | Modular Monolith (نه میکروسرویس) | الزام صریح سند؛ مرزها با پکیج‌های مستقل + قانون import (ماژول‌ها فقط از `shared` و API سطح بالای همدیگر استفاده می‌کنند) |
| ADR-2 | SQLAlchemy 2.0 **sync** + psycopg2 | کنترل هم‌زمانی صریح (`SELECT … FOR UPDATE`)، سادگی استدلال دربارهٔ تراکنش مالی، پایداری؛ FastAPI endpointها را با threadpool اجرا می‌کند |
| ADR-3 | UUID PK + `university_id` روی تمام جداول دامنه | جداسازی بین دانشگاه‌ها سمت سرور (بخش ۵) |
| ADR-4 | امتیاز `Numeric(14,2)` + Decimal | ممنوعیت floating-point؛ گرد کردن متمرکز |
| ADR-5 | Triggers بی‌ردپا در DB برای `ledger_entries`, `audit_log`, `educational_events` | حذف/ویرایش بی‌ردپا حتی با دسترسی مستقیم DB ممکن نیست |
| ADR-6 | Transactional Outbox + Inbox با کلید یکتا | انتشار اتکاپذیر رویداد داخلی؛ at-least-once تحویل، اثر امتیازی exactly-once با Idempotency و قید یکتا — ادعای exactly-once شبکه‌ای نمی‌کنیم |
| ADR-7 | Celery در Prod، InlineRunner در Dev/Test | سندباکس بدون Redis هم «قابل اجرا و آزمون» است؛ کد Task یکسان است، فقط Runner عوض می‌شود؛ وضعیت در `/system/info` شفاف |
| ADR-8 | pgvector نصب نمی‌شود | تا نیاز واقعی به توصیه‌گر معنایی (مرحلهٔ دوم/سوم) اضافه نمی‌شود |
| ADR-9 | OpenAPI مرجع قرارداد؛ Client فرانت دست‌نویس typed با قرارداد مشترک | تولید خودکار Client در CI جای توسعه دارد (ثبت در Backlog) |

## ۳. جریان مرجع: «رویداد → امتیاز»

1. LMS/Adapter → `POST /api/v1/events/ingest` (احراز سرویس + امضای HMAC + Rate limit).
2. `event_ingestion`: اعتبارسنجی Schema → کلید یکتای مرکب `(university_id, source_id, event_id)` → تکراری: پاسخ idempotent بدون اثر دوم. نامعتبر: Quarantine/Dead-letter با دلیل. رویداد خام حداقلی **غیرقابل تغییر** ذخیره می‌شود.
3. Outbox پیام `EducationalEventReceived` در همان تراکنش نوشته می‌شود.
4. Dispatcher/Worker پیام را برمی‌دارد → `policy_engine`: انتخاب PolicyVersion **منتشرشدهٔ** معتبر براساس `occurred_at` (نه زمان پردازش) → ارزیابی DSL با Trace کامل → `RuleEvaluation`.
5. `points_ledger`: در یک Unit of Work با `Idempotency-Key = inbox_message_id`: تراکنش award + LedgerEntryها + به‌روزرسانی حساب (با Row Lock) + BalanceProjection + استفادهٔ سقف (`policy_cap_usage` با قفل ردیف) + ثبت Trace + انقضا/بازده کاهشی طبق نسخهٔ سیاست.
6. رویدادهای داخلی سطح/نشان (`TierCheckRequested`, `BadgeCriteriaMet`) از Outbox → `achievements_tiers`.
7. اگر Worker یک پیام را دوباره پردازش کند، Inbox + قید یکتا اثر مضاعف نمی‌سازد (آزمون سناریو ۵).
8. قطع LMS هیچ کاهش امتیازی و هیچ پرچم تقلبی ایجاد نمی‌کند (آزمون سناریو ۱۴)؛ نبود داده = نبود رویداد.

## ۴. مرز تراکنش و Unit of Work

- هر فرمان حساس در یک تراکنش DB: (رزرو ظرفیت + رزرو امتیاز)، (award + cap + trace + projection)، (تصمیم پرونده + اصلاح دفترکل).
- قفل‌ها: `SELECT … FOR UPDATE` روی `point_accounts` و `reward_capacities` و `policy_cap_usage`.
- Deadlock/Serialization Failure: retry محدود (۳ بار، backoff تصادفی) در `shared/uow.py`.
- تحویل خارجی هرگز داخل تراکنش طولانی DB انجام نمی‌شود؛ با Outbox + شناسهٔ پایدار + Callback + Reconciliation.

## ۵. اتصال به دانشجو۳۶۰ (Adapterها)

مالکیت: باشگاه هویت، گراف مهارت یا سنجش یادگیری **نیست**. دادهٔ محلی فقط Snapshot حداقلی با `source`, `snapshot_at` است.

| Adapter | قرارداد | وضعیت |
| --- | --- | --- |
| هویت و رویداد یکپارچه (۱) | `IdentityAdapter`: verify_token, get_student_reference | Simulator فعال + OIDC Config آماده (`mode=simulator`) |
| وضعیت آموزشی/اهداف مجاز (۲و۱۳) | `AcademicStatusAdapter`: snapshot وضعیت + اهداف مجاز | Simulator |
| یادگیری/ارزیابی/پیشرفت معتبر (۳) | `LearningAdapter`: رویدادهای verified | Simulator = منبع رویداد آزمایشی |
| تقویم و قواعد برای دستیار (۴) | `ClubCalendarAdapter` (export) | پیاده‌سازی خواندنی از PolicyVersionهای published |
| مهارت و شکاف (۵و۱۳) | `SkillAdapter` | Simulator (Snapshot حداقلی) |
| ظرفیت/سیاست/گزارش تجمیعی (۸) | `CapacityReportAdapter` | داخلی |
| توصیهٔ حمایتی مجاز (۱۴) | `SupportAdviceAdapter` | فقط توصیه؛ بدون مدل ترک‌تحصیل |
| سیگنال/ارجاع رسمی (۱۵) | `ReferralAdapter` (خروج) | فقط ارجاع رسمی، نه رأی |
| فرصت پروژه/کارآموزی (۱۶) | `OpportunityAdapter` | فهرست فرصت تأییدشده؛ تضمین پذیرش نیست |

حالت اتصال (واقعی/آزمایشی) در تنظیمات و گزارش `/api/v1/system/info` صریح است. Adapter آزمایشی از Production جدا است (`ENABLE_SIMULATORS=false` آن‌ها را از مسیر Runtime حذف می‌کند).

## ۶. استقرار

- Dev: `docker compose up` (db+redis+backend+worker+beat+frontend) — و حالت «بدون Redis» برای سندباکس.
- Prod: Nginx (TLS) → backend uvicorn (چند replica) → PG (primary + backup) + Redis؛ MinIO سازگار S3 برای فایل خصوصی با لینک کوتاه‌عمر.
- Health: `/healthz` (liveness) و `/readyz` (db+migrations+queue)؛ اهداف p95 فقط پس از آزمون بار قابل اعلام است (بخش ۱۹ سند کارفرما) و تا آن زمان در TEST_RESULTS «اجرا نشده» ثبت می‌شود.

## ۷. قواعد مرزبندی کد

1. Router فقط: auth, parse, authorize, صدا زدن Service, پاسخ DTO — بدون منطق کسب‌وکار.
2. Service/Domain: تمام قواعد، تراکنش، رویداد؛ تست‌پذیر بدون HTTP.
3. ماژول‌ها از جدول‌های یکدیگر مستقیم query نمی‌کنند؛ از سرویس/ریپازیتوری ماژول مقصد یا رویداد Outbox استفاده می‌کنند.
4. هر موجودیت دامنه `university_id` دارد مگر جداول مرجع سراسری (TierDefinition template و …).
5. هیچ ماژولی `eval/exec/__import__` استفاده نمی‌کند (CI grep).
