# مستند فنی باشگاه دانشجو۳۶۰

**زیرسیستم ۱۷ اکوسیستم دانشجو۳۶۰ — «باشگاه هوشمند پیشرفت، مشارکت و تجربهٔ دانشجو»** · مخاطب: معمار، توسعه‌دهنده و مدیر فنی · مبنا: کد واقعی ریپو `club360` (backend FastAPI، frontend React+Vite+TS، PostgreSQL، Redis/Celery)، اسناد شماره‌دار `docs/01..15` و نتایج اجرای واقعی آزمون‌ها در `backend/TEST_RESULTS.md`.

## خلاصهٔ اجرایی

باشگاه دانشجو۳۶۰ یک Modular Monolith مبتنی بر FastAPI است که سه خدمت اصلی «امتیاز/سطح/نشان/پاداش»، «پیشنهاد شخصی‌سازی‌شده» و «نظارت اخلاقی و کشف سوءاستفاده» را روی یک دفترکل امتیازی متوازن و بی‌ردپا ارائه می‌کند. هستهٔ مالی سامانه (`points_ledger`) با PostgreSQL 16 به‌عنوان مرجع صحت، triggerهای append-only، قید توازن هر تراکنش در لحظهٔ COMMIT، کلید یکتای مرکب رویداد، و جفت Inbox/Outbox اثر امتیازی exactly-once را تضمین می‌کند؛ موتور سیاست (`policy_engine`) نسخه‌های DSL امضاشدهٔ JSON را بدون `eval` ارزیابی و Trace کامل محاسبه ذخیره می‌کند. دسترسی‌ها با RBAC داخلی (۱۰ نقش + Principal سرویس) و ورود یکپارچهٔ OIDC با سامانهٔ مرکزی مدیریت می‌شود. frontend یک SPA فارسی RTL با React+Vite+TypeScript و فونت محلی Vazirmatn است. کل سامانه در docker-compose (پورت ۸۰۸۹) و در بستهٔ قابل‌حمل ویندوز/لینوکس اجرا می‌شود؛ **۴۸/۴۸ آزمون backend روی PostgreSQL 16.2 واقعی پاس شده** و ادعاهای اجرانشده (E2E مرورگر، Load test، Backup واقعی، Celery روی Redis واقعی) صریحاً جدا شده‌اند. نسخهٔ فعلی کد v1.3.1 (بک‌اند) با ارتقای گرافیکی v1.4 در frontend است.

## فصل ۱ — مقدمه، اهداف و دامنهٔ سامانه

باشگاه دانشجو۳۶۰ زیرسیستم شمارهٔ ۱۷ از اکوسیستم «دانشجو۳۶۰» است؛ سامانه‌ای داوطلبانه که فعالیت‌های تأییدشدهٔ آموزشی و مشارکتی دانشجو را به امتیاز، سطح، نشان و پاداشِ شفاف و قابل‌ردیابی تبدیل می‌کند. اصل بنیادین طراحی — مستند در `docs/01-requirements-interpretation.md` و رعایت‌شده در کل کد — آن است که باشگاه «هیچ‌وقت نمرهٔ آموزشی نیست»: عضویت داوطلبانه است، امتیاز هیچ اثری بر پروندهٔ تحصیلی ندارد، رقابت فرساینده و رتبه‌بندی عمومی وجود ندارد، و خروج از باشگاه خدمات پایهٔ اکوسیستم را محدود نمی‌کند.

دامنهٔ سامانه سه خدمت اصلی است که وضعیت آن‌ها در README و `TEST_RESULTS.md` صریح شده است: (۱) موتور امتیاز، سطح، نشان و پاداش با دفترکل متوازن — در وضعیت «MVP عملیاتی»؛ (۲) پیشنهاد شخصی‌سازی‌شدهٔ قاعده‌محور با دلیل محاسبه‌شده و حالت عمومی بدون رضایت — عملیاتی، با توصیه‌گر داده‌محور (ML) به مرحلهٔ ۲ موکول است؛ (۳) نظارت اخلاقی و کشف سوءاستفاده با کنترل‌های قطعی و الگوهای ریسک که فقط پرونده می‌سازند و هرگز حکم خودکار نمی‌دهند — کشف پیشرفته به مرحلهٔ ۳ موکول است.

آنچه صریحاً خارج از دامنه است: مالکیت هویت و گراف مهارت دانشجو (متعلق به زیرسیستم‌های ۱ و ۵ اکوسیستم)، سنجش یادگیری و اتصال واقعی LMS (Adapter آماده است اما در حالت `simulator` کار می‌کند)، و مدل‌های پیش‌بینی ترک‌تحصیل. اتصال به سایر زیرسیستم‌ها فقط از طریق Adapterهای قراردادی در ماژول `integrations` و Snapshot حداقلی با `source` و `snapshot_at` انجام می‌شود.

مخاطب این سند معمار و توسعه‌دهنده است؛ بنابراین هر ادعا به مسیر کد یا سند ارجاع دارد. سلسله‌مراتب مستندات: `docs/02-requirements-matrix.md` ماتریس ردیابی کامل الزامات (شناسه‌هایی مانند PNT، LED، EVT، RWD، REC، INT، ACC، CLUB، SEC، UX)، `docs/03..06` معماری/داده/ماشین‌حالت/قرارداد، `docs/07..09` سیستم طراحی، تهدید و آزمون، و `docs/10..15` نقشهٔ راه، Runbook، مدل AI، امنیت/دسترس‌پذیری و آمادگی پایلوت. صداقت تحویل در دو سطح اعمال شده: «تولید شده» از «اجرا و آزموده‌شده» جدا است، و نتایج عددی واقعی فقط در `backend/TEST_RESULTS.md` (آخرین اجرا ۲۰۲۶-۱۱-۲۲: ۴۸/۴۸ پاس روی PostgreSQL 16.2 واقعی، بدون SQLite) ثبت می‌شود. نسخه‌های تحویل از v1.1 (SSO و بستهٔ قابل‌حمل) تا v1.3.1 (تجربهٔ باشگاه و هات‌فیکس) منتشر شده و ارتقای گرافیکی v1.4 در کد frontend موجود است؛ جزئیات در فصل ۸ و ۱۲ آمده است.

## فصل ۲ — معماری کلی

معماری سامانه «مونولیت ماژولار» است (ADR-1 در `docs/03`): یک فرایند FastAPI با مرزهای ماژولی روشن، نه میکروسرویس. دلیل انتخاب، الزام صریح سند کارفرما و سادگی استدلال دربارهٔ تراکنش مالی است؛ مرز ماژول‌ها با قانون import حفظ می‌شود: ماژول‌ها فقط از `shared` و سرویس/API سطح بالای یکدیگر استفاده می‌کنند و مستقیماً جدول‌های ماژول مقصد را query نمی‌کنند (`docs/03`، بخش ۷). هر ماژول الگوی یکسانی دارد: `models.py` (SQLAlchemy)، `service.py` (تمام منطق کسب‌وکار و تراکنش) و `router.py` (فقط auth، parse، authorize و پاسخ DTO — بدون منطق).

```
React 18 + Vite + TS + Tailwind RTL (SPA)  —  پورت dev 3000
            │  HTTPS/JSON  /api/v1  (Nginx Reverse Proxy در استقرار، پورت 8089)
FastAPI (modular monolith, uvicorn:8000)
  Middleware: CorrelationID · StructuredLog · RateLimit · CSRF-origin
  Shared kernel: app/core (config/db/errors/security/rbac/money/logging)
                 app/shared (uow · outbox · idempotency · jobs)
  ۱۷ پکیج دامنه: app/modules/*
        │ SQLAlchemy 2.0 (sync)              │ Celery (Prod) / InlineRunner (Dev)
PostgreSQL 16 — مرجع صحت، دفترکل append-only  Redis 7 — cache/broker
(فقط PG مرجع صحت است؛ Redis «نباید مرجع مانده باشد»)
```

تصمیم‌های معماری کلیدی (`docs/03`): SQLAlchemy 2.0 **sync** با psycopg2 تا کنترل هم‌زمانی با `SELECT … FOR UPDATE` صریح باشد (ADR-2)؛ کلید اصلی UUID و ستون `university_id` روی تمام جداول دامنه برای جداسازی دانشگاه‌ها سمت سرور (ADR-3)؛ امتیاز با `Numeric(14,2)` و Decimal — floating-point ممنوع (ADR-4)؛ Transactional Outbox + Inbox برای انتشار اتکاپذیر رویدادهای داخلی (ADR-6)؛ و Celery در تولید با InlineRunner در توسعه/آزمون — کد Task یکسان است و فقط Runner عوض می‌شود؛ وضعیت واقعی در `GET /api/v1/system/info` شفاف اعلام می‌شود (ADR-7). pgvector تا زمان نیاز واقعی به توصیه‌گر معنایی نصب نمی‌شود (ADR-8).

