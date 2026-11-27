/** ویجت دستیار هوشمند «دانشگاه هوشمند من» — نمایندهٔ هستهٔ عامل در باشگاه دانشجو۳۶۰ (v1.6).
 *
 * سامانهٔ مادر: «دانشگاه هوشمند من» (دانشجویار هوشمند دانشجو) که نقش دستیار هوشمند را
 * در تمامی سامانه‌های اکوسیستم دانشجو۳۶۰ بازی می‌کند. این کامپوننت اسکریپت رسمی ویجت
 * (public/msu-agent-widget.js — نسخهٔ 1.2.0 هستهٔ عامل) را با پیکربندی زیر تزریق می‌کند:
 *  - در همهٔ صفحات باشگاه (حتی صفحهٔ ورود) — با یک بار mount در App.tsx بیرون از Routes.
 *  - موقعیت: پایین‌چپ صفحه (data-position="bl") طبق مشخصات یکپارچه‌سازی.
 *  - آدرس هستهٔ عامل: VITE_MSU_AGENT_URL (پیش‌فرض: مبدأ فعلی — در استقرار واقعی ست شود).
 *  - هویت دانشجو: توکن باشگاه فقط درون‌حافظه‌ای (window.__MSU_AGENT_TOKEN) در اختیار ویجت
 *    گذاشته می‌شود تا هستهٔ عامل در هماهنگی با SSO مرکزی، راهنمای هوشمند شخصی‌سازی‌شده بدهد
 *    (الگوی رسمی ویجت: «تکیه بر توکن سامانهٔ میزبان»)؛ طبق ACC-15 در localStorage ذخیره نمی‌شود.
 */
import { useEffect } from "react";
import { getAccessToken } from "../lib/api";
import { useAuth } from "../lib/auth";

declare global {
  interface Window {
    MSUAgent?: {
      open(): void; close(): void; toggle(): void;
      setToken(jwt: string): void; clearToken(): void; version: string;
    };
    __MSU_AGENT_TOKEN?: string;
  }
}

/** آدرس هستهٔ عامل «دانشگاه هوشمند من» — از متغیر محیطی ساخت (build-time). */
export const MSU_AGENT_URL: string =
  (import.meta.env.VITE_MSU_AGENT_URL as string | undefined)?.trim() || window.location.origin;

/** شناسهٔ سامانهٔ میزبان در هستهٔ عامل — برای گزارش مبدأ گفتگوها. */
export const MSU_ORIGIN = "bashgha360";

export default function SmartAssistant() {
  const { me } = useAuth();

  // تزریق یک‌بارهٔ اسکریپت رسمی ویجت (StrictMode دوبار mount می‌شود؛ گارد id)
  useEffect(() => {
    if (document.getElementById("msu-agent-widget")) return;
    const s = document.createElement("script");
    s.id = "msu-agent-widget";
    s.src = "/msu-agent-widget.js";
    s.async = true;
    s.dataset.agentUrl = MSU_AGENT_URL;
    s.dataset.origin = MSU_ORIGIN;
    s.dataset.title = "دانشگاه هوشمند من";
    s.dataset.subtitle = "دستیار هوشمند دانشجو — متصل به هستهٔ عامل";
    s.dataset.position = "bl"; // پایین‌چپ — طبق درخواست یکپارچه‌سازی
    s.dataset.accent = "#7c3aed";   // بنفش Aurora (روز) — خوانا روی پنل روشن ویجت
    s.dataset.accent2 = "#db2777";  // صورتی Aurora (روز)
    document.body.appendChild(s);
  }, []);

  // پل هویت میزبان → ویجت: فقط حافظه؛ با خروج کاربر پاک می‌شود
  useEffect(() => {
    const t = getAccessToken();
    if (t) window.__MSU_AGENT_TOKEN = t;
    else delete window.__MSU_AGENT_TOKEN;
  }, [me]);

  return null;
}
