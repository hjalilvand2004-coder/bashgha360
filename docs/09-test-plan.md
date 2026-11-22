# ۰۹ — برنامهٔ آزمون (Test Plan) و نگاشت ۲۰ سناریوی الزامی

نسخهٔ 1.0. اجرا: `cd backend && pytest -q` روی **PostgreSQL 16 واقعی** (بدون SQLite — SEC-15).

## ۱. لایه‌ها

| لایه | ابزار | دامنه |
| --- | --- | --- |
| Unit | pytest | ارزیاب DSL، گردکردن Decimal، قواعد ریسک، ماشین‌های حالت |
| Integration | pytest + PG واقعی | همهٔ سرویس‌ها با DB؛ seed |
| Contract | pytest + httpx | قرارداد رویداد و خطاها |
| Concurrency | pytest + ThreadPool روی PG | رزرو ظرفیت، سقف، مصرف هم‌زمان |
| Property | hypothesis | ناوردایی دفترکل و ماشین حالت |
| E2E (UI) | Playwright | سناریوهای مسیر طلایی — **اجرا نشده در سندباکس** |
| Accessibility | axe/ناوبری دستی | TST-18 — **اجرا نشده ابزاری** |
| Load | k6/locust | p95 اهداف — **اجرا نشده (نیازمند بار توافق‌شده)** |
| Backup/Restore | اسکریپت + آزمون بازیابی | **اجرا نشده** |
| Security | Bandit/grep + بررسی دستی | CI |

## ۲. نگاشت سناریوهای الزامی → آزمون → نتیجه (پس از اجرا در TEST_RESULTS.md)

| سناریو | فایل آزمون | معیار پذیرش |
| --- | --- | --- |
| ۱ ارسال چندباره رویداد = یک اثر | test_events_and_policy.py::test_duplicate_event_single_effect | duplicate=true، یک LedgerTransaction |
| ۲ رویداد خارج از ترتیب طبق زمان/نسخهٔ سیاست | test_events_and_policy.py::test_out_of_order_policy_selection | انتخاب نسخه براساس occurred_at |
| ۳ دو درخواست آخرین ظرفیت = یک رزرو | test_rewards_concurrency.py::test_capacity_race | یک delivered/reserved، بقیه CAPACITY_EXHAUSTED |
| ۴ درخواست هم‌زمان چند دستگاه = مضاعف نشدن خرج | test_ledger_concurrency.py::test_concurrent_spend | available≥0 و Σ خروجی ≤ مانده |
| ۵ Retry Worker بدون اثر مضاعف | test_worker_idempotency.py::test_worker_retry | تعداد tx ثابت |
| ۶ اصلاح با سند جبرانی قابل پیگیری | test_ledger_corrections.py::test_correction_link | correction_of مرئی و مانده سازگار |
| ۷ تغییر سیاست بازنویسی گذشته نکند | test_events_and_policy.py::test_policy_version_freezes_past | txهای قدیمی با نسخهٔ قبلی |
| ۸ مصرف پاداش پیشرفت تجمعی را کم نکند | test_ledger_invariants.py::test_spend_keeps_progress | progress ثابت پس از spend |
| ۹ تحویل نامعلوم با Reconciliation | test_rewards_flow.py::test_unknown_delivery_reconciliation | بدون استرداد خودکار؛ تصمیم انسانی |
| ۱۰ خروج خدمات پایه را محدود نکند | test_membership_exit.py::test_exit_keeps_services | APIهای پایه پاسخ می‌دهند |
| ۱۱ رد شخصی‌سازی کاتالوگ را نیندازد | test_recommendations.py::test_no_consent_generic | پیشنهاد عمومی + reasons |
| ۱۲ هشدار ناهنجاری رأی خودکار نسازد | test_integrity.py::test_signal_no_auto_penalty | Case باز، تراکنش‌ها دست‌نخورده |
| ۱۳ اعتراض پذیرفته‌شده دفترکل/سطح/نشان را اصلاح کند | test_appeals.py::test_accepted_appeal_corrects | سند جبرانی + بازمحاسبهٔ سطح/نشان |
| ۱۴ قطع LMS بدون جریمه | test_events_and_policy.py::test_lms_outage_no_penalty | بدون کاهش/پرچم |
| ۱۵ نشان بدون رضایت منتشر نشود | test_badges.py::test_public_share_requires_consent | share رد شود |
| ۱۶ ارائه‌دهنده دادهٔ اضافی نبیند | test_rbac.py::test_provider_scope | پاسخ فیلد-کمینه |
| ۱۷ مدیر فنی بدون Scope نبیند | test_rbac.py::test_tech_admin_no_data | 403 روی دادهٔ آموزشی |
| ۱۸ عضویت/دفترکل/پاداش با صفحه‌کلید و صفحه‌خوان | Playwright + axe | **اجرا نشده** |
| ۱۹ سقف در پردازش موازی رعایت شود | test_policy_concurrency.py::test_cap_parallel | Σ امتیاز ≤ سقف |
| ۲۰ رزرو منقضی ظرفیت/امتیاز را آزاد کند | test_rewards_flow.py::test_expired_reservation_release | sweeper آزاد می‌کند |

## ۳. ناوردایی‌های Property (hypothesis)

- هر دنبالهٔ عملیات award/reserve/spend/release/expire/adjust ⇒ Σ(debit)=Σ(credit) per tx؛ available≥0؛ بازسازی Projection از entries.
- هر گذار غیرمجاز ماشین‌حالت ⇒ رد و بدون تغییر state.

## ۴. فرمان‌ها

```bash
cd backend && pytest -q                    # همهٔ آزمون‌ها (PG واقعی)
pytest -q tests/test_ledger_concurrency.py # فقط هم‌زمانی
cd ../frontend && npm run test             # Vitest
npm run e2e                                # Playwright (اجرا نشده در سندباکس)
```