استقرار پیش‌فرض با docker-compose (فایل `docker-compose.yml` با نام پروژهٔ `bashgah360`) هفت سرویس دارد: `db` (postgres:16-alpine با healthcheck)، `redis` (redis:7-alpine)، `backend` (اجرای `alembic upgrade head` و سپس uvicorn)، `worker` و `beat` (هر دو `celery -A app.main.celery_app`)، `frontend` و `nginx` (nginx:1.27-alpine روی پورت ۸۰۸۹ که `/api/` را به backend و `/` را به frontend پروکسی می‌کند و هدرهای امنیتی CSP/X-Frame-Options/X-Content-Type-Options را ست می‌کند). نمونهٔ بخش اصلی:

```yaml
backend:
  build: ./backend
  environment:
    DATABASE_URL: postgresql+psycopg2://postgres:postgres@db:5432/club360_dev
    REDIS_URL: redis://redis:6379/0
  command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
worker:
  command: celery -A app.main.celery_app worker -l info
nginx:
  ports: ["8089:8089"]
```

نقطهٔ ورود `backend/app/main.py` همهٔ ۳۰ router دامنه را با پیشوند `/api/v1` ثبت می‌کند، نقطهٔ `/api/docs` (OpenAPI) را فعال می‌کند و فایل خصوصی را با لینک کوتاه‌عمر امضاشده در `/api/v1/files/{key}` سرو می‌کند. نقطه‌های سلامت `/healthz` (liveness) و `/readyz` (db+migrations+queue) برای Kubernetes/compose healthcheck در ماژول `integrations/system_router.py` پیاده شده‌اند.

## فصل ۳ — سه خدمت اصلی: امتیاز/سطح/نشان/پاداش، پیشنهاد شخصی‌سازی‌شده، نظارت اخلاقی و کشف سوءاستفاده

**۱. امتیاز، سطح، نشان و پاداش.** جریان مرجع «رویداد → امتیاز» (`docs/03`، بخش ۳) به این شکل است: LMS/Adapter رویداد را به `POST /api/v1/events/ingest` با احراز سرویس و امضای HMAC می‌فرستد؛ ماژول `event_ingestion` اعتبارسنجی قرارداد می‌کند، رویداد خام را غیرقابل تغییر ذخیره می‌کند و تکراری‌ها را با پاسخ idempotent بدون اثر دوم می‌پذیرد. Outbox در همان تراکنش پیام `EducationalEventReceived` می‌نویسد؛ Dispatcher آن را برمی‌دارد و `policy_engine` نسخهٔ سیاست **منتشرشدهٔ معتبر بر اساس `occurred_at`** (نه زمان پردازش) را انتخاب و DSL را با Trace کامل ارزیابی می‌کند. سپس `points_ledger` در یک Unit of Work با `Idempotency-Key = inbox_message_id`: award + LedgerEntryها + به‌روزرسانی حساب با Row Lock + BalanceProjection + استفادهٔ سقف انجام می‌دهد. رویدادهای داخلی `TierCheckRequested` و `BadgeCriteriaMet` از Outbox به `achievements_tiers` می‌رسند تا سطح (سه مسیر مستقل learning/skill/collaboration) و نشان صادر شود؛ درخواست پاداش در `rewards_fulfillment` ظرفیت و امتیاز را در **یک تراکنش** رزرو می‌کند. تضمین‌های آزمون‌شدهٔ این زنجیره: ارسال چندبارهٔ رویداد فقط یک اثر دارد، رزرو ظرفیت در مسابقهٔ هم‌زمان فقط یک برنده دارد، خرج چنددستگاهی هرگز مانده را منفی نمی‌کند، Retry Worker اثر مضاعف نمی‌سازد، اصلاح با سند جبرانی قابل پیگیری است، و قطع LMS هیچ کاهش امتیاز و پرچم تقلبی ایجاد نمی‌کند (نگاشت سناریوهای ۱ تا ۲۰ در `TEST_RESULTS.md`).

**۲. پیشنهاد شخصی‌سازی‌شده.** سرویس `recommendations/service.py` توصیه‌گر قاعده‌محور واقعی با نسخهٔ `rules-1.0` است (`docs/13`): هفت گام شامل بررسی رضایت شخصی‌سازی (تعیین `basis=consent_personal` یا `generic`)، فهرست پاداش‌های مجاز، فیلتر ظرفیت/زمان/شرایط/دسترس‌پذیری، تطبیق هدف و علایق، محدودکنندهٔ تنوع، تولید **دلیل واقعی محاسبه‌شده** (reasons_fa مثل «تناسب با هدف اعلامی» +۰٫۵، ظرفیت آزاد +۰٫۲) و ثبت بازخورد (like/dismiss/not_now). ورودی‌های ممنوع: دادهٔ مالی، سلامت و هر برچسب «ضعیف/پرریسک». اگر دانشجو رضایت شخصی‌سازی ندهد، کاتالوگ عمومی بدون دادهٔ شخصی کار می‌کند (سناریوی ۱۱، آزمون `test_no_consent_generic_recommendations`). هر اجرا با `inputs_snapshot` و نسخهٔ rule-pack ثبت می‌شود تا قابل حسابرسی باشد.

**۳. نظارت اخلاقی و کشف سوءاستفاده.** `integrity_reviews/service.py` دو لایه دارد: کنترل‌های قطعی (deterministic) که در صورت نقض raise/block می‌کنند، و الگوهای ریسک (risk_pattern) که **فقط** `ReviewCase` می‌سازند — هرگز حکم خودکار، جریمهٔ خودکار یا بلاک گسترده ندارند (TST-12؛ آزمون `test_signal_no_auto_penalty`). هر پرونده با `sla_due_at`، متن توضیح دانشجو (`case_explanations`) و تصمیم چهارحالته (cleared / violation_minor / violation_major / refer_official) بسته می‌شود و تصمیمِ مؤثر از مسیر سند جبرانی دفترکل اعمال می‌شود. مسیر مستقل اعتراض (`appeals`) با بررسی‌کنندهٔ متفاوت از بررسی‌کنندهٔ اولیه، پذیرش اعتراض را به اصلاح هم‌زمان دفترکل، سطح و نشان وصل می‌کند (سناریوی ۱۳). این طراحی «نظارت اخلاقی» را از ابزار سرزنش جدا می‌کند: سیگنال، هشدار است نه رأی.

## فصل ۴ — ماژول‌های backend

در `backend/app/modules/` **۱۷ پکیج دامنه** وجود دارد (README در بلوک «ساختار» عدد ۱۶ را نوشته که به پیش از افزوده‌شدن `club_experience` در v1.3 تعلق دارد). ترکیب فایل‌ها متفاوت است: برخی کامل (models/router/service)، چند ماژول فقط مدل یا فقط سرویس دارند و endpointهایشان در ماژول مجاور میزبانی می‌شود؛ `main.py` در مجموع ۳۰ router را ثبت می‌کند. فهرست کامل:

