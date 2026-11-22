# ۰۸ — Threat Model (خلاصهٔ STRIDE)

نسخهٔ 1.0 — دامنه: سامانهٔ باشگاه۳۶۰ + درگاه‌های LMS/ارائه‌دهنده. خارج از دامنه: زیرساخت‌های دانشجو۳۶۰ (هویت مرکزی، LMS اصلی).

| # | جریان | تهدید (STRIDE) | سناریو | کنترل پیاده‌شده |
| --- | --- | --- | --- | --- |
| T1 | ingest رویداد | Spoofing منبع | مهاجم رویداد جعلی امتیاز می‌سازد | X-Integration-Key + HMAC امضای بدنه + پنجرهٔ زمانی؛ ذخیرهٔ secret به‌صورت reference (خارج از ریپو)؛ Rate limit per source |
| T2 | ingest | Replay | ارسال دوبارهٔ همان پیام | کلید یکتای مرکب (uni, source, event_id) + EventInbox؛ پاسخ duplicate بدون اثر (TST-01) |
| T3 | ingest | Tampering | تغییر payload در مسیر | HMAC؛ ابطال رویداد فقط با رویداد اصلاحی؛ خام غیرقابل تغییر (trigger) |
| T4 | auth | Spoofing کاربر | حدس رمز، نشست ربایی | bcrypt + Rate limit ورود + قفل تدریجی؛ refresh در Cookie HttpOnly/SameSite؛ بدون توکن بلندمدت در localStorage؛ چرخش refresh |
| T5 | auth | Elevation | نقش‌های حساس | RBAC + Scope؛ MFA flag (ACC-14، مشروط تصویب)؛ break-glass موقت با audit |
| T6 | API | IDOR | دسترسی به منبع دانشگاه/کاربر دیگر | همهٔ Queryها university_id + owner check سمت سرور (TST-16/17) |
| T7 | API | Injection | SQL/DSL | ORM پارامتری؛ DSL بدون eval با allowlist عملگر (CI grep) |
| T8 | API | CSRF | فرمان با Cookie کاربر | SameSite=Lax + چک Origin/Referer + double-submit توکن برای متدهای تغییردهنده |
| T9 | API | XSS | نمایش محتوای کاربر | React escaping؛ بدون dangerouslySetInnerHTML؛ CSP سخت‌گیرانه در Nginx |
| T10 | خروجی‌ها | Information Disclosure | دادهٔ حساس در Log/اعلان/Analytics | masker Log؛ payload اعلان حداقلی؛ k-ناشناسی k=5؛ ارائه‌دهنده فقط فیلدهای ضروری (TST-16) |
| T11 | rewards | DoS/مسابقهٔ ظرفیت | سیل درخواست روی آخرین ظرفیت | Row lock + Rate limit + Idempotency؛ رفتار معین: یک رزرو موفق (TST-03) |
| T12 | rewards | Fraud تحویل | Callback جعلی «delivered» | HMAC callback + شناسهٔ پایدار + عدم تحویل دوباره + Reconciliation برای unknown |
| T13 | ledger | Repudiation/دستکاری | ویرایش سابقهٔ امتیاز | append-only trigger + سند جبرانی + AuditLog + توازن کنترل‌شده در COMMIT |
| T14 | policy | Tampering نسخه | تغییر نسخهٔ منتشرشده | قفل published؛ تأیید دوم؛ requester≠approver؛ AuditLog تغییرات |
| T15 | integrity | سوءاستفاده | تکرار/تبانی/حجم ناسازگار | کنترل‌های قطعی + Rule-based checks فقط Case؛ بدون حکم خودکار (TST-12) |
| T16 | file | SSRF/فایل خطرناک | آپلود مخرب، fetch داخلی | allowlist نوع/حجم؛ ذخیرهٔ خصوصی؛ لینک کوتاه‌عمر؛ SSRF guard روی URL بیرونی |
| T17 | infra | DoS | سیل درخواست | Nginx + Rate limit لایهٔ اپ؛ timeoutها |
| T18 | backup | Data loss | خرابی | Backup روزانه PG + آزمون Restore مستند (اجرا نشده در سندباکس — صریح) |

**اقدامات آیندهٔ ثبت‌شده:** penetration test بیرونی، ممیزی a11y ابزاری، load test با بار توافق‌شده — همه «اجرا نشده» در TEST_RESULTS.
