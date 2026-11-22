/** App shell: RTL sidebar, header with dark-mode + connection status, skip link (UX).
 * v1.2 — modern glass UI: aurora background, gradient active pill, sticky glass header. */
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Home, Target, ListOrdered, Medal, Flag, Gift, Receipt, Sparkles, ShieldCheck, Lock,
  CheckSquare, Users, Gauge, Scale, Package, Activity, Stamp, Store, FolderOpen, Gavel,
  FileSearch, Terminal, LogOut, Moon, Sun, WifiOff, KeyRound, Trophy,
} from "lucide-react";
import { useAuth, hasRole } from "../lib/auth";
import { NAV } from "../design/tokens";
import { Chip } from "./ui";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  home: Home, target: Target, list: ListOrdered, medal: Medal, flag: Flag, gift: Gift,
  receipt: Receipt, sparkles: Sparkles, shield: ShieldCheck, lock: Lock, check: CheckSquare,
  users: Users, gauge: Gauge, scale: Scale, package: Package, activity: Activity, stamp: Stamp,
  store: Store, folder: FolderOpen, gavel: Gavel, "file-search": FileSearch, terminal: Terminal,
  key: KeyRound, trophy: Trophy,
};

const ROLE_FA: Record<string, string> = {
  student: "دانشجو", professor: "استاد", advisor: "مشاور آموزشی", club_manager: "مدیر باشگاه",
  policy_officer: "مسئول سیاست‌گذاری", reward_provider: "ارائه‌دهندهٔ پاداش",
  edtech_specialist: "کارشناس سلامت آموزشی", appeal_referee: "مرجع اعتراض",
  tech_admin: "مدیر فنی", auditor: "حسابرس",
};

/** لوگوی گرادیانی باشگاه — یک‌جا تعریف شده تا در سایدبار/هدر/موبایل یکسان باشد. */
function BrandMark({ className = "size-9" }: { className?: string }) {
  return (
    <span className={`grid ${className} shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-primary via-[#31427f] to-accent text-primary-fg shadow-glow`}>
      <svg viewBox="0 0 32 32" className="size-1/2" aria-hidden>
        <circle cx="16" cy="16" r="12" fill="none" stroke="currentColor" strokeWidth="2.6" opacity=".9" />
        <circle cx="16" cy="16" r="5" fill="currentColor" />
      </svg>
    </span>
  );
}