| # | ماژول | فایل‌ها | شرح واقعی |
| --- | --- | --- | --- |
| ۱ | `identity_access` | models + router + `sso.py` | هویت: universities/users/roles/sessions/auth_audit؛ ورود محلی، refresh کوکی‌محور، `/me`، break-glass؛ جریان کامل SSO/OIDC با state امضاشدهٔ HMAC و تنظیمات ثبت سامانه (`sso_settings_router`) |
| ۲ | `memberships_consents` | models + router + service | عضویت با ماشین‌حالت (draft→pending_terms→active→…)، نسخه‌های آیین‌نامه، رضایت‌ها (personalization/public_badge/notifications) و خروجی دادهٔ شخصی |
| ۳ | `student_goals` | models + router | هدف دانشجو، دوره‌های آموزشی و درخواست اصلاح داده؛ router اضافی ماژول برای شفاف‌بودن مرز؛ endpointهای goals/data-corrections در `recommendations/router` |
| ۴ | `event_ingestion` | models + router + service | دریافت رویداد: اعتبارسنجی قرارداد، HMAC، کلید یکتای مرکب، قرنطینه/dead-letter، خوداظهاری، تأیید انسانی و اصلاحیهٔ رویداد |
| ۵ | `policy_engine` | models + router + service | DSL نسخه‌دار JSON بدون eval، گردش draft→published با تأیید دوم، diff نسخه‌ها، شبیه‌سازی بی‌اثر و Trace ارزیابی |
| ۶ | `points_ledger` | models + router + service | هستهٔ مالی: award/verify_pending/reserve/release/spend/expire/adjust، projections بازسازی‌پذیر، trace تراکنش و حساب استخر (pool) دانشگاه |
| ۷ | `achievements_tiers` | models + router + service | سطوح سه‌مسیره، نشان‌ها با criteria JSONB، اشتراک نشان با توکن؛ میزبان endpointهای missions و groups هم هست |
| ۸ | `missions_groups` | فقط models | موجودیت‌های مأموریت، مشارکت، گروه یادگیری و سهم گروهی (با قید ضدامتیاز تکراری)؛ منطق و endpoint در `achievements_tiers` |
| ۹ | `rewards_fulfillment` | models + router + service | کاتالوگ پاداش، ماشین‌حالت درخواست، رزرو هم‌زمان ظرفیت+امتیاز، صف ارائه‌دهنده، callback با HMAC، reconciliation و TTL sweeper |
| ۱۰ | `recommendations` | models + router + service | توصیه‌گر قاعده‌محور + بازخورد؛ router این ماژول میزبان ۸ router دیگر است: notifications، analytics، audit، reviews، appeals، goals، data-corrections |
| ۱۱ | `integrity_reviews` | models + service | کنترل‌های قطعی و الگوهای ریسک؛ ساخت پروندهٔ بررسی بدون حکم خودکار |
| ۱۲ | `appeals` | models + service | اعتراض مستقل با بررسی‌کنندهٔ متفاوت و outcome شامل سند جبرانی دفترکل و بازمحاسبهٔ سطح/نشان |
| ۱۳ | `notifications` | models + service | اعلان با ترجیح کاربر، ساعات سکوت، سقف روزانه، حذف تکرار و payload بدون دادهٔ حساس؛ نوع‌های transactional مجزا |
| ۱۴ | `analytics` | فقط `__init__` | پکیج جایگاه‌دار؛ endpoint `/analytics/overview` و شاخص‌های ANA در `recommendations/router` پیاده شده‌اند |
| ۱۵ | `audit` | models + service | نوشتن رکوردهای audit_log (append-only با trigger) برای هر عمل حساس، با correlation_id و IP ماسک‌شده |
| ۱۶ | `integrations` | `adapters.py` + `system_router.py` | Adapterهای قراردادی زیرسیستم‌های اکوسیستم (Identity/Academic/Learning/…؛ حالت simulator) و endpointهای system/info، healthz، readyz، metrics |
| ۱۷ | `club_experience` | models + router + service | لایهٔ تجربهٔ v1.3: onboarding سه‌قدمی، دعوت دوست بدون امتیاز، فضای دستاوردهای رضایت‌محور (`/api/v1/club-experience/*`) |

نکتهٔ معماری قابل توجه برای توسعه‌دهندهٔ جدید: میزبانی چند router در یک فایل (مثلاً هشت router عملیاتی در `recommendations/router.py` و چهار router در `achievements_tiers/router.py`) یک تصمیم آگاهانه برای کوچک نگه‌داشتن مرزهای دامنه است، اما یعنی نام پکیج همیشه با گروه URL یکی نیست (مثلاً `/api/v1/notifications` از ماژول recommendations سرو می‌شود). هنگام افزودن قابلیت جدید، جدول بالا و قانون import بخش ۷ `docs/03` را مبنا بگیرید: منطق در service، router بدون منطق، و ارتباط بین ماژول‌ها فقط با سرویس یا رویداد Outbox.

## فصل ۵ — مدل داده، مایگریشن و یکپارچگی

مدل داده به‌صورت واقعی در `backend/app/modules/*/models.py` تعریف شده و مایگریشن اولیهٔ آن `alembic/versions/278c1303e6e6_initial_schema.py` است. همهٔ جداول دامنه کلید UUID با `gen_random_uuid`، ستون `university_id` (جداسازی دانشگاه)، `created_at/updated_at` از نوع TIMESTAMPTZ با UTC، و برچسب `source`/`retention_class` برای سیاست نگهداری دارند؛ FKها با `ON DELETE RESTRICT` ساخته شده‌اند تا حذف مولد ممنوع باشد و حذف PII فقط از مسیر ناشناس‌سازی مصوب (`anonymization_log`) ممکن شود. نمای موجودیت‌ها به تفکیک ماژول در `docs/04-data-model.md` کامل است — از `users`/`user_role_scopes` و `consent_records` گرفته تا `ledger_transactions`/`ledger_entries`، `reward_requests`/`reward_reservations` و `outbox_messages`.

پنج مایگریشن Alembic تا امروز وجود دارد: اسکیمای اولیه، `a1b2c3d4e5f6_integrity_triggers`، `b2c3d4e5f6a7_external_identities` (پیوند هویت SSO)، `c3d4e5f6a7b8_sso_system_settings` (جدول تک‌ردیفی تنظیمات ثبت سامانه) و `d4e5f6a7b8c9_club_experience` (فیلدهای تجربهٔ باشگاه v1.3). مایگریشن triggers مهم‌ترین لایهٔ یکپارچگی است:

- **بی‌ردپا (append-only):** تابع `deny_mutate_{table}` هر UPDATE/DELETE را با `RAISE EXCEPTION` رد می‌کند؛ روی `ledger_entries`، `audit_logs`، `educational_events` و `auth_audit` فعال است. حتی با دسترسی مستقیم به DB، ویرایش سابقهٔ مالی/حسابرسی ممکن نیست.
- **قید توازن:** `CONSTRAINT TRIGGER trg_ledger_tx_balanced` (DEFERRABLE) در لحظهٔ COMMIT برای هر ردیف `ledger_transactions` برابری Σdebit=Σcredit را بررسی می‌کند؛ این قید در اجرای واقعی یک خطای طراحی در مسیر spend را گرفت و اصلاح شد (`TEST_RESULTS.md`).

ناوردایی‌های دیگر در خود اسکیما هستند: `point_accounts` با CHECK موجودی‌های غیرمنفی (available/reserved/pending ≥ 0)؛ ایندکس جزئی یکتا روی `ledger_transactions(idempotency_key) WHERE NOT NULL` که اثر مضاعف فرمان‌ها را در سطح DB بسته می‌کند؛ کلید یکتای مرکب `(university_id, source_id, event_id)` روی `educational_events` که تکرار رویداد را ناممکن می‌کند؛ قید یکتای `(policy, version_no)`؛ و `uq(student_ref, version, window_key)` روی `policy_cap_usage` برای اجرای هم‌زمانِ سقف‌ها. شمارندهٔ `seq` جدول دفترکل در حالت قابل‌حمل (SQLite) با شمارندهٔ درون‌پردازشی جایگزین می‌شود اما حساب‌ها همیشه از جمع رکوردها بازسازی می‌شوند (`app/portable.py`).

الگوی **Inbox/Idempotency**: پیام‌های ورودی در `event_inbox` با `state`، `attempts`، `next_retry_at` و `quarantined_reason` نگهداری می‌شوند؛ پردازش هر پیام با `Idempotency-Key = inbox_message_id` انجام می‌شود، پس اجرای دوبارهٔ Worker (Retry Worker) اثر امتیازی مضاعف نمی‌سازد. در سطح API نیز فرمان‌های حساس (`/reward-requests`، `/events/ingest`، `/appeals`، `/data-corrections`) هدر `Idempotency-Key` می‌پذیرند: کلید تکراری با payload یکسان پاسخ ذخیره‌شده را برمی‌گرداند و با payload متفاوت خطای `409 IDEMPOTENCY_CONFLICT` می‌دهد (`shared/idempotency.py`، API-04). الگوی **Outbox**: تغییرات حالت در همان تراکنش کسب‌وکار در `outbox_messages` نوشته می‌شوند (state: pending/dispatched/failed) و Worker آن‌ها را at-least-once منتشر می‌کند؛ مصرف‌کننده‌ها idempotent هستند و ادعای exactly-once شبکه‌ای انجام نمی‌شود (ADR-6). واحد کار تراکنشی `shared/uow.py` خطاهای deadlock/serialization را حداکثر ۳ بار با backoff تصادفی تکرار می‌کند و کلاس `jobs.py` با جدول `background_jobs` و Job Status API وضعیت کارهای پس‌زمینه را شفاف نگه می‌دارد. سیاست نگهداری پیش‌فرض نیز نسخه‌گذاری شده: دفترکل/آدیت دائمی، payload رویداد ۳۶ ماه، اعلان‌ها ۱۲ ماه، snapshot توصیه‌گر ۱۸ ماه (بخش ۳ `docs/04`).

