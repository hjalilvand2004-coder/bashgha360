# ۰۲ — ماتریس ردیابی نیازمندی‌ها (Requirements Traceability Matrix)

نسخهٔ 1.0. همهٔ الزامات سند کارفرما (شامل موارد فاقد شناسه که شناسهٔ پایدار گرفته‌اند) در این ماتریس ثبت شده‌اند. متن شناسه‌های CLUB/EVT/PNT/ACH/RWD/REC از بدنهٔ بخش‌های ۶ تا ۱۲ سند بازسازی شده است.

**راهنمای وضعیت:** «انجام» = پیاده‌سازی و در این تحویل موجود | «بخشی» = هستهٔ انجام شده، ادامه در مرحلهٔ بعد (صریح) | «مرحله ۲/۳» = در Backlog قابل ردیابی، با Endpoint تکمیل‌شده نمایش داده نمی‌شود | «مشروط» = نیازمند تصمیم/تصویب کارفرما (حالت امن فعال) | «اجرا نشده» = کد هست اما اجرا در سندباکس ممکن نبوده.

| شناسه | نیازمندی (چکیده) | ماژول | API | صفحه | آزمون | وضعیت |
| --- | --- | --- | --- | --- | --- | --- |
| **بخش ۱ — اصول غیرقابل نقض** | | | | | | |
| PRN-01 | امتیاز فقط از مشارکت داوطلبانه + پیشرفت آموزشی معتبر | policy_engine | — | — | TST-07 | انجام |
| PRN-02 | کلیک/زمان آنلاین/پیام/پخش به‌تنهایی امتیاز نیست | event_ingestion | — | — | TST-02 | انجام (نوع‌های قراردادی فقط verified/assessed/approved) |
| PRN-03 | تفکیک پیشرفت فردی از عملکرد مطلق (خط پایه معتبر) | points_ledger | /points/summary | داشبورد | TST-08 | انجام (ProgressRecord با baseline_type) |
| PRN-04 | عدم عضویت/خروج خدمات پایه را محدود نکند | memberships | /memberships | /privacy | TST-10 | انجام |
| PRN-05 | امتیاز ≠ نمره/وضعیت تحصیلی/رأی انضباطی | همه | — | — | بررسی کد | انجام |
| PRN-06 | منابع/حمایت ضروری پشت شرط امتیاز نباشند | rewards | /rewards | کاتالوگ | بررسی کد | انجام (Reward.is_essential با قید Validation) |
| PRN-07 | تصمیم احتمالی مدل، حکم تخلف نیست | integrity_reviews | /reviews | /cases | TST-12 | انجام |
| PRN-08 | قواعد و دلایل تخصیص/عدم تخصیص/اصلاح قابل مشاهده و اعتراض | policy_engine+ledger | /ledger,/policies | /ledger | TST-06 | انجام (Calculation Trace) |
| PRN-09 | پایش بیرونی/دوربین/چهره خارج از دامنه | — | — | — | — | انجام (خارج از دامنه) |
| PRN-10 | خریدوفروش/پولی‌سازی امتیاز پیاده نشود | rewards | — | — | بررسی کد | انجام |
| PRN-11 | ممنوعیت زنجیرهٔ اجباری، اعلان اضطراب‌زا، رقابت تحقیرکننده، اعتیادآور | همه | — | رابط | — | انجام (رتبه‌بندی عمومی نیست؛ اعلان سقف/سکوت دارد) |
| PRN-12 | بدون معرفی سیاست/اعداد مصوب | seed | — | — | — | انجام (اعداد برچسب Demo) |
| **بخش ۲ — فناوری‌های الزامی** | | | | | | |
| TECH-01 | Python/FastAPI/Pydantic/SQLAlchemy/Alembic/OpenAPI/pytest | backend | /docs | — | همه | انجام |
| TECH-02 | PostgreSQL مرجع صحت؛ Redis فقط cache/صف؛ Redis مرجع مانده/رزرو نیست | core | /system/info | — | TST-03/04/19 | انجام |
| TECH-03 | Celery برای پس‌زمینه/زمان‌بندی | shared/jobs | /jobs | /tech | TST-05 | انجام (Prod: Celery+Beat، Dev بدون Redis: InlineRunner شفاف) |
| TECH-04 | React+TS+Vite+Tailwind+Radix RTL+Router+TanStack Query+RHF+Zod+Recharts+Lucide+Motion | frontend | — | همه | VT | انجام |
| TECH-05 | Vitest+RTL+Playwright | frontend | — | — | VT/Playwright | Vitest: انجام؛ Playwright: اجرا نشده (سندباکس) |
| TECH-06 | S3-suggest/MinIO توسعه، Docker/Compose، Nginx، .env.example، Health/Ready، CI | استقرار | /healthz,/readyz | — | — | Docker/Compose/Nginx/CI: انجام (ساخت) — اجرای Compose در سندباکس: اجرا نشده |
| TECH-07 | نسخه‌های پایدار قفل‌شده | pyproject/package.json | — | — | — | انجام |
| TECH-08 | pgvector فقط در صورت نیاز | — | — | — | — | نصب نشده (مستند) |
| **بخش ۳ — معماری** | | | | | | |
| ARC-01 | Modular Monolith با ۱۶ ماژول و مرز روشن؛ بدون ریزخدمت‌سازی | backend | — | — | — | انجام |
| ARC-02 | منطق در Service/Domain نه Endpoint/Component | backend | — | — | — | انجام |
| ARC-03 | Unit of Work و مرز تراکنش برای حساس‌ها | shared/uow | — | — | TST-03/04/19 | انجام |
| ARC-04 | Transactional Outbox + at-least-once + اثر exactly-once با Inbox/یکتا/Idempotency؛ بدون ادعای شبکه‌ای | shared/outbox | — | — | TST-01/05 | انجام |
| ARC-05 | اجزای دانشجو۳۶۰ دوباره ساخته نشوند؛ Adapter + سرویس آزمایشی مجزا | integrations | /system/info | — | — | انجام |
| **بخش ۴ — طراحی گرافیکی و UX** | | | | | | |
| UX-01 | سبک دانشگاهی مدرن؛ توکن‌ها؛ کنتراست آزموده | frontend | — | همه | A11y | انجام (توکن‌ها + جدول کنتراست در گزارش) |
| UX-02 | Vazirmatn محلی، RTL کامل، ترکیب fa/latn | frontend | — | همه | — | انجام (@fontsource/vazirmatn باندل محلی) |
| UX-03 | حالت روشن/تاریک با کنتراست | frontend | — | همه | — | انجام |
| UX-04 | واکنش‌گرا موبایل تا دسکتاپ | frontend | — | همه | — | انجام (Tailwind breakpoints) |
| UX-05 | کارت عضویت، PointsDualCard، مسیر سطح، نشان SVG، کارت پاداش، Timeline، نقشهٔ مأموریت، EmptyState فارسی، Skeleton/ErrorState/اتصال | frontend | — | صفحات | — | انجام |
| UX-06 | نشان/تصویرسازی اصل، آفلاین، مجوز مشخص | frontend | — | — | — | انجام (SVG درون‌ریپو) |
| UX-07 | انیمیشن محدود، reduced-motion، بدون افکت فشارآور | frontend | — | — | — | انجام |
| UX-08 | WCAG 2.2 AA، صفحه‌کلید، Skip Link، Dialog/فرم/جدول صفحه‌خوان‌پذیر، خلاصهٔ متنی نمودار، لمس ≥44px، مسیر کم‌مصرف | frontend | — | همه | TST-18 | بخشی (پیاده‌سازی انجام؛ ممیزی ابزاری کامل: اجرا نشده) |
| UX-09 | UTC+tz-aware ذخیره، نمایش منطقهٔ دانشگاه، تقویم شمسی، ISO-8601، مرز روز/ترم/انقضا | core | — | همه | — | انجام |
| UX-10 | ابتدا Design System/Sitemap/Wireframe/High-fidelity سپس پیاده‌سازی؛ دکمه‌ها واقعی | docs+frontend | — | — | — | انجام (این سند + رابط) |
| **بخش ۵ — کاربران و دسترسی** | | | | | | |
| ACC-01 | ۱۰ نقش تعریف‌شده | identity_access | /auth | — | TST-16/17 | انجام |
| ACC-02 | RBAC + مالکیت + Scope دانشگاه سمت سرور | identity_access | همه | — | TST-16/17 | انجام (UserRoleScope) |
| ACC-03 | دانشجو فقط دادهٔ خود | همه | — | — | TST-16 | انجام |
| ACC-04 | استاد فقط حوزهٔ مجاز خود | memberships | /approvals | /approvals | — | انجام (approval_scope) |
| ACC-05 | مشاور فقط تخصیص‌یافته‌ها و دادهٔ مجاز | student_goals | /advisees | /advisees | — | انجام |
| ACC-06 | ارائه‌دهنده فقط اطلاعات ضروری درخواست‌های خود | rewards | /provider | /provider | TST-16 | انجام |
| ACC-07 | استقلال کارشناس اولیه و مرجع اعتراض | appeals | /cases | /cases | TST-13 | انجام (قید نقش) |
| ACC-08 | مدیر فنی پیش‌فرض به دادهٔ آموزشی دسترسی ندارد | identity_access | — | /tech | TST-17 | انجام |
| ACC-09 | انتشار سیاست حساس/تعدیل عمده/محدودیت حساس = تأیید دوم | policy_engine | /policy-approvals | /policy-approvals | — | انجام |
| ACC-10 | درخواست‌کننده حساس را خودش تأیید نکند | policy_engine | — | — | — | انجام (قید requester≠approver) |
| ACC-11 | جداسازی بین دانشگاه با university_id | core | همه | — | SEED-01 | انجام |
| ACC-12 | دسترسی اضطراری موقت/مستند/قابل حسابرسی | identity_access | /auth/break-glass | — | — | انجام (TTL + AuditLog اجباری) |
| ACC-13 | OIDC/OAuth2 به هویت دانشجو۳۶۰؛ ورود محلی فقط توسعه/مستقل مصوب | integrations | /auth | /login | — | مشروط (Adapter آماده، mode=simulator) |
| ACC-14 | MFA نقش‌های حساس در عملیات | identity_access | — | — | — | مشروط (پرچم تنظیم؛ نیازمند تصویب Q1) |
| ACC-15 | نشست امن؛ بدون توکن بلندمدت در localStorage؛ Cookie با HttpOnly/Secure/SameSite + CSRF | core+frontend | /auth/refresh | — | — | انجام |
| **بخش ۶ — عضویت، رضایت، ترجیحات (CLUB)** | | | | | | |
| CLUB-01 | نمایش شرایط/سیاست داده پیش از عضویت و ثبت نسخهٔ پذیرفته‌شده | memberships | /memberships/join, /consents | /join | — | انجام (TermsVersion + ConsentRecord) |
| CLUB-02 | رضایت‌های جداگانه: شخصی‌سازی، نمایش عمومی نشان، اعلان | memberships | /consents | /join,/privacy | TST-15 | انجام |
| CLUB-03 | انتخاب هدف مجاز (رفع ضعف/امتحان/مهارت/همکاری/…) | student_goals | /goals | /goals | — | انجام |
| CLUB-04 | توقف شخصی‌سازی — واقعی و فوری | memberships | /consents | /privacy | TST-11 | انجام |
| CLUB-05 | ترک مأموریت بدون تنبیه | missions_groups | /missions | /missions | — | انجام |
| CLUB-06 | خروج از باشگاه + مرخصی/انتقال/تغییر رشته/فارغ‌التحصیلی طبق سیاست | memberships | /memberships | /privacy | TST-10 | انجام |
| CLUB-07 | نمایش منشأ داده، زمان به‌روزرسانی، مسیر اصلاح + دانلود اطلاعات شخصی مجاز | memberships+audit | /memberships/export | /privacy | — | انجام (DataCorrectionRequest + JSON export) |
| **بخش ۷ — دریافت رویداد (EVT)** | | | | | | |
| EVT-01 | قرارداد حداقلی رویداد با ۱۴ فیلد الزامی | event_ingestion | /events/ingest | — | CT | انجام (docs/06) |
| EVT-02 | ۸ نوع رویداد نمونه + مستندسازی نگاشت LMS | event_ingestion | — | — | CT | انجام |
| EVT-03 | اعتبارسنجی Schema/اصالت منبع/Scope/نرخ | event_ingestion | — | — | CT | انجام (HMAC + rate limit) |
| EVT-04 | احراز سرویس و امضای پیام Webhook | event_ingestion | — | — | CT | انجام |
| EVT-05 | کنترل بازپخش/تکراری + کلید یکتای مرکب | event_ingestion | — | — | TST-01 | انجام |
| EVT-06 | خام حداقلی غیرقابل تغییر + اصلاح با رویداد اصلاحی | event_ingestion | /events/{id}/corrections | — | TST-06 | انجام (trigger بی‌ردپا) |
| EVT-07 | سیاست دیررس/خارج از ترتیب/آیندهٔ نامعتبر | event_ingestion | — | — | TST-02 | انجام |
| EVT-08 | Quarantine/Dead-letter + Retry با backoff و سقف + مشاهده/بازپردازش | event_ingestion | /events/dead-letter, /jobs | /tech | TST-05 | انجام |
| EVT-09 | خوداظهاری فقط در انتظار شواهد/تأیید انسانی | event_ingestion | /events/self-report | — | — | انجام (وضعیت pending_human) |
| EVT-10 | قطع LMS: کاهش امتیاز/تفسیر تخلف ممنوع | event_ingestion | — | — | TST-14 | انجام |
| EVT-11 | یک قرارداد واقعی + Adapter یک LMS یا Simulator برچسب‌دار + تست قرارداد؛ ادعای اتصال واقعی ممنوع | integrations | — | — | CT | انجام (Simulator برچسب «آزمایشی») |
| **بخش ۸ — موتور سیاست و امتیاز (PNT)** | | | | | | |
| PNT-01 | ساختار کامل PolicyVersion (scope/شرایط/شواهد/پایه/ضرایب/سقف/بازده کاهشی/تکرار/دیررس/وضعیت/تصویب) | policy_engine | /policies | /admin/policies | — | انجام |
| PNT-02 | DSL ساختاریافته JSON با اعتبارسنجی محدود؛ بدون eval/Python/SQL دلخواه | policy_engine | — | — | بررسی کد+CI | انجام |
| PNT-03 | فرمول پایه×کیفیت×پیشرفت×تکرار؛ اعداد فقط Demo | policy_engine | — | — | — | انجام |
| PNT-04 | نوع عدد و گردکردن ثابت و مستند؛ بدون float | core/money | — | — | UT/PT | انجام (Decimal, ROUND_HALF_UP) |
| PNT-05 | Calculation Trace کامل برای هر تصمیم | policy_engine | /ledger/{tx}/trace | /ledger | TST-06 | انجام (RuleEvaluation) |
| PNT-06 | نسخهٔ منتشرشده تغییرناپذیر؛ تغییر = نسخهٔ جدید | policy_engine | — | — | TST-07 | انجام |
| PNT-07 | شبیه‌سازی بدون تغییر دفترکل عملیاتی | policy_engine | /simulations | /admin/simulation | — | انجام |
| PNT-08 | تقدم/گروه انحصاری برای قواعد متعارض | policy_engine | — | — | — | انجام (exclusive_group) |
| PNT-09 | enforce سقف در پردازش هم‌زمان | policy_engine | — | — | TST-19 | انجام (policy_cap_usage + قفل ردیف) |
| PNT-10 | وضعیت‌های draft…retired + مرجع/زمان تصویب | policy_engine | — | — | — | انجام |
| **بخش ۹ — دفترکل (LED)** | | | | | | |
| LED-01 | append-only قابل حسابرسی + تراکنش‌های متوازن | points_ledger | /ledger | /ledger | PT | انجام (trigger بی‌ردپا + قید توازن) |
| LED-02 | تفکیک پیشرفت تجمعی از قابل مصرف | points_ledger | /points/summary | داشبورد | TST-08 | انجام |
| LED-03 | اصلاح دستاورد نامعتبر طبق سیاست بر پیشرفت/سطح/نشان اثر کند | points_ledger | — | — | TST-13 | انجام |
| LED-04 | buckets: pending/available/reserved/spent/expired/reversed-adjusted + گذارهای روشن | points_ledger | — | — | PT | انجام |
| LED-05 | ماندهٔ قابل مصرف غیرمنفی | points_ledger | — | — | TST-04/PT | انجام (CHECK + قفل) |
| LED-06 | جلوگیری از امتیازدهی/مصرف مضاعف + Idempotency فرمان‌ها | shared/idempotency | — | — | TST-01/04/05 | انجام |
| LED-07 | قید یکتا در DB نه فقط کد | migrations | — | — | TST-01/03 | انجام |
| LED-08 | Transaction/Row Lock/کنترل هم‌زمانی معادل | points_ledger | — | — | TST-03/19 | انجام |
| LED-09 | Retry محدود Deadlock/Serialization | shared/uow | — | — | — | انجام |
| LED-10 | ثبت منشأ، Rule Version و Reference هر تراکنش | points_ledger | — | — | — | انجام |
| LED-11 | اصلاح با سند جبرانی؛ حذف سابقه ممنوع | points_ledger | — | — | TST-06/13 | انجام |
| LED-12 | Balance Projection قابل بازسازی + Job تطبیق و هشدار مغایرت | points_ledger | /jobs/reconcile | /tech | PT | انجام |
| LED-13 | Replay محاسبات در محیط مجزا بدون اثر | points_ledger | /jobs/replay | — | — | انجام (حالت dry-run) |
| LED-14 | سیاست صریح برای اصلاحِ امتیازِ مصرف‌شده؛ بدون بدهی خودکار | points_ledger | — | — | — | انجام (بدون خودکار؛ فقط با PolicyVersion مصوب) |
| LED-15 | مدیریت انقضا/انتقال ترم/خروج طبق سیاست نسخه‌دار | points_ledger | /jobs | — | TST-20 | انجام |
| LED-16 | تضمین‌ها با آزمون هم‌زمانی روی PostgreSQL واقعی (نه SQLite) | tests | — | — | TST-03/04/19 | انجام (PG 16.2) |
| **بخش ۱۰ — سطح، نشان، مأموریت (ACH/MIS)** | | | | | | |
| ACH-01 | سه مسیر مستقل: استمرار/مهارت/همکاری | achievements | /tiers | /badges | — | انجام |
| ACH-02 | نشان با عنوان/تصویر/صادرکننده/معیار+نسخه/صدور/اعتبار/شواهد/وضعیت/دلیل/اعتراض | achievements | /badges | /badges | TST-13 | انجام |
| ACH-03 | نمایش عمومی فقط با انتخاب دانشجو؛ لینک لغوشدنی/منقضی‌شدنی | achievements | /badges/share | — | TST-15 | انجام (BadgeShare) |
| ACH-04 | نشان باشگاه = مدرک رسمی مهارت معرفی نشود | frontend | — | /badges | — | انجام (برچسب صریح) |
| ACH-05 | مأموریت: هدف/فعالیت/پیش‌نیاز/معیار/بازه/پاداش/سقف/مسیر جایگزین/ترک/بار آموزشی | missions | /missions | /missions | — | انجام |
| ACH-06 | مأموریت گروهی: رضایت اعضا/سهم/تأیید/تفکیک همکاری مجاز از تبادل پاسخ/محدودیت امتیاز تکراری | missions | /groups | /missions | — | انجام |
| ACH-07 | بدون رتبه‌بندی عمومی در پایه؛ آینده با Flag/عضویت اختیاری/گروه قابل مقایسه | — | — | — | — | انجام (وجود ندارد؛ Backlog ثبت شد) |
| **بخش ۱۱ — کاتالوگ و گردش پاداش (RWD)** | | | | | | |
| RWD-01 | ۸ نوع پاداش تعریف‌شده | rewards | /rewards | /rewards | — | انجام |
| RWD-02 | فیلدهای کامل Reward (شرایط/هزینه/ظرفیت/هزینهٔ عملیاتی/اعتبار/تخصیص/تحویل/لغو/اشتراک داده/وضعیت) | rewards | /rewards | /rewards/:id | — | انجام |
| RWD-03 | تفکیک مزیت خودکار از خرید با امتیاز | rewards | — | — | — | انجام (auto_grant flag) |
| RWD-04 | State Machine کامل با مسیرهای ۹گانه و اثر دفترکل هر گذار | rewards | /reward-requests | /requests | SM | انجام |
| RWD-05 | رزرو ظرفیت+امتیاز در یک تراکنش محلی هماهنگ | rewards | — | — | TST-03 | انجام |
| RWD-06 | تحویل خارجی خارج از تراکنش طولانی؛ Outbox+شناسهٔ پایدار+Callback+جبران | rewards | /providers/{id}/callback | — | TST-09 | انجام |
| RWD-07 | TTL رزرو، بازپس‌گیری، جلوگیری از تحویل دوباره، کد یک‌بارمصرف، رسید، Retry/آشتی‌سازی | rewards | — | /requests | TST-20/09 | انجام |
| RWD-08 | «نامعلوم» ⇒ Reconciliation اول؛ بدون استرداد خودکار | rewards | — | — | TST-09 | انجام |
| RWD-09 | کنترل ظرفیت در درخواست هم‌زمان + نمایش شرایط/هزینه قبل از تأیید | rewards | — | /rewards/:id | TST-03 | انجام |
| RWD-10 | پاداش کمیاب: صف/سهمیه/قرعهٔ شفاف؛ کلیک‌سرعت معیار تصادفی نشود | rewards | — | — | — | بخشی (first_come + quota انجام؛ صف/قرعه: مرحله ۲) |
| RWD-11 | دعوت به پروژه/کارآموزی تضمین پذیرش نیست | rewards | — | /rewards | — | انجام (متن صریح) |
| **بخش ۱۲ — پیشنهاد پاداش هوشمند (REC)** | | | | | | |
| REC-01 | توصیه‌گر قاعده‌محور واقعی با ۷ گام (رضایت→مجاز→فیلتر→تطبیق→تنوع→دلیل→بازخورد) | recommendations | /recommendations | /recommendations | TST-11 | انجام |
| REC-02 | فقط ورودی‌های مجاز؛ بدون دادهٔ مالی/سلامت؛ بدون برچسب «ضعیف/پرریسک» | recommendations | — | — | — | انجام |
| REC-03 | بدون رضایت: کاتالوگ و پیشنهاد عمومی کار کند | recommendations | — | — | TST-11 | انجام |
| REC-04 | دادهٔ ناکافی: پیشنهاد قاعده‌محور یا انتخاب دانشجو | recommendations | — | — | — | انجام |
| REC-05 | ML: Provider Interface قابل تعویض + Dataset/Model Version + تفکیک داده + خط پایه + ارزیابی + Kill Switch + Drift | recommendations | — | — | — | مرحله ۲/۳ (Interface تعریف شده؛ ثبت Backlog) |
| REC-06 | LLM اختیاری؛ بدون حق تغییر امتیاز/شرایط/حکم | — | — | — | — | انجام (در هسته نیست) |
| REC-07 | دلیل پیشنهاد از علت واقعی محاسبه، نه متن ساختگی | recommendations | — | /recommendations | — | انجام |
| **بخش ۱۳ — سلامت آموزشی و اعتراض (INT)** | | | | | | |
| INT-01 | کنترل قطعی جدا از هشدار احتمالی | integrity_reviews | /reviews | /cases | TST-12 | انجام |
| INT-02 | کنترل پایه: تکراری/امضای نامعتبر/رزرو تکراری/سقف/تغییر غیرمجاز/دسترسی غیرمجاز | integrity+core | — | — | TST-01/12 | انجام |
| INT-03 | الگوهای احتمالی فقط Case بسازند؛ IP مشترک/ابزار کمکی/افت فعالیت/تشخیص AI به‌تنهایی تخلف نیست | integrity_reviews | — | — | TST-12 | انجام |
| INT-04 | گردش کامل ۹حالته + شواهد حداقلی + خلاصهٔ قابل فهم + زمان/مرجع + SLA و هشدار تأخیر | integrity_reviews | /reviews | /cases/:id | — | انجام |
| INT-05 | فقط تراکنش مرتبط طبق سیاست pending؛ بدون مسدودسازی گستردهٔ خودکار | points_ledger | — | — | TST-12 | انجام |
| INT-06 | تصمیم مستند و متناسب + بررسی مستقل اعتراض + اصلاح دفترکل/سطح/نشان پس از پذیرش | appeals | /appeals | /cases | TST-13 | انجام |
| INT-07 | ارجاع رسمی فقط از مسیر زیرسیستم ۱۵ | integrations | — | — | — | انجام (ReferralAdapter فقط خروجی) |
| INT-08 | تا کفایت داده: Rule-based Risk Checks با عنوان صریح | integrity_reviews | — | /tech | — | انجام |
| **بخش ۱۴ — صفحات سامانه** | | | | | | |
| PGS-01..10 | همهٔ صفحات ۱۰ نقش طبق سند | frontend | — | Sitemap doc/07 | TST-18 | انجام (نقش‌محور؛ زیرصفحات گزارش/تاریخچه در حد MVP عملیاتی) |
| **بخش ۱۵ — مدل داده** | | | | | | |
| DM-01 | ۵۵ موجودیت حداقلی سند | همه ماژول‌ها | — | — | — | انجام (فهرست در docs/04) |
| DM-02 | فیلد/نوع/Nullable/PK/FK/Unique/Check/Index/university_id/State/منبع/زمان‌ها/Retention | migrations | — | — | — | انجام |
| DM-03 | AuditLog و LedgerEntry بی‌ردپا | audit+ledger | — | — | — | انجام (DB trigger) |
| DM-04 | حذف PII با جداسازی هویت/حسابرسی + ناشناس‌سازی مصوب | audit | /data-corrections | /privacy | — | انجام (RetentionPolicy + anonymize) |
| DM-05 | نگهداری نامحدود پیش‌فرض نیست | audit | — | — | — | انجام |
| DM-06 | دادهٔ حساس در Log/Analytics/اعلان کپی نشود | core/logging | — | — | — | انجام (masker + allowlist) |
| **بخش ۱۶ — API و قراردادها** | | | | | | |
| API-01 | پیشوند /api/v1 و ۲۶ گروه | backend | همه | — | — | انجام |
| API-02 | DTO/Schema روشن؛ Pagination/Filter/Sort امن | backend | همه | — | — | انجام |
| API-03 | خطای ساختاریافته code/message/correlation_id | core/errors | — | — | — | انجام |
| API-04 | Idempotency-Key برای فرمان حساس؛ تکرار با payload متفاوت ⇒ Conflict | shared/idempotency | — | — | TST-04 | انجام |
| API-05 | مجوز و مالکیت سمت سرور | core/rbac | — | — | TST-16/17 | انجام |
| API-06 | قرارداد نسخه‌دار + نمونه Request/Response | docs/06 | — | — | CT | انجام |
| API-07 | Job Status برای کار طولانی | /jobs | — | /tech | — | انجام |
| API-08 | OpenAPI + Collection آزمایشی | /docs, scripts/api.http | — | — | — | انجام |
| API-09 | ممنوعیت Endpoint عمومی تأیید مستقیم امتیاز توسط دانشجو | — | — | — | بررسی کد | انجام |
| **بخش ۱۷ — اتصال دانشجو۳۶۰** | | | | | | |
| S360-01..09 | Adapterهای ۱،۲،۳،۴،۵و۱۳،۸،۱۲،۱۴،۱۵،۱۶ طبق سند | integrations | /system/info | — | — | انجام (Simulator جدا از Prod، حالت شفاف) |
| S360-10 | مالکیت هویت/گراف مهارت/سنجش با باشگاه نیست؛ Snapshot حداقلی با منشأ | integrations | — | /privacy | — | انجام |
| **بخش ۱۸ — اعلان‌ها (NTF)** | | | | | | |
| NTF-01 | ۶ نوع اعلان تعریف‌شده | notifications | /notifications | زنگوله | — | انجام |
| NTF-02 | سکوت/سقف/عدم تکرار/کانال/بدون دادهٔ حساس/متن محترمانه/تفکیک اختیاری-ضروری/بدون افشای نیاز حمایتی/Retry و ثبت نتیجه | notifications | /notifications/preferences | /privacy | — | انجام |
| **بخش ۱۹ — امنیت و عملیات** | | | | | | |
| SEC-01..08 | TLS/Secrets خارج ریپو/رمزنگاری و Backup در استقرار/حداقل دسترسی/CORS و Rate Limit/IDOR-Injection-XSS-CSRF/SSRF/فایل | core+استقرار | — | — | TST-SEC | بخشی (کد و تنظیمات انجام؛ آزمون نفوذ و Restore: اجرا نشده) |
| SEC-09 | فایل خصوصی + لینک کوتاه‌عمر | integrations/storage | — | — | — | انجام (امضاشده، TTL) |
| SEC-10 | Mask دادهٔ شخصی در Log | core/logging | — | — | — | انجام |
| SEC-11 | ثبت تغییر سیاست/تعدیل/تصمیم | audit | — | /audit | — | انجام |
| SEC-12 | Dependency و Secret Scanning | CI | — | — | — | انجام (workflow) |
| SEC-13 | Threat Model مستند | docs/08 | — | — | — | انجام |
| SEC-14 | Backup و آزمون Restore + Runbookها | docs/11 | — | — | — | بخشی (مستند + اسکریپت؛ اجرای Restore واقعی: اجرا نشده) |
| SEC-15 | بدون SQLite در آزمون صحت تراکنش | tests | — | — | — | انجام (PG 16.2) |
| OBS-01..04 | Structured Log/Correlation ID/Metrics/Trace + داشبورد تأخیر/Queue/Dead-letter/مغایرت | core+tech | /metrics | /tech | — | بخشی (Log/Correlation/metrics متن انجام؛ داشبورد APM خارجی: مرحله ۲) |
| PERF-01..03 | p95<2s، پردازش p95≤5min، دسترس‌پذیری ۹۹٫۵٪ — بدون آزمون اعلام نشود | — | — | — | Load | اجرا نشده (صریح) |
| **بخش ۲۰ — تحلیل اثربخشی و عدالت** | | | | | | |
| ANA-01 | ۱۲ شاخص با تعریف/بازه/پوشش | analytics | /analytics | /admin | — | انجام (تعریف + محاسبهٔ واقعی) |
| ANA-02 | فیلترهای مجاز دانشگاه/دوره/درس/برنامه | analytics | — | /admin | — | انجام |
| ANA-03 | پنهان‌سازی گروه کوچک با آستانهٔ مصوب (k=5) | analytics | — | — | — | انجام |
| ANA-04 | ویژگی حساس فقط برای انصاف با دسترسی جدا | analytics | — | — | — | انجام (endpoint مجزا + مجوز) |
| ANA-05 | کلیک ≠ موفقیت؛ بدون ادعای علیت؛ A/B فقط با تصویب | analytics | — | — | — | انجام (برچسب توصیفی) |
| **بخش ۲۱ — سیاست‌ها و تنظیمات** | | | | | | |
| CFG-01 | تنظیمات بدون تغییر کد در ۱۱ حوزه | core/settings + policy | /admin/settings | — | — | انجام |
| CFG-02 | تنظیمات حساس نسخه‌دار و نیازمند تأیید | policy_engine | /policy-approvals | — | — | انجام |
| CFG-03 | Production تا تأیید سیاست‌های ضروری وارد بهره‌برداری نشود | core/config | — | — | — | انجام (SETTINGS_REQUIRE_POLICY_SIGNOFF) |
| CFG-04 | Feature Flag برای قابلیت‌های پیشرفته | core/flags | — | — | — | انجام |
| **بخش ۲۲ — دادهٔ نمونه (SEED)** | | | | | | |
| SEED-01..11 | همهٔ اقلام ۱۱گانهٔ سند (۲ دانشگاه، نقش‌ها، رویدادهای ۵گانه، سیاست سقف/بازده، دفترکل متوازن، سطح/نشان، مأموریت فردی/گروهی، پاداش محدود/نامحدود، درخواست‌های ۳حالته، پرونده+اعتراض پذیرفته‌شده) | scripts/seed.py | — | رابط برچسب «آزمایشی» | SEED | انجام |
| SEED-12 | Seed در Prod خودکار بارگذاری نشود + برچسب محیط آزمایشی | scripts/seed.py | — | — | — | انجام (گارد محیط) |
| **بخش ۲۳ — آزمون و معیار پذیرش** | | | | | | |
| TST-01..TST-20 | ۲۰ سناریوی الزامی سند | backend/tests | — | — | نتایج واقعی در TEST_RESULTS.md | انجام (۱۸ سناریوی بک‌اند اجرا شد؛ TST-18 a11y و Load: اجرا نشده) |
| TST-L | لایه‌ها: Unit/Integration/Contract/E2E/Concurrency/Security/A11y/Load/Backup/Property | backend+frontend | — | — | — | بخشی (Unit/Integration/Contract/Concurrency/Property: انجام؛ E2E/Load/Backup: اجرا نشده) |
| **بخش ۲۴ — مراحل توسعه** | | | | | | |
| PH-0 | مرحلهٔ صفر کامل | docs | — | — | — | انجام (این بسته) |
| PH-1 | MVP عملیاتی (۱۳ قلم) | backend+frontend | — | — | — | انجام (فهرست وضعیت در README) |
| PH-2 | مأموریت پیشرفته/مهارت/ارائه‌دهندهٔ بیشتر/انصاف/توصیه‌گر داده‌محور | — | — | — | — | مرحله ۲ (Backlog) |
| PH-3 | کشف پیشرفته/شبیه‌سازی پیشرفته/پایش مدل/آزمایش انگیزشی/صنعت | — | — | — | — | مرحله ۳ (Backlog) |
| **بخش ۲۵ — روش تحویل و مستندات** | | | | | | |
| DL-01 | ۸ قلم ابتدایی تحویل | docs | — | — | — | انجام |
| DL-02..08 | گزارش هر بخش (مسیر/کد/migration/seed/فرمان/آزمون/قرارداد/وضعیت/محدودیت) | README+TEST_RESULTS | — | — | — | انجام |
| DOC-01..10 | ۱۰ سند مستندات سند کارفرما | docs | — | — | — | انجام (فهرست در README) |

**یادداشت صداقت:** هر ردیف «انجام» به کد/آزمون واقعی در این ریپو اشاره دارد. موارد «اجرا نشده» صریحاً اعلام شده‌اند و در `TEST_RESULTS.md` با دلیل ثبت می‌شوند.
