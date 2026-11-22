# نتایج واقعی اجرای آزمون‌ها (TEST RESULTS)

محیط اجرا: PostgreSQL 16.2 واقعی (باینری رسمی، ساکت یونیکس) — بدون SQLite (SEC-15)
فرمان اجرا: `cd backend && pytest -q`
آخرین اجرا: 2026-11-22 — نتیجه: **۴۸/۴۸ پاس** (v1.3)

## اجرای v1.3.0 (2026-11-22) — تجربهٔ باشگاه (شروع فوری، دعوت دوست، فضای دستاوردها)

- **۴۸/۴۸ پاس**: ۴۰ آزمون قبلی + ۸ آزمون جدید `test_club_experience.py`:
  - پیشنهاد مأموریت اول در وضعیت onboarding (اولویت رویداد آغازین) و شکل کامل personas/interests؛
  - صدور یک‌بارهٔ نشان «اولین قدم» + upsert پروفایل + فیلتر علاقه‌های نامعتبر؛
  - **صفر سند امتیازی** از onboarding و دعوت (امتیاز فقط از سیاست‌های مصوب)؛
  - دعوت فقط برای عضو مأموریت (۴۰۹ بدون عضویت)، کد یک‌بارمصرف (۴۰۹ در پذیرش دوم)، ممنوعیت پذیرش دعوت خود (۴۰۹)، ممنوعیت غیردانشجو (۴۰۳)؛
  - دروازهٔ رضایت فضای دستاوردها (روایت بدون رضایت نمایش داده نمی‌شود) و نبود هر فیلد رتبه/امتیاز در خروجی؛
  - فیلدهای تجربه‌محور در فهرست مأموریت‌ها (mission_kind/kind_label_fa/output_fa/duration) و گروه‌های علاقه‌ای (interest_tag/goal_fa/expected_output/duration).
- مایگریشن `d4e5f6a7b8c9` روی dev اجرا و schema test با همان ستون‌ها هم‌تراز و stamp شد.
- seed بازپذیر شد (گارد درخواست پاداش با `_request_once`) تا اجرای دوم crash نکند.
- دودتست مرورگر واقعی (Chromium) با حساب دانشجو: جادوی شروع ۳مرحله‌ای تا نشان «اولین قدم»، کارت رویداد آغازین، فیلتر مأموریت‌ها، ساخت دعوت با کد قابل‌کپی، فضای دستاوردها و فیلتر پاداش‌های تجربه‌ساز — همه رندر و کار کردند (گزارش تصویری در بستهٔ تحویل). در همین تست رگرسیون مودال‌ها (transform والد → fixed زیر صفحه) کشف و با portal اصلاح شد.

## اجرای v1.2.0 (2026-11-17) — تنظیمات ورود یکپارچه (ثبت سامانه در پورتال)

- **۴۰/۴۰ پاس** (`pytest -q` روی PostgreSQL واقعی): ۲۸ آزمون پایه + ۱۲ آزمون `test_sso.py` که ۴ آزمون جدید آن پوشش تنظیمات ثبت سامانه است: پیش‌فرض‌های هم‌سان با پورتال مرکزی (کلید `daneshjooclub`، Client ID `daneshjooclub360`، آیکن 🥇، ترتیب ۱۴، فعال)، گردش خواندن/به‌روزرسانی توسط مدیر باشگاه + ثبت آدیت، ممنوعیت دسترسی دانشجو/ناشناس (401/403) و اعتبارسنجی آدرس ورود (422 ساختاریافته).
- مایگریشن `c3d4e5f6a7b8` (جدول تک‌ردیفی `sso_system_settings` + ردیف پیش‌فرض) روی dev/test اجرا و تأیید شد.
- دودتست مرورگر واقعی (Chromium): صفحهٔ ورود، ورود محلی مدیر، رندر صفحهٔ `/admin/sso` با مقادیر پیش‌فرض پورتال و داشبورد — همه به‌درستی نمایش داده شد (گزارش تصویری در بستهٔ تحویل).

## اجرای v1.1.0 (2026-11-15) — SSO و اصلاح آزمون تاریخ‌دار

- **۳۶/۳۶ پاس**: ۲۸ آزمون قبلی + ۸ آزمون جدید `test_sso.py` (امضای state، شروع ورود یکپارچه، تأمین کاربر، پیوند حساب بدون رمز، عدم تصاحب حساب رمزدار، عدم ارتقای نقش از توکن، ورود مجدد همان هویت، status).
- اصلاح آزمون‌های تاریخ‌دار: `test_event_ingest_contract` زمان‌های رویداد را نسبی به اکنون می‌سازد (تاریخ مطلق قدیمی در پنجرهٔ ۷۲ ساعت رویداد دیررس می‌افتاد — خطای آزمون، نه خطای سیستم).
- آزمون بوت واقعی بستهٔ قابل‌حمل لینوکس: healthz، SPA در /، SSO status، ورود محلی — همه سبز.
- راستی‌آزمایی ساختاری بستهٔ ویندوز + بسته‌بودن importها در runtime جاسازی‌شده.

## نگاشت سناریوهای الزامی سند کارفرما → نتیجه