## فصل ۶ — امنیت، احراز هویت و RBAC

هر لایهٔ امنیتی در کد واقعی قابل اشاره است. **رمز و توکن** (`app/core/security.py`): هش رمز با bcrypt (rounds=10)، توکن دسترسی JWT با HS256 و عمر کوتاه (`access_token_minutes`؛ قرارداد نمونهٔ `docs/06` مقدار ۹۰۰ ثانیه)، refresh به‌صورت hash یکتا در جدول `sessions` و ارسال با کوکی HttpOnly/SameSite=Lax (Secure در تولید)، و امضای HMAC برای webhook سرویس‌ها. **میان‌افزار** (`main.py`): Rate limit درون‌حافظه‌ای per-IP (در تولید Redis) با پاسخ `429 RATE_LIMITED` ساختاریافته، و بررسی Origin برای متدهای ناامن cookie-auth در مسیرهای `/api/v1/auth` (ضد CSRF). فایل خصوصی فقط با لینک امضاشدهٔ کوتاه‌عمر سرو می‌شود و nginx هدرهای CSP، X-Frame-Options، nosniff و Referrer-Policy را اعمال می‌کند (`nginx/nginx.conf`). ورود یکپارچه در `identity_access/sso.py` جریان OIDC Authorization Code با سامانهٔ مرکزی است: state امضاشدهٔ HMAC با عمر محدود (ضد CSRF)، کشف خودکار endpoints از issuer، هویت **فقط** از userinfo، هیچ نقشی از توکن IdP پذیرفته نمی‌شود (تأمین با نقش پیش‌فرض student)، عدم تصاحب حساب‌های رمزدار و پیوند حساب در `external_identities`. پیکربندی از `.env` خوانده می‌شود (`SSO_ISSUER/SSO_CLIENT_ID/SSO_CLIENT_SECRET/SSO_REDIRECT_URI`) و راز Client هرگز در UI یا DB ذخیره نمی‌شود. صفحهٔ `/admin/sso` (v1.2) با `GET|PUT /api/v1/admin/sso-settings` قرینهٔ ثبت این سامانه در پورتال مرکزی است — پیش‌فرض‌ها در مایگریشن `c3d4e5f6a7b8`: کلید `daneshjooclub`، Client ID `daneshjooclub360`، آیکن 🥇، ترتیب ۱۴، فعال — و تغییرات در Audit ثبت می‌شود.

**RBAC** (`app/core/rbac.py`) دو جزء دارد: allowlist مجوزها (۳۱ مجوز؛ هیچ مجوزی بیرون از این مجموعه قابل تخصیص نیست) و نگاشت نقش‌ها. نقش‌های واقعی کد:

| نقش (`role_code`) | مجوزهای کلیدی |
| --- | --- |
| `student` | ledger:read_own، rewards:request، appeals:submit، notifications:read_own، data:export_own، events:self_report |
| `professor` | approvals:verify (تأیید فعالیت آموزشی) |
| `advisor` | advisor:read (فقط دانشجویان تخصیص‌یافته) |
| `club_manager` | memberships:manage، policies:write/simulate، rewards:manage/approve، missions:manage، badges:manage، events:manage، ledger:read، analytics:read، notifications:manage |
| `policy_officer` | policies:read/approve، analytics:read (تأییدکنندهٔ دوم سیاست) |
| `reward_provider` | rewards:deliver (فقط صف و ثبت تحویل خودش) |
| `edtech_specialist` | reviews:handle، ledger:read |
| `appeal_referee` | appeals:review، ledger:read |
| `tech_admin` | tech:admin — صریحاً بدون هیچ مجوز دادهٔ آموزشی |
| `auditor` | audit:read، analytics:sensitive (فقط ارزیابی انصاف) |

علاوه بر این‌ها، `Principal` سرویس برای `events:ingest` و `providers:callback` از مسیر HMAC ساخته می‌شود (`is_service=True`). نقش‌ها در `user_role_scopes` با `university_id`، `department`، `expires_at` و پرچم `is_emergency` (مسیر break-glass اختصاصی در router auth) تخصیص می‌یابند و همهٔ جست‌وجوها با فیلتر `university_id` از Principal اعمال می‌شوند — جداسازی دانشگاه در آزمون قرارداد تأیید شده است. سه سناریوی حدی در آزمون‌ها مستندند: ارائه‌دهندهٔ دادهٔ اضافی نمی‌بیند (field-minimal در `/providers/queue`)، مدیر فنی بدون Scope دادهٔ آموزشی نمی‌بیند، و حسابرس فقط Audit و شاخص انصاف می‌بیند. در frontend نیز RBAC به‌صورت آینه در سطح Route تکرار شده (`RequirePerm`/`RequireRoles` در `App.tsx`) تا کاربر به صفحهٔ خالی برخورد نکند؛ اما مرجع تصمیم همیشه سرور است.

## فصل ۷ — موتور سیاست و دفترکل

موتور سیاست (`policy_engine/service.py`) DSL نسخه‌دار JSON را **بدون eval** ارزیابی می‌کند (PNT-02)؛ گارد CI `scripts/guard_no_eval.py` هر استفاده از `eval/exec/__import__` را در کل backend می‌گردد و در workflow CI اجرا می‌شود. عملگرهای مجاز فقط `== != > >= < <= in not_in between` هستند و مقادیر فقط ثابت. نمونهٔ واقعی از seed (`ATT-BASE`, `rule_id=attendance_base_v1`):

```json
{
  "rule_id": "attendance_base_v1",
  "event_type": "meaningful_attendance_verified", "path": "learning",
  "conditions": {"all": [{"field": "payload.duration_minutes", "op": ">=", "value": 45}]},
  "base_points": "10.00",
  "quality_multiplier": {"field": "payload.quality", "map": {"high": "1.20", "normal": "1.00"}, "default": "1.00"},
  "repeat_policy": {"window_days": 7, "diminishing": ["1.00", "1.00", "0.50", "0.25"], "beyond": "0"},
  "caps": {"per_day": "30.00", "per_period": "300.00"},
  "exclusive_group": "attendance",
  "late_policy": {"max_late_hours": 72, "factor": "1.00"},
  "human_reason_template": "حضور معنادار تأییدشده در {activity_reference}"
}
```

چرخهٔ نسخه‌گذاری کامل است: policy_officer نسخهٔ draft می‌سازد، `POST /policy-approvals` تأیید دوم را ثبت می‌کند (requester≠approver در سرویس اعمال می‌شود)، نسخهٔ published قفل می‌شود و برای گذشته بازنویسی نمی‌گردد — انتخاب نسخه بر اساس `occurred_at` رویداد است، پس رویداد دیررس یا خارج‌ازترتیب با سیاستِ زمانِ وقوعش امتیاز می‌گیرد (سناریوهای ۲ و ۷). هر ارزیابی یک ردیف `rule_evaluations` با `conditions_result`، `effective_inputs`، `caps_applied`، گردکردن و `final_points` به‌همراه reason فارسی انسانی می‌سازد؛ `GET /ledger/{tx_id}/trace` همین Trace را برمی‌گرداند (PNT-05). شبیه‌سازی (`POST /simulations`) بدون اثر عملیاتی است و در `rule_simulations` ثبت می‌شود.

**دفترکل و رزرو هم‌زمان.** سرویس `points_ledger` عملیات award/reserve/release/spend/expire/adjust را با Row Lock روی `point_accounts` و bucketهای available/pending انجام می‌دهد؛ `cumulative_progress` مستقل از spending است (سناریوی ۸). در مسیر پاداش (`rewards_fulfillment/service.py::request_reward`) رزرو ظرفیت و رزرو امتیاز در **یک تراکنش** با قفل ردیف `reward_capacities` انجام می‌شود؛ مسابقهٔ ظرفیت فقط یک برنده دارد و درخواست فعالِ تکراری با ایندکس جزئی روی `(student_ref, reward, active_states)` بسته می‌شود. سقف‌ها با `policy_cap_usage` و قفل ردیف در پردازش موازی رعایت می‌شوند (سناریو ۱۹: Σ امتیاز ≤ سقف روزانه در ۶ رشتهٔ هم‌زمان). **اصلاح و جبران:** تعدیل دستی (`ledger.adjust`) و تصمیم پرونده/اعتراض، تراکنش جبرانی با `correction_of` ارجاع به تراکنش مبدأ می‌سازند تا مسیر اصلاح قابل پیگیری بماند (سناریوهای ۶ و ۱۳). **Retry Worker:** پیام‌های inbox/outbox با attempts و next_retry_at دوباره اجرا می‌شوند و به لطف Inbox + کلید یکتا + idempotency_key بدون اثر مضاعف‌اند (سناریو ۵). **TTL و Reconciliation:** `sweep_expired` رزروهای منقضی را آزاد می‌کند (سناریو ۲۰)، پاسخ `unknown` ارائه‌دهنده به‌جای استرداد خودکار `ReconciliationCase` می‌سازد (سناریو ۹) و صف کارهای پس‌زمینه با Celery beat (تولید) یا InlineRunner (سندباکس) اجرا می‌شود — تفاوت فقط در Runner است و در `/system/info` شفاف اعلام می‌شود.

