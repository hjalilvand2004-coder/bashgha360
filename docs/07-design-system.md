# ۰۷ — سیستم طراحی بصری و فهرست کامپوننت‌ها (Component Inventory)

نسخهٔ 1.0 — «محصول دانشگاهی مدرن، حرفه‌ای، جذاب و انسانی»

## ۱. اصول

- فضای سفید کافی، سلسله‌مراتب روشن، کارت‌های مرتب، جزئیات دقیق؛ شاد و متعادل — نه کودکانه، نه شبیه بازی اعتیادآور.
- RTL کامل؛ متن ترکیبی فارسی/لاتین با `dir="auto"` در عناصر متنی.
- معنا هرگز فقط با رنگ/حرکت: همراه آیکون + متن (مثلاً وضعیت‌ها chip متنی دارند).
- انیمیشن کوتاه (≤240ms)، فقط انتقال وضعیت/جشن اختیاری دستاورد؛ `prefers-reduced-motion` محترم شمرده می‌شود (پیش‌فرض Motion: خاموش اگر کاربر درخواست کاهش حرکت کند).

## ۲. Design Tokens (تعریف در `src/design/tokens.ts` + متغیرهای CSS)

| توکن | روشن | تاریک | کاربرد |
| --- | --- | --- | --- |
| `color.bg` | `#F6F7FB` | `#0F1420` | پس‌زمینهٔ صفحه |
| `color.surface` | `#FFFFFF` | `#171E2E` | کارت‌ها |
| `color.primary` (سرمه‌ای/نیلی) | `#1E2A5A` | `#A7B4EE` | هویت برند، هدر، دکمهٔ اصلی |
| `color.primary-contrast` | `#FFFFFF` | `#0F1420` | متن روی primary |
| `color.accent` (فیروزه‌ای) | `#0E9F9A` | `#4ED8CF` | CTA ثانویه، لینک، نمودار |
| `color.gold` (تأکید محدود) | `#B8860B` | `#E3B84C` | فقط سطح/نشان/جشن دستاورد |
| `color.success` | `#1B7F4D` | `#5BD59B` | وضعیت مثبت |
| `color.warning` | `#B25E09` | `#F0B25A` | هشدار |
| `color.danger` | `#B3261E` | `#F08C85` | خطا/قرنطینه |
| `color.text` | `#171C28` | `#E8EAF2` | متن اصلی |
| `color.text-muted` | `#5A6478` | `#9AA3B8` | متن ثانویه |
| `color.border` | `#E3E7F0` | `#2A3350` | خطوط |
| `radius` | `sm 6px · md 10px · lg 16px · full` | — | |
| `space` | مقیاس 4px (4,8,12,16,24,32,48) | — | |
| `shadow` | `sm/md/lg` ملایم | تاریک: سایهٔ کم | عمق کارت |
| `font` | `Vazirmatn` (میزبانی محلی @fontsource) | — | عنوان‌ها 700/800، بدنه 400/500 |
| `motion` | `fast 120ms · base 200ms · celebrate 600ms` | — | |

**کنتراست:** ترکیب‌های متن/پس‌زمینهٔ اصلی ≥ 4.5:1 (متن بدنه) و ≥3:1 (متن بزرگ) — جدول بررسی در گزارش دسترس‌پذیری `docs/15-pilot-readiness.md`. در حالت تاریک، primary به نیلی روشن تبدیل می‌شود تا کنتراست حفظ شود.

## ۳. تایپوگرافی و اعداد

- عنوان H1 28/34·H2 22/30·H3 18/26؛ بدنه 14/22؛ زیرنویس 12/18.
- اعداد در محاسبات مالی/امتیاز: فارسی‌نما با جداکنندهٔ هزارگان (`formatPoints`)؛ نمایش تاریخ: تقویم شمسی با `Intl.DateTimeFormat('fa-IR-u-ca-persian')`؛ ذخیره/تبادل ISO-8601 UTC.

## ۴. Component Inventory (پیاده‌سازی در `src/components/ui/`)

