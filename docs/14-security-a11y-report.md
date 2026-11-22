# ۱۴ — گزارش امنیت و دسترس‌پذیری

## ۱. امنیت — وضعیت واقعی

| قلم | وضعیت | شواهد |
| --- | --- | --- |
| JWT کوتاه‌عمر + Refresh در Cookie HttpOnly/SameSite | انجام | `app/modules/identity_access/router.py`؛ بدون ذخیرهٔ توکن در localStorage (frontend/src/lib/api.ts) |
| RBAC + مالکیت + Scope دانشگاه سمت سرور | انجام | `core/rbac.py` + آزمون TST-16/17 |
| IDOR: فیلتر university_id در کوئری‌ها | انجام | آزمون جداسازی دانشگاه (test_university_isolation) |
| امضای HMAC رویداد/Callback | انجام | `event_ingestion/service.py`, `providers callback` |
| Idempotency + Conflict | انجام | `shared/idempotency.py` + آزمون API |
| Rate limit + Origin-check CSRF | انجام | middleware در `main.py` (Prod: Redis-based) |
| Triggers بی‌ردپا (ledger/audit/events) | انجام | Migration `a1b2c3d4e5f6` — در اجرای واقعی خطای طراحی spend را گرفت |
| قید توازن دفترکل در COMMIT | انجام | همان Migration (constraint trigger deferrable) |
| Masking لاگ‌ها | انجام | `core/logging.py` (ایمیل/توکن/کد ملی/…) |
| بدون eval/SQL دلخواه در DSL | انجام | ارزیاب allowlist + گارد CI |
| Security headers + CSP | انجام | nginx.conf |
| Bandit / secret scanning | انجام در CI | `.github/workflows/ci.yml` |
| Threat Model | مستند | docs/08 |

**کاستی‌های شفاف:** pen-test بیرونی نشده؛ ممیزی وابستگی کامل در CI اجرا می‌شود نه اینجا؛ MFA کد آماده دارد اما بدون تأیید کارفرما (Q1) فعال نیست.

## ۲. دسترس‌پذیری (هدف WCAG 2.2 AA)

| قلم | وضعیت |
| --- | --- |
| Semantic HTML + Landmark | انجام (header/nav/main/aside/footer) |
| Skip Link | انجام (AppShell) |
| ناوبری کامل صفحه‌کلید + focus-visible | انجام |
| فرم‌ها: label مرتبط + aria-invalid + پیام نقش alert | انجام |
| Dialog: aria-modal + Esc (بستن با کلیک/دکمه) | انجام (نسخهٔ دست‌ساز) |
| جدول‌ها: caption + th scope | انجام |
| نمودارها: خلاصهٔ متنی sr-only + جدول جایگزین details | انجام |
| هدف لمس ≥44px | انجام (min-h-11) |
| معنا فقط با رنگ نیست | انجام (Chip آیکون/متن) |
| reduced-motion | انجام (CSS) |
| ممیزی ابزاری axe / صفحه‌خوان | **اجرا نشده** (سندباکس بدون مرورگر full-CI؛ مرورگر headless برای بررسی بصری استفاده شد) |

## ۳. تاریخ‌ها و اعداد
- ذخیره UTC timezone-aware؛ نمایش شمسی `Intl fa-IR-u-ca-persian`؛ API با ISO-8601 — آزمون‌شده در رابط (۲۰ آبان ۱۴۰۵ نمایش صحیح).