## فصل ۸ — تجربهٔ باشگاه v1.3 و ارتقای گرافیک v1.4

نسخهٔ ۱٫۳ تجربهٔ کاربر را از «امتیاز گرفتن برای فعالیت» به «ماجراجویی، ساختن، ارتباط و دستاورد قابل‌نمایش» منتقل کرد — بدون هیچ تغییری در منطق امتیاز/سیاست/دفترکل؛ همهٔ ایده‌ها در چارچوب آیین‌نامه (داوطلبانه، بدون اثر بر نمره، بدون رقابت فرساینده) ماندند. ماژول جدید `app/modules/club_experience` با endpointهای `/api/v1/club-experience/onboarding|invites|showcase` و مایگریشن `d4e5f6a7b8c9` تحویل شد و ۸ آزمون جدید به مجموعه افزود (۴۸/۴۸).

- **شروع فوری «اولین دستاورد در ۱۵ دقیقه»:** صفحهٔ `/onboarding` سه قدم دارد — انتخاب مسیر انتخابی، انتخاب علاقه‌ها (حداکثر ۵) و بازکردن اولین مأموریت. پس از عضویت کاربر خودکار به همین جریان می‌رود؛ نشان «اولین قدم» بلافاصله و فقط یک‌بار صادر می‌شود (`onboarding_profiles` + `_ensure_first_badge`). اصل مهم: **هیچ سند امتیازی از onboarding و دعوت ساخته نمی‌شود** — امتیاز فقط از سیاست‌های مصوب می‌آید (آزمون‌شده).
- **مسیرهای انتخابی ملموس:** سازنده/کاوشگر/همیار/متخصص/راهبر؛ هر کدام فقط برچسب تجربهٔ همان سه مسیر مصوب سطح‌بندی (learning/skill/collaboration) است.
- **مأموریت‌های واقعی با خروجی ملموس:** فیلد `mission_kind` (رویداد آغازین، چالش ۲۰ دقیقه‌ای، مأموریت یک‌روزه، کارگاه آزمایشی، یک عصر یک مهارت، مسئلهٔ واقعی، راهنما) به‌همراه `output_fa`، `duration_label_fa`، `team_size_hint` و `interest_tags`؛ فیلترهای «کوتاه و کم‌تعهد» و «تیمی و واقعی» در UI.
- **گروه‌های کوچک علاقه‌ای:** `GET /api/v1/groups` با هدف روشن، زمان محدود و خروجی مشخص («یک هفته، سه نفر، یک ایدهٔ قابل‌ارائه»)؛ چهار گروه نمونه در seed.
- **دعوت دوست برای مأموریت مشترک:** `POST /club-experience/invites` فقط برای عضو فعلی مأموریت (۴۰۹ بدون عضویت)، کد یک‌بارمصرف، ممنوعیت پذیرش دعوت خود و غیردانشجو؛ **هیچ امتیازی برای تعداد دعوت‌ها نیست** و این در UI صریح است.
- **فضای دستاوردها به‌جای رتبه‌بندی** (`/showcase`): روایت‌های کوتاه «این تیم چه ساخت؟ / چه مسئله‌ای حل کرد؟ / چه مهارتی تجربه شد؟» فقط با رضایت (`has_consent`)؛ خروجی API هیچ فیلد رتبه/امتیازی ندارد (آزمون‌شده) و نشان بدون رضایت منتشر نمی‌شود.
- **نشان‌های داستان‌محور و پاداش تجربه‌ساز:** فیلد `story_fa` («اولین قدم، سازنده، هم‌مسیر، حل‌گر، پیوسته») و فیلد `kind` برای پاداش‌ها (experience/choice/resource/physical) با فیلتر «فقط پاداش‌های تجربه‌ساز» — کارگاه با متخصص، بازدید آزمایشگاه، بازخورد نمونه‌کار، حق انتخاب موضوع رویداد بعدی و منتورینگ. رویداد آغازین (kind=kickoff) با کارت ویژه و پیام تجربه‌محور در صفحهٔ عضویت معرفی می‌شود.

اصلاح رگرسیون مهم v1.3: دیالوگ‌های مودال به‌دلیل transformِ انیمیشن ورود زیر صفحه رندر می‌شدند و اکنون با portal به `document.body` مونت می‌شوند (کشف‌شده در دودتست مرورگر واقعی Chromium).

**ارتقای گرافیک v1.4** در کد frontend است (`frontend/src/index.css` و `src/components/ui.tsx`): پالت جوان و شاد با افزودن بنفش/صورتی/نارنجی/لیمویی به نیلی/فیروزه‌ای/طلایی، کارت‌های آماری رنگی با حباب آیکن گرادیانی و glow (`HUES`/`StatCard`)، حلقهٔ پیشرفت گرادیانی SVG با انیمیشن پرشدن، جشن کاغذرنگی (confetti) برای دستاورد، و کامل‌بودن حالت تاریک با کلاس `.dark` و توکن‌های کنتراست-بررسی‌شده. حرکت‌ها همچنان محدود و `prefers-reduced-motion` محترم شمرده می‌شود؛ این نسخه هنوز فایل Release Notes مستقل ندارد و در نسخهٔ بستهٔ قابل‌حمل پیش‌فرض (`v1.3.1` در `build_portable.py`) لحاظ نشده — یعنی گرافیک v1.4 با بیلد فعلی frontend همراه می‌شود اما برچسب نسخهٔ مستقل نگرفته است.

## فصل ۹ — رابط کاربری و سیستم طراحی

frontend یک SPA مستقل در `frontend/` است: React 18 + Vite + TypeScript با Tailwind CSS در جهت RTL کامل. وابستگی‌های اصلی (از `package.json`): `react-router-dom` برای مسیریابی، `@tanstack/react-query` برای دادهٔ سرور، `react-hook-form` + `zod` برای فرم‌های اعتبارسنجی‌شده، Radix UI (Dialog/Switch/Tabs) برای پرimitivesهای دسترس‌پذیر، Recharts برای نمودارها، framer-motion برای انیمیشن‌های محدود و lucide-react برای آیکن‌ها. فونت فارسی Vazirmatn به‌صورت محلی با `@fontsource/vazirmatn` باندل می‌شود (وزن‌های ۴۰۰/۵۰۰/۷۰۰/۸۰۰ در `index.css`) — بدون درخواست CDN خارجی. متن ترکیبی فارسی/لاتین با `dir="auto"` و اعداد امتیاز با جداکنندهٔ هزارگان فارسی‌نما (`lib/format.ts`) نمایش داده می‌شوند؛ ذخیره و تبادل زمان UTC/ISO-8601 است و نمایش به تقویم شمسی و منطقهٔ زمانی دانشگاه انجام می‌شود.

**دیزاین‌توکن‌ها** در `src/design/tokens.ts` و متغیرهای CSS (`index.css`) تعریف شده‌اند: `--c-bg/surface/primary/accent/gold` به‌علاوهٔ رنگ‌های شاد v1.4 (`--c-violet/pink/orange/lime`)، مقیاس فاصلهٔ 4px، شعاع‌های sm/md/lg/full و مدت‌های حرکت (fast 120ms / base 200ms / celebrate 600ms). حالت تاریک با کلاس `.dark` همهٔ توکن‌ها را با جفت‌های کنتراست-بررسی‌شده عوض می‌کند (در تاریک، primary به نیلی روشن تبدیل می‌شود). کامپوننت‌های پایه در `src/components/ui.tsx` دست‌سازند: Card، Chip وضعیت (همیشه آیکون+متن، نه فقط رنگ)، Dialog با trap-focus، Toast با aria-live، StatCard با حباب آیکن، ProgressRing و Progress خطی با role="progressbar"، ProgressPath مسیر سطح، PointsDualCard که «قابل مصرف» و «پیشرفت تجمعی» را **مستقل** نشان می‌دهد، و AppShell با Skip Link. تصویرسازی و نشان‌ها SVG اصل درون‌ریپو هستند (`illustrations.tsx`) و هر نمودار Recharts خلاصهٔ متنی/جدول جایگزین دارد.

