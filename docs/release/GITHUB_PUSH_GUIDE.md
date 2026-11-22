# راهنمای پوش به GitHub و انتشار Release — باشگاه دانشجو۳۶۰ (v1.1.1)

این راهنما دقیقاً دستورات موردنیاز برای «پوش کد + انتشار Release جدید با
نسخهٔ قابل‌حمل» را دارد. فقط `USER/REPO` را با مخزن خودتان جایگزین کنید.

## پیش‌نیازها

- `git` نصب باشد؛ برای روش سادهٔ B یکی از دو راه برای احراز هویت:
  - `gh` (GitHub CLI) نصب و `gh auth login` شده باشد، **یا**
  - یک Personal Access Token با دسترسی `repo` ساخته باشید.
- فایل‌های ساخته‌شدهٔ قابل‌حمل در پوشهٔ `build/portable/`:
  - `club360-portable-windows-x64-v1.1.1.zip`
  - `club360-portable-linux-x64-v1.1.1.tar.gz`

> نکته: در محیط ساخت فعلی credentialهای GitHub وجود ندارد، پس خودِ پوش از
> اینجا انجام نمی‌شود؛ دستورات زیر روی سیستم شما اجرا می‌شوند.

---

## مرحلهٔ ۱ — پوش کد (برچسب v1.1.1 همراه commitها آماده است)

```bash
cd club360
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/USER/REPO.git
git push -u origin main
git push origin v1.1.1          # پوش تگ نسخهٔ ۱٫۱٫۰
```

## مرحلهٔ ۲ — ساخت Release به‌صورت خودکار (روش توصیه‌شده)

خودِ مخزن یک GitHub Action دارد (`.github/workflows/release.yml`) که با پوش
شدن تگ، **هر دو بستهٔ قابل‌حمل را می‌سازد و به Release پیوست می‌کند**:

```bash
git push origin v1.1.1   # همین کافی است؛ Action بسته‌ها را می‌سازد و Release می‌سازد
```

پیشرفت در تب «Actions» مخزن دیده می‌شود؛ پس از سبز شدن، در تب «Releases»
نسخهٔ v1.1.1 با دو فایل زیر منتشر شده است:

- `club360-portable-windows-x64-v1.1.1.zip`
- `club360-portable-linux-x64-v1.1.1.tar.gz`

## مرحلهٔ ۲ جایگزین — Release دستی با `gh` (بدون صبر برای Action)

```bash
gh release create v1.1.1 \
  "build/portable/club360-portable-windows-x64-v1.1.1.zip" \
  "build/portable/club360-portable-linux-x64-v1.1.1.tar.gz" \
  --title "باشگاه دانشجو۳۶۰ — نسخهٔ قابل‌حمل $TAG (Portable + SSO)" \
  --notes-file docs/release/RELEASE_NOTES_v1.1.1.md
```

یا کاملاً دستی: تب Releases → «Draft a new release» → تگ `v1.1.1` را انتخاب
کنید → عنوان و توضیحات را از `docs/release/RELEASE_NOTES_v1.1.1.md` کپی کنید →
دو فایل بالا را Attach کنید → Publish.

## مرحلهٔ ۳ — اگر قبلاً تگ v1.0.0 را پوش کرده‌اید

تگ جدید `v1.1.1` مستقل است؛ نیازی به تغییر تگ قبلی نیست. فقط مراحل بالا را
برای v1.1.1 انجام دهید.

---

## چک‌لیست پس از انتشار

- [ ] در تب Actions اجرای `build-portable-release` سبز شده است.
- [ ] در تب Releases نسخهٔ v1.1.1 با دو پیوست دیده می‌شود.
- [ ] دانلود zip ویندوزی، استخراج و اجرای `start.bat` روی یک سیستم بدون
  پایتون امتحان شده و صفحهٔ ورود در `http://localhost:8089` باز می‌شود.
- [ ] در سامانهٔ مرکزی دانشجو۳۶۰، Client با Redirect URI زیر ثبت شده است:
  `http://188.212.96.235:8089/api/v1/auth/sso/callback`
- [ ] در سر مقصد، پورت ۸۰۸۹ در فایروال باز شده است.