| کامپوننت | پایه | نکتهٔ RTL/دسترس‌پذیری |
| --- | --- | --- |
| `Button` | دست‌ساز | سایز لمسی ≥44px، focus-visible حلقهٔ 2px |
| `Card`, `CardHeader/Title/Content` | — | padding یکنواخت p-4/p-6 |
| `Badge/Chip` (وضعیت) | — | آیکون + متن؛ فقط رنگ نه |
| `Input`, `Textarea`, `Select` (native styled + Radix Select برای فرم‌های اصلی) | Radix | label همیشه متصل، خطا با aria-describedby |
| `Dialog` | Radix Dialog | trap focus، Esc، برچسب فارسی |
| `Tabs` | Radix Tabs | جهت RTL خودکار |
| `Switch` | Radix Switch | برای ترجیحات/حالت تاریک |
| `Toast` | دست‌ساز (aria-live=polite) | بدون دادهٔ حساس |
| `Table` (دیتا) | — | caption، th scope، قابل ناوبری صفحه‌کلید |
| `Skeleton`, `EmptyState`, `ErrorState` | — | EmptyState با تصویرسازی SVG سبک اختصاصی |
| `Timeline` | — | تراکنش‌ها/درخواست پاداش |
| `ProgressPath` | — | مسیر تصویری سطح/پیشرفت |
| `MembershipCard` | — | کارت عضویت دیجیتال (نام، دانشگاه، سطح، شماره عضویت) |
| `PointsDualCard` | — | نمایش **مستقل** «قابل مصرف» و «پیشرفت تجمعی» |
| `RewardCard` | — | ظرفیت، شرایط، هزینهٔ امتیازی، شیوهٔ تحویل قبل از تأیید |
| `BadgeIcon` | SVG اختصاصی | سه خانواده: یادگیری/مهارت/همکاری — اصل، آفلاین، بدون مجوز خارجی |
| `StatCard`, `MiniChart` | Recharts | هر نمودار: خلاصهٔ متنی + جدول جایگزین |
| `AppShell` (سایدبار/هدر/بخش نقش‌محور) | — | Skip Link، ناوبری کامل صفحه‌کلید |

## ۵. تصویرسازی و نشان‌ها

- تمام SVGها اصل و درون‌ریپو هستند (`src/assets/illustrations/`, `badges.tsx`)؛ سبک خطی ساده با دو رنگ برند؛ بدون تصویر خارجی/لینک ناپایدار؛ مجوز: همان مجوز کد ریپو.

## ۶. حالت‌ها

- Skeleton برای هر Query؛ Error State با «تلاش دوباره»؛ Empty Stateهای فارسی (مثال: «هنوز تراکنشی ثبت نشده — با تکمیل فعالیت‌های تأییدشده، امتیاز شما اینجا دیده می‌شود.»)
- وضعیت اتصال: نوار باریک بالای صفحه در Offline («اتصال قطع است — آخرین داده‌ها نمایش داده می‌شود»).
- مسیر کم‌مصرف: بدون تصویر حجیم (SVG)، چانک‌بندی Route-level، فونت subset.

## ۷. نقشهٔ صفحات (Sitemap) — نگاشت به بخش ۱۴ سند کارفرما

```
/login · /join (عضویت+شرایط+رضایت‌ها) · / (داشبورد نقش‌محور)
دانشجو: /goals · /ledger · /badges · /missions · /rewards · /rewards/:id
        /requests · /recommendations · /cases · /privacy
استاد: /approvals          مشاور: /advisees
مدیر باشگاه: /admin (نمای کلی) · /admin/members · /admin/policies · /admin/simulation
             /admin/catalog · /admin/requests · /admin/health
مسئول سیاست: /policy-approvals      ارائه‌دهنده: /provider
کارشناس/مرجع اعتراض: /cases (صف) · /cases/:id      حسابرس: /audit      مدیر فنی: /tech
```
تمام دکمه‌های فعال به عملکرد واقعی متصل‌اند؛ صفحات دارای دادهٔ Demo برچسب «محیط آزمایشی» می‌گیرند.