**صفحات نقش‌محور:** سند طراحی (`docs/07`، بخش ۷) ۲۲ صفحه را نگاشت الزامات کرده و پیاده‌سازی واقعی در `App.tsx` ۲۶ مسیر react-router دارد (شامل `/login`) که فایل‌های `src/pages/*` آن را پر می‌کنند: مسیرهای دانشجو (`/onboarding`، `/goals`، `/ledger`، `/badges`، `/missions`، `/rewards`، `/requests`، `/recommendations`، `/showcase`، `/privacy`)، استاد (`/approvals`)، مشاور (`/advisees`)، مدیر باشگاه (`/admin`، `/admin/policies`، `/admin/catalog`، `/admin/health`، `/admin/sso`)، مسئول سیاست (`/policy-approvals`)، کارشناس سلامت آموزشی (`/review-cases`)، مرجع اعتراض (`/appeals-queue`)، ارائه‌دهنده (`/provider`)، حسابرس (`/audit`) و مدیر فنی (`/tech`). دروازهٔ نقش سمت کلاینت با دو helper `RequirePerm`/`RequireRoles` فقط «آینهٔ» RBAC سرور است تا کاربر به صفحهٔ خالی برخورد نکند؛ مرجع تصمیم همیشه backend است. Skeleton برای هر Query، EmptyState فارسی (مثل «هنوز تراکنشی ثبت نشده…») و نوار وضعیت Offline پیاده شده‌اند.

**دسترس‌پذیری (UX-08، WCAG 2.2 AA):** ناوبری کامل صفحه‌کلید، Skip Link، focus-visible با حلقهٔ 2px، هدف لمسی ≥44px، Dialog/فرم/جدول صفحه‌خوان‌پذیر (label متصل، aria-describedby، th scope)، خلاصهٔ متنی نمودارها و مسیر کم‌مصرف (SVG، چانک‌بندی Route-level، فونت subset). طبق ماتریس الزامات، پیاده‌سازی انجام شده اما **ممیزی ابزاری axe/Playwright هنوز اجرا نشده** و صریحاً به استقرار واقعی موکول شده است. **آزمون UI** با Vitest + Testing Library (`src/test/ui.test.tsx`، ۶ آزمون) پوشش رندر پایهٔ کامپوننت‌ها را می‌دهد و در CI اجرا می‌شود.

## فصل ۱۰ — APIها

همهٔ مسیرها با پیشوند `/api/v1` سرو می‌شوند؛ مرجع کامل و قابل‌تولید، OpenAPI در `/api/docs` است. قراردادهای سراسری (`docs/06`): خطای ساختاریافتهٔ `{code, message, correlation_id, details}`، هدر `Idempotency-Key` برای فرمان‌های حساس، صفحه‌بندی امن (`page_size ≤ 100`، sort/filter از allowlist) و تاریخ ISO-8601 UTC. مجموعاً ۹۵ endpoint در ۳۰ router ثبت شده‌اند (به‌علاوهٔ `GET /api/v1/files/{key}` در main.py برای فایل خصوصی امضاشده)؛ جدول زیر مهم‌ترین‌ها را با مجوز RBAC واقعی کد خلاصه می‌کند:

| مسیر (بدون پیشوند) | متد | مجوز لازم | شرح |
| --- | --- | --- | --- |
| `/auth/login` | POST | عمومی | ورود محلی؛ access token + کوکی refresh |
| `/auth/refresh` · `/auth/logout` | POST | کوکی refresh | چرخش/ابطال نشست |
| `/auth/me` · `/auth/break-glass` | GET · POST | کاربر واردشده | پروفایل Principal؛ scope اضطراری |
| `/auth/sso/status` | GET | عمومی | وضعیت SSO + نام/آیکن دکمهٔ ورود |
| `/auth/sso/login` · `/auth/sso/callback` | GET | عمومی | شروع/تکمیل جریان OIDC (state امضاشدهٔ HMAC) |
| `/admin/sso-settings` | GET · PUT | club_manager یا tech_admin | تنظیمات ثبت سامانه در پورتال؛ ثبت در Audit |
| `/memberships/join` · `/me` · `/exit` · `/export` | POST · GET · POST · GET | ledger:read_own / data:export_own | عضویت، وضعیت، خروج؛ خروجی دادهٔ شخصی |
| `/consents/{type}` · `/consents` | PATCH · GET | ledger:read_own | تغییر/مشاهدهٔ رضایت‌ها |
| `/events/ingest` | POST | سرویس (`events:ingest` + HMAC) | ورودی رویداد آموزشی؛ idempotent |
| `/events/self-report` | POST | events:self_report | خوداظهاری با تأیید انسانی |
| `/events/{id}/verify` · `/events/pending-verification` | POST · GET | approvals:verify | تأیید فعالیت (نقش استاد) |
| `/events/dead-letter` · `…/requeue` | GET · POST | events:manage | قرنطینه/ارسال مجدد مدیر باشگاه |
| `/policies` (+`/{id}/versions`، `…/submit`، `…/diff`) | GET · POST | policies:read / policies:write | چرخهٔ نسخهٔ سیاست |
| `/policy-approvals` (+`/pending`) | POST · GET | policies:approve | تأیید دوم (مسئول سیاست) |
| `/simulations` | POST | policies:simulate | شبیه‌سازی بی‌اثر روی دفترکل |
| `/points/summary` | GET | ledger:read_own | مانده‌ها + سطح فعلی |
| `/ledger` · `/ledger/{tx}/trace` | GET | ledger:read_own | دفترکل شخصی + Trace محاسبه |
| `/tiers/me` · `/badges/me` · `/badges/share` · `…/revoke-share` | GET · POST | ledger:read_own | سطح/نشان/اشتراک نشان با رضایت |
| `/missions` (+`/{id}/join`، `/{id}/quit`) | GET · POST | ledger:read_own / missions:manage | فهرست/عضویت مأموریت؛ ایجاد: مدیر |
| `/groups` (+`/members`، `/contributions`) | GET · POST | ledger:read_own / missions:manage / approvals:verify | گروه‌های علاقه‌ای و ثبت سهم تأییدشده |
| `/rewards` · `/rewards/{id}` | GET · POST | ledger:read_own / rewards:manage | کاتالوگ؛ ایجاد آیتم: مدیر |
| `/reward-requests` (+`/cancel`، `/approve`، `/deliver`، `/receipt`) | POST · GET | rewards:request / rewards:approve | رزرو هم‌زمان ظرفیت+امتیاز؛ گردش تحویل |
| `/providers/queue` · `/providers/{id}/callback` · `/providers/reconciliation` (+`/resolve`) | GET · POST | rewards:deliver / rewards:approve / سرویس (`providers:callback`) | صف فیلد-کمینه؛ callback با HMAC؛ پروندهٔ تحویل نامعلوم |
| `/recommendations` · `/recommendations/feedback` | GET · POST | ledger:read_own | پیشنهاد + بازخورد |
| `/notifications` (+`/preferences`) | GET · PATCH · POST | notifications:read_own | اعلان‌ها و ترجیحات |
| `/reviews/cases` (+`/explanation`، `/transition`، `/decide`) | GET · POST | reviews:handle / ledger:read_own | پروندهٔ سلامت آموزشی |
| `/appeals` (+`/queue`، `/assign`، `/decide`) | POST · GET | appeals:submit / appeals:review | اعتراض و رسیدگی مستقل |
| `/goals` (+`/periods`) · `/data-corrections` | GET · POST | ledger:read_own / policies:read / appeals:submit | اهداف، دوره‌ها، اصلاح داده |
| `/club-experience/onboarding` · `/invites` (+`/accept`) · `/showcase` | GET · POST | ledger:read_own / missions:manage | تجربهٔ باشگاه v1.3 |
| `/system/info` · `/healthz` · `/readyz` · `/metrics` | GET | عمومی | شفافیت حالت (mode=simulator، queue_backend) و سلامت |

## فصل ۱۱ — آزمون‌ها و تضمین کیفیت

