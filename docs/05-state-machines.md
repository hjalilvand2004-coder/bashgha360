# ۰۵ — ماشین‌های حالت (State Machines)

نسخهٔ 1.0. گذارهای غیرمجاز در Service لایه + در جداول transition-log رد می‌شوند. آزمون Property برای ناوردایی گذارها در `tests/test_state_machine_property.py` است.

## ۱. Membership (عضویت باشگاه)

```
draft → pending_terms → active ⇄ paused
active → left_v oluntary | graduated | transferred | suspended(admin, doc required)
paused/left/* → active (بازگشت طبق سیاست، نسخهٔ جدید Terms)
```
- گذارهای مجاز: `{draft:[pending_terms], pending_terms:[active], active:[paused,left_voluntary,graduated,transferred,suspended], paused:[active,left_voluntary,graduated], suspended:[active,left_voluntary]}`
- ناوردایی: هر حالت غیر از active/paused هیچ امتیاز کسب جدیدی نمی‌گیرد؛ اما موجودی قابل مصرف و خدمات پایه دست‌نخورده می‌ماند.

## ۲. ConsentRecord (رضایت)

```
granted → revoked (زمان‌دار، قابل پیگیری)  — revoked → granted (نسخهٔ جدید با timestamp جدید)
```
- اثر فوری: لغو رضایت شخصی‌سازی ⇒ پیشنهاد شخصی متوقف (کاتالوگ عمومی کار می‌کند — آزمون ۱۱)؛ لغو رضایت نمایش عمومی نشان ⇒ همهٔ BadgeShare فعال باطل.

## ۳. EventInboxMessage (پردازش رویداد)

```
received → validated → applied | failed(retryable) → quarantined(dead-letter)
received → rejected(schema/auth/scope/duplicate/future/late-out-of-window)
failed → applied (پس از retry موفق با backoff و سقف)
```
- ناوردایی: `applied` حداکثر یک‌بار به‌ازای کلید یکتای مرکب؛ خروجی از `applied`/`rejected` نداریم (غیرقابل برگشت).

## ۴. PolicyVersion

```
draft → simulated → pending_approval → published → retired
pending_approval → draft (رد با دلیل)  simulated → draft
```
- ناوردایی: `published`/`retired` تغییرناپذیر (بدنهٔ DSL قفل می‌شود؛ تغییر ⇒ نسخهٔ جدید). انتشار حساس: تأیید دومِ غیر از درخواست‌کننده (PolicyApproval با قید یکتای (version, approver) و بررسی requester≠approver).

## ۵. Buckets حساب امتیاز (LedgerEntry.bucket)

```
pending → available (تأیید شواهد)
available → reserved (رزرو پاداش) → spent (تحویل) | available (لغو/انقضای رزرو)
available → expired (انقضای مصوب)
هر حالت → adjusted (سند جبرانی مرتبط با سند اولیه — هرگز حذف)
```
- ناوردایی‌ها (Property-tested): `available ≥ 0`، `reserved ≥ 0`، مجموع ماندهٔ قابل بازسازی از entries == BalanceProjection == حساب؛ جمع debit==credit در هر LedgerTransaction.

## ۶. RewardRequest

```
requested → reserved → approved → fulfilling → delivered
requested/reserved/approved → rejected | cancelled
reserved → expired (TTL)          fulfilling → delivered | failed | unknown
unknown → delivered | failed      (فقط پس از Reconciliation — بدون استرداد خودکار)
failed/unknown(بعد از تصمیم) → refunded (سند جبرانی)
```

| گذار | اثر دفترکل | اثر ظرفیت |
| --- | --- | --- |
| requested→reserved | available→reserved | reserved_count +1 |
| reserved→approved | — | — |
| approved→fulfilling | — | — |
| fulfilling→delivered | reserved→spent | final_count +1 |
| reserved/approved→cancelled | reserved→available | reserved_count −1 |
| →expired | reserved→available | آزادسازی |
| →failed (پس از بررسی) | reserved→available + ثبت علت | آزادسازی |
| →refunded | available→spent جبرانی مرتبط با سند اولیه (فقط با سیاست مصوب) | — |
| →unknown | — (نگه‌داشتن رزرو تا Reconciliation) | — |

## ۷. ReviewCase (سلامت آموزشی)

```
flagged → data_validation → human_review → awaiting_explanation → decided → notified → closed
decided → appealed → final_review → closed
data_validation → dismissed (خطای داده، بدون اثر بر دانشجو)
```
- ناوردایی: هیچ گذاری به «جریمهٔ خودکار» منتهی نمی‌شود؛ فقط `decided` است که طبق سیاست می‌تواند تراکنش‌های مرتبط را pending کند (و حداکثر همان تراکنش‌ها).

## ۸. Appeal

```
submitted → in_review → accepted | rejected → implemented(در صورت accept: اصلاح دفترکل/سطح/نشان) → closed
```
- استقلال: مرجع اعتراض ≠ کارشناس اولیه (قید نقش در سرویس + audit).

## ۹. MissionParticipation

```
active → completed | quit(بدون تنبیه) | expired
```

## ۱۰. FulfillmentAttempt

```
created → sent → confirmed | failed | unknown → reconciled(confirmed|failed)
```

## ۱۱. Notification

```
queued → sending → sent | failed(retry≤N) → dead-letter
```
- تفکیک `transactional` (حقوقی/تراکنشی، همیشه ارسال) از `optional` (ترجیحات/سکوت/سقف اعمال می‌شود).

## ۱۲. DataCorrectionRequest (اصلاح داده)

```
submitted → in_review → applied | rejected → closed
```
