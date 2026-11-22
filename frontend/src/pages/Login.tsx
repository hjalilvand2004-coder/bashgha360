import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { get } from "../lib/api";
import { Button, Input } from "../components/ui";
import { useAuth } from "../lib/auth";
import { toFa } from "../lib/format";

const schema = z.object({ username: z.string().min(3, "نام کاربری را وارد کنید"), password: z.string().min(4, "رمز عبور کوتاه است") });
type FormT = z.infer<typeof schema>;

const SSO_ERRORS: Record<string, string> = {
  state: "درخواست ورود یکپارچه نامعتبر یا منقضی شده است — دوباره تلاش کنید.",
  token: "تبدیل کد احراز به توکن ناموفق بود (client_id/client_secret یا redirect_uri را در تنظیمات بررسی کنید).",
  userinfo: "اطلاعات هویت از سامانهٔ SSO دریافت نشد.",
  upstream: "سامانهٔ مرکزی SSO در دسترس نیست — بعداً تلاش کنید یا از ورود محلی استفاده کنید.",
  disabled: "ورود یکپارچه در این استقرار فعال نیست.",
};

type SsoStatus = { enabled: boolean; issuer: string; app_key: string; display_name_fa: string; icon_emoji: string; is_active: boolean; entry_url: string };

const FEATURES: { icon: string; title: string; body: string }[] = [
  { icon: "🎯", title: "پیشرفت فردی", body: "امتیاز و سطح نسبت به خط پایهٔ خودتان — بدون مقایسه با دیگران" },
  { icon: "🎁", title: "پاداش شفاف", body: "کاتالوگ پاداش با ظرفیت مشخص و رسید قابل پیگیری" },
  { icon: "🛡️", title: "حریم خصوصی", body: "دادهٔ حساس گروهی کوچک پنهان می‌شود؛ شما کنترل داده‌تان را دارید" },
];

/** صفحهٔ ورود مستقل — ورود یکپارچه با SSO (اصلی) + ورود محلی (ثانویه). v1.2: قالب دو‌ستونی مدرن. */
export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [err, setErr] = useState("");
  const { register, handleSubmit, formState } = useForm<FormT>({ resolver: zodResolver(schema) });
  const [sso, setSso] = useState<SsoStatus | null>(null);

  useEffect(() => {
    const ssoErr = params.get("sso_error");
    if (ssoErr) setErr(SSO_ERRORS[ssoErr] ?? "ورود یکپارچه ناموفق بود — دوباره تلاش کنید.");
    get<SsoStatus>("/auth/sso/status").then(setSso).catch(() => setSso(null));
  }, [params]);

  const name = sso?.display_name_fa ?? "باشگاه دانشجو۳۶۰";
  const icon = sso?.icon_emoji ?? "🎓";

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-bg p-4">
      {/* پس‌زمینهٔ aurora */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="orb orb-a" />
        <div className="orb orb-b" />
        <div className="absolute inset-0 bg-grid mask-fade" />
      </div>

      <div className="animate-fade-up grid w-full max-w-4xl overflow-hidden rounded-3xl border border-line/70 bg-surface/80 shadow-lg backdrop-blur-xl md:grid-cols-2">
        {/* ستون معرفی — فقط دسکتاپ */}
        <div className="relative hidden flex-col justify-between bg-gradient-to-bl from-primary via-[#2b3a78] to-[#1a6f74] p-8 text-primary-fg md:flex">
          <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
            <span className="absolute -right-10 -top-10 size-44 rounded-full bg-white/10 blur-2xl" />
            <span className="absolute -bottom-12 -left-8 size-56 rounded-full bg-accent/30 blur-3xl" />
          </div>
          <div className="relative">
            <span className="grid size-14 place-items-center rounded-2xl bg-white/15 text-2xl backdrop-blur" aria-hidden>{icon}</span>
            <h1 className="mt-5 text-2xl font-extrabold leading-9">{name}</h1>
            <p className="mt-2 text-xs leading-6 opacity-80">زیرسیستم ۱۷ اکوسیستم دانشجو۳۶۰ — باشگاه هوشمند پیشرفت، مشارکت و تجربهٔ دانشجو</p>
          </div>
          <ul className="relative mt-8 space-y-4">
            {FEATURES.map((f) => (
              <li key={f.title} className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/12 text-lg" aria-hidden>{f.icon}</span>
                <div>
                  <p className="text-sm font-bold">{f.title}</p>
                  <p className="mt-0.5 text-[11px] leading-5 opacity-75">{f.body}</p>
                </div>
              </li>
            ))}
          </ul>
          <p className="relative mt-8 text-[10px] opacity-70">امتیاز باشگاه با نمره و وضعیت تحصیلی متفاوت است</p>
        </div>

        {/* ستون ورود */}
        <div className="p-6 md:p-8">
          <div className="mb-6 flex flex-col items-center gap-2 md:hidden">
            <span className="grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-primary to-accent text-2xl text-primary-fg shadow-glow" aria-hidden>{icon}</span>
            <h1 className="text-xl font-extrabold">ورود به {name}</h1>
            <p className="text-center text-xs text-ink-soft">زیرسیستم ۱۷ اکوسیستم دانشجو۳۶۰</p>
          </div>

          {err && <p role="alert" className="mb-4 rounded-xl border border-bad/30 bg-bad/10 px-3 py-2 text-sm text-bad">{err}</p>}

          <a
            href="/api/v1/auth/sso/login"
            data-testid="sso-login"
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-l from-primary to-[#31427f] px-4 py-3 text-sm font-bold text-primary-fg shadow-glow transition hover:brightness-110 active:scale-[.98]"
          >
            <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            ورود یکپارچه با {name} (SSO)
          </a>
          <p className="mt-1.5 text-center text-[11px] leading-5 text-ink-soft">
            با حساب دانشجویی سامانهٔ مرکزی وارد شوید{sso?.issuer ? <> — آدرس سامانه: <code dir="ltr">{sso.issuer.replace(/^https?:\/\//, "")}</code></> : null}
          </p>

          <div className="my-5 flex items-center gap-3 text-[11px] text-ink-soft">
            <span className="h-px flex-1 bg-line" />
            یا ورود محلی (مدیران و محیط آزمایشی)
            <span className="h-px flex-1 bg-line" />
          </div>

          <form onSubmit={handleSubmit(async (d) => {
            setErr("");
            try { await login(d.username, d.password); nav("/"); }
            catch (e) { setErr(e instanceof Error ? e.message : "ورود ناموفق بود"); }
          })} className="space-y-4" noValidate>
            <Input label="نام کاربری" {...register("username")} error={formState.errors.username?.message} autoComplete="username" />
            <Input label="رمز عبور" type="password" {...register("password")} error={formState.errors.password?.message} autoComplete="current-password" />
            <Button type="submit" loading={formState.isSubmitting} variant="ghost" className="w-full">ورود محلی</Button>
          </form>

          <div className="mt-5 rounded-xl border border-line bg-bg p-3 text-xs leading-6 text-ink-soft">
            <p className="font-bold text-ink">حساب‌های نمونه (محیط آزمایشی):</p>
            <p>دانشجو: <code dir="ltr">st1@u1.demo</code> / <code dir="ltr">{toFa("12345678")}</code></p>
            <p>مدیر باشگاه: <code dir="ltr">mgr1@u1.demo</code> · حسابرس: <code dir="ltr">aud1@u1.demo</code></p>
          </div>
        </div>
      </div>
    </div>
  );
}