نتایج مرجع، فایل `backend/TEST_RESULTS.md` است: آخرین اجرا **۴۸/۴۸ پاس** روی PostgreSQL 16.2 واقعی (باینری رسمی، socket یونیکس؛ بدون SQLite — الزام SEC-15) با فرمان `pytest -q`. تاریخچهٔ نسخه‌ها: ۲۸/۲۸ در MVP، ۳۶/۳۶ با افزودن ۸ آزمون SSO (v1.1)، ۴۰/۴۰ با ۴ آزمون تنظیمات SSO (v1.2) و ۴۸/۴۸ با ۸ آزمون تجربهٔ باشگاه (v1.3). ترکیب واقعی ۴۸ آزمون در هشت فایل `backend/tests/`:

| فایل آزمون | تعداد | پوشش |
| --- | --- | --- |
| `test_api_contract.py` | ۶ | قرارداد HTTP: خطای ساختاریافته، RBAC، جداسازی دانشگاه، Idempotency-Key (تکرار/Conflict)، قرارداد ingest |
| `test_events_and_policy.py` | ۴ | اثر واحد رویداد تکراری، انتخاب سیاست خارج‌ازترتیب، قفل‌بودن گذشته، قطع LMS بدون جریمه |
| `test_ledger_concurrency.py` | ۳ | مسابقهٔ ظرفیت (ThreadPool واقعی)، خرج چنددستگاهی، سقف در پردازش موازی |
| `test_ledger_invariants.py` | ۴ | Retry Worker، سند جبرانی قابل پیگیری، پیشرفت مستقل از خرج + Property test با hypothesis (توازن/غیرمنفی/بازسازی Projection) |
| `test_rewards_flow.py` | ۴ | گردش کامل، رد گذار غیرمجاز، TTL رزرو منقضی، Reconciliation بدون استرداد خودکار |
| `test_domain_rules.py` | ۷ | خروج بدون قطع خدمات، توصیهٔ عمومی بدون رضایت، سیگنال بدون حکم خودکار، اصلاح با اعتراض، رضایت انتشار نشان، field-minimal ارائه‌دهنده، مدیر فنی بدون دادهٔ آموزشی |
| `test_sso.py` | ۱۲ | امضای state، تأمین کاربر، پیوند حساب، عدم تصاحب حساب رمزدار، عدم ارتقای نقش از توکن IdP، تنظیمات ثبت سامانه |
| `test_club_experience.py` | ۸ | onboarding سه‌قدمی، نشان یک‌بار «اولین قدم»، صفر سند امتیازی از onboarding/دعوت، قواعد دعوت (۴۰۹/۴۰۳)، دروازهٔ رضایت showcase، فیلدهای تجربه‌محور |

نگاشت ۲۰ سناریوی الزامی سند کارفرما به آزمون‌ها در TEST_RESULTS جدول شده و هر سناریو یا «پاس» دارد یا صریحاً «اجرا نشده» (مثل سناریوی ۱۸: صفحه‌کلید/صفحه‌خوان با Playwright+axe). **CI دو workflow دارد** در `.github/workflows/`: `ci.yml` با سه job — backend روی runner با سرویس postgres:16 (install → `alembic upgrade head` → **گارد PNT-02** با `scripts/guard_no_eval.py` → bandit → `pytest -q`)، frontend (npm ci → build/tsc → Vitest؛ با کامنت محل اجرای Playwright/axe در CI کامل) و docker (`docker compose build`)؛ و `release.yml` که با push تگ `v*` SPA می‌سازد، با `scripts/build_portable.py` بستهٔ ویندوز/لینوکس می‌سازد و GitHub Release با یادداشت‌های `docs/release/RELEASE_NOTES_v*.md` منتشر می‌کند. کیفیت متن با گارد PNT-02 (ممنوعیت eval/exec در کل backend) و اسکن bandit تضمین می‌شود؛ نتیجهٔ هر اجرا باید در TEST_RESULTS به‌روز شود تا ادعای README همیشه به اجرای واقعی گره بخورد. آزمون‌های تاریخ‌دار به‌صورت نسبی به اکنون ساخته می‌شوند (اصلاح ثبت‌شده در v1.1) تا مثل پنجرهٔ دیررس ۷۲ ساعته فرسوده نشوند.

## فصل ۱۲ — استقرار، نسخهٔ قابل‌حمل و نقشهٔ راه

سه مسیر اجرا مستند و آزموده‌اند: (A) سندباکس بدون Docker با pgserver محلی (`alembic upgrade head && python -m app.seed && uvicorn`)؛ (B) `docker compose up --build` با هفت سرویس فصل ۲ (db، redis، backend، worker، beat، frontend، nginx روی پورت ۸۰۸۹) و پیکربندی SSO از `.env`؛ (C) بستهٔ قابل‌حمل. `scripts/build_portable.py` دو بستهٔ `club360-portable-windows-x64.zip` و `club360-portable-linux-x64.tar.gz` می‌سازد: runtime جاسازی‌شدهٔ Python 3.12.8 (embeddable ویندوز / python-build-standalone لینوکس)، پکیج backend، SPA بیلدشده در `web/` و لانچرهای `start.bat`/`start.sh` که `python -m app.portable` را روی **پورت ۸۰۸۹** اجرا می‌کنند. در این حالت (`app/portable.py`، مستند در سرفایل): پایگاه‌داده SQLite فایلی در `data/club360.db`، صف به‌صورت inline و اسکیما با create_all — PostgreSQL همچنان مرجع رسمی عملیات است و این حالت برای اجرای سریع/پایلوت کوچک است؛ فایل `.env` کنار لانچر (شامل `CLUB360_PORT=8089`، `CORS_ORIGINS`، `SSO_*`) پیکربندی را می‌دهد و دسترسی شبکه با بازکردن TCP 8089 در فایروال امکان‌پذیر است. درس‌های انتشار واقعی در Release Notes ثبت شده: v1.1.1 و v1.3.1 هر دو هات‌فیکس بستهٔ ویندوز بودند (ModuleNotFoundError ناشی از isolated mode پایتون جاسازی‌شده با جابه‌جایی app/ کنار runtime و ست‌کردن `CLUB360_BASE`؛ و شبیه‌سازی نبود tzdata ویندوز که seed را برای قرنطینهٔ رویداد بدون crash سازگار کرد). حالت پرچم‌های شفافیت: `ENABLE_SIMULATORS=false` Simulatorها را از Runtime حذف و `REQUIRE_POLICY_SIGNOFF` بهره‌برداری واقعی را تا signoff سیاست قفل می‌کند.

| نسخه | محتوای تحویل‌شده | آزمون |
| --- | --- | --- |
| v1.0 (MVP) | هستهٔ امتیاز/سیاست/دفترکل/پاداش + frontend + Docker | ۲۸/۲۸ روی PG |
| v1.1.0 | SSO/OIDC با سامانهٔ مرکزی، بستهٔ قابل‌حمل، مایگریشن external_identities | ۳۶/۳۶ + بوت واقعی بستهٔ لینوکس |
| v1.1.1 | هات‌فیکس اجرای بستهٔ ویندوز | راستی‌آزمایی ساختاری |
| v1.2.0 | صفحهٔ `/admin/sso`، مایگریشن sso_system_settings، بازطراحی aurora/glass | ۴۰/۴۰ + دودتست Chromium |
| v1.3.0 / v1.3.1 | تجربهٔ باشگاه (onboarding/دعوت/showcase)، هات‌فیکس tzdata ویندوز | ۴۸/۴۸ + دودتست مرورگر |
| v1.4 (کد فعلی frontend) | پالت شاد، حلقهٔ پیشرفت، جشن، دارک‌مود | بدون Release Notes مستقل |

**آنچه صریحاً آزمون نشده** (بخش «صداقت تحویل» README و TEST_RESULTS): E2E مرورگر (Playwright) و ممیزی axe — بررسی بصری با مرورگر headless انجام شده؛ Load test و اعلام p95 — نیازمند بار توافق‌شده؛ آزمون واقعی Backup/Restore — اسکریپت و سیاست در `docs/11` (pg_dump روزانه + WAL، نگهداری ۳۰ روز رمزی‌شده) آماده است؛ و Celery روی Redis واقعی — منطق Task با InlineRunner آزموده شده و `docker compose up worker beat` در محیط دارای Redis باقی است. اتصال OIDC/LMS واقعی نیز هنوز در حالت simulator است.