| سناریو | آزمون | نتیجه |
| --- | --- | --- |
| ۱ ارسال چندباره رویداد = یک اثر | `test_events_and_policy.py::test_duplicate_event_single_effect` | پاس |
| ۲ رویداد خارج از ترتیب طبق زمان/نسخهٔ سیاست | `test_events_and_policy.py::test_out_of_order_policy_selection` | پاس |
| ۳ دو درخواست آخرین ظرفیت = یک رزرو | `test_ledger_concurrency.py::test_capacity_race_single_winner` | پاس (ThreadPool روی PG واقعی) |
| ۴ درخواست هم‌زمان چند دستگاه = مضاعف نشدن | `test_ledger_concurrency.py::test_concurrent_spend_never_negative` | پاس (۸ رشته هم‌زمان؛ ۲ موفق، ۶ رد) |
| ۵ Retry Worker بدون اثر مضاعف | `test_ledger_invariants.py::test_worker_retry_no_double_effect` | پاس |
| ۶ اصلاح با سند جبرانی قابل پیگیری | `test_ledger_invariants.py::test_correction_compensation_traceable` | پاس |
| ۷ تغییر سیاست گذشته را بازنویسی نکند | `test_events_and_policy.py::test_policy_version_freezes_past` | پاس |
| ۸ مصرف پاداش پیشرفت را کم نکند | `test_ledger_invariants.py::test_spend_keeps_progress` | پاس |
| ۹ تحویل نامعلوم با Reconciliation | `test_rewards_flow.py::test_unknown_delivery_reconciliation` | پاس (بدون استرداد خودکار) |
| ۱۰ خروج خدمات پایه را محدود نکند | `test_domain_rules.py::test_exit_keeps_base_services` | پاس |
| ۱۱ رد شخصی‌سازی، کاتالوگ کار کند | `test_domain_rules.py::test_no_consent_generic_recommendations` | پاس |
| ۱۲ هشدار ناهنجاری رأی خودکار نسازد | `test_domain_rules.py::test_signal_no_auto_penalty` | پاس |
| ۱۳ اعتراض پذیرفته‌شده اصلاح کند | `test_domain_rules.py::test_accepted_appeal_corrects_ledger_tiers` | پاس (سند جبرانی + سطح) |
| ۱۴ قطع LMS بدون جریمه | `test_events_and_policy.py::test_lms_outage_no_penalty` | پاس |
| ۱۵ نشان بدون رضایت منتشر نشود | `test_domain_rules.py::test_public_share_requires_consent` | پاس |
| ۱۶ ارائه‌دهنده دادهٔ اضافی نبیند | `test_domain_rules.py::test_provider_scope_minimal_fields` + روتر `/providers/queue` (فیلد-کمینه) | پاس |
| ۱۷ مدیر فنی بدون Scope نبیند | `test_domain_rules.py::test_tech_admin_no_educational_data` + `test_points_summary_rbac` | پاس |
| ۱۸ عضویت/دفترکل/پاداش با صفحه‌کلید و صفحه‌خوان | Playwright + axe | **اجرا نشده** — سندباکس امکان نصب مرورگر Playwright را ندارد؛ پیاده‌سازی a11y انجام شد (Skip Link، Radix با ARIA، focus-visible، هدف لمس ≥44px) و ممیزی ابزاری به استقرار واقعی موکول شد |
| ۱۹ سقف در پردازش موازی | `test_ledger_concurrency.py::test_cap_parallel_respected` | پاس (۶ رشته هم‌زمان؛ Σ ≤ سقف روزانه) |
| ۲۰ رزرو منقضی آزاد شود | `test_rewards_flow.py::test_expired_reservation_release` | پاس |

## سایر آزمون‌های اجراشده

| آزمون | پوشش | نتیجه |
| --- | --- | --- |
| `test_api_contract.py` (۶ آزمون) | قرارداد HTTP: خطای ساختاریافته، RBAC، جداسازی دانشگاه، Idempotency-Key (تکرار/Conflict)، قرارداد ingest + تکراری | پاس |
| `test_ledger_invariants.py::test_ledger_invariants_property` | Property (hypothesis): توازن هر تراکنش، غیرمنفی بودن مانده‌ها، بازسازی Projection از entries | پاس |
| `test_rewards_flow.py::test_full_happy_path` / `test_state_machine_rejects_invalid_transition` | گردش کامل پاداش و رد گذار غیرمجاز | پاس |
| قیدهای DB | trigger بی‌ردپا (ledger/audit/events)، trigger توازن DEFERRABLE (در اجرای واقعی یک خطای طراحی spend را در سمت credit گرفت و اصلاح شد) | فعال و آزموده |

## صریحاً اجرا نشده (بدون ادعا)

| قلم | دلیل | اقدام لازم |
| --- | --- | --- |
| E2E مرورگر (Playwright) و ممیزی axe | سندباکس بدون Chromium | اجرا در CI/استقرار واقعی |
| Load test (p95 اهداف بخش ۱۹) | نیازمند بار توافق‌شده با کارفرما | پس از توافق بار |
| Backup/Restore واقعی | نیازمند زیرساخت Prod | اسکریپت‌ها ارائه شده؛ آزمون بازیابی در استقرار |
| Celery روی Redis واقعی | سندباکس بدون Redis | `docker compose up worker beat` در محیط دارای Redis؛ منطق Task همان است و با InlineRunner آزموده شد |