export default function AppShell() {
  const { me, loading, logout } = useAuth();
  const [dark, setDark] = useState(() => localStorage.getItem("theme") === "dark");
  const [offline, setOffline] = useState(!navigator.onLine);
  const nav = useNavigate();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.classList.toggle("light", !dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    const on = () => setOffline(false), off = () => setOffline(true);
    window.addEventListener("online", on); window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);

  if (loading) return <div className="flex min-h-screen items-center justify-center text-ink-soft">در حال بارگذاری…</div>;
  if (!me) { nav("/login"); return null; }

  const items = NAV
    // multi-role entries (e.g. تنظیمات ورود یکپارچه: مدیر باشگاه + مدیر فنی)
    .filter((n) => (n.roles ? n.roles.some((r) => hasRole(me, r)) : true))
    .filter((n) => (n.perm ? me.permissions.includes(n.perm) : true) && (n.role ? hasRole(me, n.role) || me.permissions.includes(n.perm ?? "") : true))
    .filter((n) => !(n.role && !hasRole(me, n.role) && n.role !== "student"))
    .filter((n) => (!n.perm || me.permissions.includes(n.perm)));

  const initials = (me.display_name || "؟").trim().slice(0, 2);

  return (
    <div className="relative flex min-h-screen flex-col">
      {/* پس‌زمینهٔ تزئینی aurora — فقط لایهٔ بصری */}
      <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="orb orb-a" />
        <div className="orb orb-b" />
        <div className="orb orb-c" />
        <div className="absolute inset-0 bg-grid mask-fade" />
      </div>

      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-fg">
        پرش به محتوای اصلی
      </a>
      {offline && (
        <div role="status" className="flex items-center justify-center gap-2 bg-warn/10 py-1.5 text-xs text-warn">
          <WifiOff className="size-4" aria-hidden /> اتصال قطع است — آخرین داده‌های دریافت‌شده نمایش داده می‌شود
        </div>
      )}
      <div className="mx-auto flex w-full max-w-7xl flex-1 gap-6 px-3 md:px-6">
        <aside className="sticky top-3 my-3 hidden h-[calc(100vh-1.5rem)] w-64 shrink-0 flex-col rounded-3xl border border-line/70 bg-surface/70 p-4 shadow-md backdrop-blur-xl lg:flex" aria-label="ناوبری اصلی">
          <div className="mb-5 flex items-center gap-2.5 px-1">
            <BrandMark />
            <div>
              <p className="font-extrabold leading-5">باشگاه دانشجو۳۶۰</p>
              <p className="text-[10px] text-ink-soft">پیشرفت · مشارکت · تجربه</p>
            </div>
          </div>
          <nav className="scroll-thin flex-1 space-y-1 overflow-y-auto pr-1">
            {items.map((n) => {
              const Icon = ICONS[n.icon] ?? Home;
              return (
                <NavLink key={n.to} to={n.to} end={n.to === "/"}
                  className={({ isActive }) => `group flex min-h-11 items-center gap-2.5 rounded-xl px-3 text-sm transition-all ${isActive
                    ? "bg-gradient-to-l from-primary to-[#31427f] font-bold text-primary-fg shadow-glow dark:from-primary dark:to-[#31427f]"
                    : "text-ink-soft hover:translate-x-[-2px] hover:bg-primary/5 hover:text-ink"}`}>
                  <Icon className="size-4.5 shrink-0" aria-hidden />
                  <span className="truncate">{n.label}</span>
                </NavLink>
              );
            })}
          </nav>
          <div className="mt-3 rounded-2xl border border-line/70 bg-gradient-to-bl from-accent/10 to-transparent p-3 text-[10px] leading-5 text-ink-soft">
            زیرسیستم ۱۷ اکوسیستم دانشجو۳۶۰ — ورود یکپارچه با هویت سازمانی
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col py-4">
          <header className="sticky top-0 z-20 mb-4 -mx-3 flex flex-wrap items-center justify-between gap-3 border-b border-line/60 bg-bg/70 px-3 py-2.5 backdrop-blur-xl md:-mx-4 md:px-4">
            <div className="flex items-center gap-2 lg:hidden">
              <BrandMark className="size-8" />
              <span className="font-extrabold">باشگاه دانشجو۳۶۰</span>
            </div>
            <div className="mr-auto flex items-center gap-2">
              <Chip>{me.roles.map((r) => ROLE_FA[r] ?? r).join("، ") || "کاربر"}</Chip>
              <span className="hidden items-center gap-2 md:flex">
                <span className="grid size-9 place-items-center rounded-full bg-gradient-to-br from-primary to-accent text-xs font-extrabold text-primary-fg shadow-glow" aria-hidden>{initials}</span>
                <span className="text-sm">{me.display_name}</span>
              </span>
              <button onClick={() => setDark(!dark)} aria-label={dark ? "حالت روشن" : "حالت تاریک"}
                className="grid size-11 place-items-center rounded-xl border border-line bg-surface transition hover:border-accent hover:text-accent">
                {dark ? <Sun className="size-5" /> : <Moon className="size-5" />}
              </button>
              <button onClick={async () => { await logout(); nav("/login"); }}
                className="flex min-h-11 items-center gap-1.5 rounded-xl border border-line bg-surface px-3 text-sm transition hover:border-bad/50 hover:text-bad">
                <LogOut className="size-4" aria-hidden /> خروج
              </button>
            </div>
          </header>
          <nav aria-label="ناوبری موبایل" className="scroll-thin mb-3 flex gap-2 overflow-x-auto lg:hidden">
            {items.slice(0, 8).map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === "/"}
                className={({ isActive }) => `whitespace-nowrap rounded-full border px-3.5 py-2 text-xs transition ${isActive
                  ? "border-transparent bg-gradient-to-l from-primary to-[#31427f] font-bold text-primary-fg shadow-glow"
                  : "border-line bg-surface/70 text-ink-soft backdrop-blur"}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
          <main id="main" className="animate-fade-up flex-1 pb-10">
            <Outlet />
          </main>
          <footer className="mt-auto border-t border-line/60 py-3 text-center text-[11px] text-ink-soft">
            باشگاه دانشجو۳۶۰ — زیرسیستم ۱۷ دانشجو۳۶۰ · امتیاز باشگاه با نمره و وضعیت تحصیلی متفاوت است · دادهٔ نمایش‌داده‌شده در این محیط «نمونه — محیط آزمایشی» است
          </footer>
        </div>
      </div>
    </div>
  );
}