**مراحل ۲ و ۳** (طبق `docs/10`) در Backlog قابل‌ردیابی‌اند و با endpoint تکمیل‌شده نمایش داده نمی‌شوند: مرحلهٔ ۲ شامل مأموریت پیشرفتهٔ فردی/گروهی، اتصال مهارت و مشاوره، ارائه‌دهندگان بیشتر، گزارش انصاف/اثربخشی کامل و توصیه‌گر داده‌محور در صورت کفایت داده؛ مرحلهٔ ۳ شامل کشف ناهنجاری پیشرفته (ML + پایش Drift)، شبیه‌سازی پیشرفته، پایش مدل، آزمایش برنامهٔ انگیزشی مصوب و مزایای صنعت. اقلام Backlog با کد BL-01 تا BL-09 ثبت‌اند: BL-01 تخصیص شفاف queue/lottery برای پاداش کمیاب، BL-02 توصیه‌گر داده‌محور (Provider Interface آماده)، BL-03 رتبه‌بندی عمومی اختیاری مشروط به تصویب سیاست، BL-04 کشف ناهنجاری ML، BL-05 اتصال OIDC واقعی و MFA اجباری، BL-06 اتصال LMS واقعی، BL-07 Load test رسمی و SLO، BL-08 داشبورد APM/Trace، و BL-09 MinIO در Compose تولیدی با آزمون Restore خودکار. شرط عبور از پایلوت (`docs/15`): صحت دفترکل و تحویل‌پذیری و کنترل دسترسی آزموده‌شده‌اند؛ «نبود آسیب آموزشی/تبعیض» نیازمند مشاهدهٔ میدانی است و شروع بهره‌برداری واقعی مشروط به پاسخ کارفرما به پرسش‌های Q1..Q4، استقرار با TLS/MFA و `ENABLE_SIMULATORS=false`، اجرای Playwright/axe و Load test در CI واقعی، و آزمون Backup/Restore با ثبت RPO/RTO مصوب است.



## فصل ۱۳ — وعده‌های چهارگانهٔ «زندگی دانشجویی» و پایلوت v1.5

ارزیابی مستند v1.4 یک پیام روشن داشت: باشگاه هنوز بیشتر «سامانه» است تا «زندگی دانشجویی». در پاسخ، هویت محصول از «امتیاز، نشان و سطح» به چهار وعدهٔ ملموس تغییر کرد — **آدم‌های من** (آدم‌های هم‌علاقه‌ام را پیدا می‌کنم)، **تجربه‌های من** (دانشگاه را جذاب‌تر و متنوع‌تر تجربه می‌کنم)، **آیندهٔ من** (مهارت، نمونه‌کار و فرصت واقعی می‌سازم) و **اثر من** (ایده‌ام شنیده می‌شود و می‌توانم چیزی را تغییر بدهم). اصل بنیادین این نوبت، «ارزش فوری بدون امتیاز» است: دفترکل امتیاز، سقف‌ها و پاداش‌ها همه باقی مانده‌اند اما به‌عنوان زیرساخت پشتیبان، نه مرکز تجربهٔ کاربر؛ هیچ‌یک از جداول تازهٔ این نسخه حتی یک کلید خارجی به جداول امتیاز ندارند و آزمون صریح `test_bundle_no_points_involved` این استقلال را قفل می‌کند.

### ماژول student_life و جداول چهار وعده

هجدهمین ماژول دامنه، `app/modules/student_life` (مدل‌ها/سرویس/روتر + مایگریشن `e5f6a7b8c9d0` با ۹ جدول تازه)، پیاده‌سازی پایلوت سه‌مسیرهٔ ارزیابی است (§۷: تعلق، تجربه، آینده):

| وعده | جداول | نقطه‌های پایانی (زیر `/api/v1/student-life`) | قواعد کلیدی |
| --- | --- | --- | --- |
| آدم‌های من — «هم‌پایه پیدا کن» | `peer_activities`, `peer_participants`, `peer_reports` | `GET/POST /peer-up`، `POST /peer-up/{id}/join`، `/leave`، `/report`، `GET /peer-up/mine`، مدیریتی: `GET /peer-reports`، `POST /peer-reports/{id}/resolve` | جمع کوچک ۲ تا ۸ نفر در محل عمومی دانشگاه؛ تطبیق فقط با علاقه/زمان اعلام‌شده و بدون هیچ برچسب شخصیتی؛ شرکت آزمایشی (`mode=trial`) بدون تعهد؛ خروج امن بدون جریمه؛ حداکثر ۳ جمع باز برای هر میزبان؛ پیام خصوصی درون‌سیستمی وجود ندارد و گزارش مزاحمت فقط برای مدیر باشگاه (مجوز `missions:manage`) نمایش داده می‌شود |
| تجربه‌های من — «امروز در دانشگاه چه خبر؟» | `opportunities`, `opportunity_regs` | `GET /week?free=&solo=&short=`، `POST /week/{id}/register`، `/cancel`، `GET /week/mine` | هر کارت فقط اطلاعات تصمیم‌گیری دارد: چه/کجا/کی/هزینه/پیش‌نیاز؛ فیلتر «بین دو کلاس» یعنی ≤۹۰ دقیقه؛ پُر شدن ظرفیت یعنی **صف انتظار شفاف** (`position_no`) و لغوِ هر نفر، سرِ صف را ارتقا می‌دهد — نه «زودتر کلیک‌کردن» و نه «امتیاز بیشتر» (نخستین گام عملی BL-01) |
| آیندهٔ من — «از صفر تا نمایش‌دادنی» | `portfolio_bundles`, `bundle_enrollments` | `GET /bundles`، `POST /bundles/{id}/enroll`، `/steps`، `/output`، `GET /bundles/mine`، مدیریتی: `POST /bundle-enrollments/{id}/verify` | هر بسته شامل ابزار لازم + راهنما/همراه + بازخورد واقعی + خروجی قابل‌نمایش است؛ مراحل رفت‌وبرگشتی در `steps_done_json` ثبت می‌شوند؛ بخشی از ظرفیت به‌عنوان **صندلی محفوظ تازه‌وارد** (`newcomer_seats`) فقط برای دانشجو با `cumulative_progress < 50` (زیر سطح «پویا») قابل گرفتن است (۴۰۳ برای پیشرفته‌ها)؛ تأیید راهنما/مدیر وضعیت را به `completed` و `output_verified` می‌برد |
| اثر من — «صدای دانشجو» | `student_proposals`, `proposal_votes` | `GET /voice`، `POST /voice`، `POST /voice/{id}/vote`، مدیریتی: `POST /voice/{id}/decision` | پیشنهادِ برنامه/فضا/بهبود با «حمایتِ لازم» ثبت می‌شود؛ **رأی همه برابر است** (قید یکتا `uq_proposal_vote`؛ امتیاز بالاتر صدا را قوی‌تر نمی‌کند) و مسیر وضعیت فقط در مسیر مصوب دریافت←بررسی←پذیرش/رد←اجرا جلو می‌رود (۴۲۲ برای گذار خارج از مسیر) |

### خانهٔ نو و انحراف آگاهانه از توسعهٔ بیشتر

فرانت‌اند چهار صفحهٔ تازه (`Peers`, `Week`, `Bundles`, `Voice`) و خانهٔ بازطراحی‌شده دارد: به‌جای شروع با کارت امتیاز، پرسش «امروز دوست داری چه کار کنی؟» با چهار کاشی وعده می‌آید، سپس «سه پیشنهاد مناسب همین هفته» از endpoint ترکیبی `GET /student-life/home` و «فعالیتی که شروع کرده‌ای» از مشارکت‌های واقعی ساخته می‌شود؛ امتیاز/نشان/دفترکل به بخش انتهایی «پیشرفت و مزایا» منتقل شده‌اند و لحن پیام‌ها خبرِ فرصت است («هنوز ظرفیت هست»)، نه احساس عقب‌ماندن. مطابق §۶ ارزیابی، رتبه‌بندی عمومی، توصیه‌گر ML، چت‌بات عمومی و فید اجتماعی بی‌پایان عمداً ساخته نشده‌اند؛ «منوی تجربه»، «استودیوی درآمدزا»، «منتورینگ با درخواست مشخص» و «گذرنامهٔ تجربه» در نقشهٔ گام بعدی‌اند — با این قاعدهٔ قطعی که دستمزد هرگز به امتیاز باشگاه تبدیل نمی‌شود. معیار موفقیت پایلوت نیز شمارش ورود نیست: چند نفر اولین تجربهٔ واقعی را تکمیل کردند، چند نفر بدون پاداش اضافی برگشتند، چند ارتباط/نمونه‌کار قابل‌استفاده ساخته شد و تازه‌واردها واقعاً دسترسی داشتند. راستی‌آزمایی این نوبت: ۱۵ آزمون تازه در `tests/test_student_life.py` (مجموع ۶۳/۶۳ روی PostgreSQL واقعی)، دودتست زندهٔ هر پنج endpoint با حساب دانشجو و سبز بودن کامل ساخت و آزمون فرانت‌اند.
