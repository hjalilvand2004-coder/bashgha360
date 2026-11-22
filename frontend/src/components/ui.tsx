/** UI kit — accessible, RTL-friendly base components (Component Inventory docs/07).
 * v1.4 — «جذاب دانشجویی»: کارت‌های رنگی با آیکن، حلقهٔ پیشرفت گرادیانی، جشن کاغذرنگی؛
 * API صفحات حفظ شده — فقط props اختیاری جدید اضافه شده است. */
import clsx from "clsx";
import { useMemo } from "react";
import { forwardRef } from "react";
import { Loader2 } from "lucide-react";
import { toFa } from "../lib/format";

export function Button({ variant = "primary", size = "md", loading, className, children, ...rest }:
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "accent" | "ghost" | "danger" | "gold"; size?: "sm" | "md" | "lg"; loading?: boolean }) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200 active:scale-[.97] disabled:pointer-events-none disabled:opacity-50",
        { sm: "min-h-9 px-3 text-xs", md: "min-h-11 px-4 text-sm", lg: "min-h-12 px-6 text-base" }[size],
        variant === "primary" && "bg-gradient-to-l from-primary to-[#31427f] text-primary-fg shadow-glow hover:-translate-y-0.5 hover:brightness-110 hover:shadow-lg dark:from-primary dark:to-[#31427f]",
        variant === "accent" && "bg-gradient-to-l from-accent to-[#0aa9a3] text-white shadow-glowAccent hover:-translate-y-0.5 hover:brightness-110 dark:text-[#0b1020]",
        variant === "gold" && "bg-gradient-to-l from-gold to-[#d3a04a] text-white shadow-glowGold hover:-translate-y-0.5 hover:brightness-110 dark:text-[#0b1020]",
        variant === "ghost" && "border border-line bg-surface text-ink transition hover:-translate-y-0.5 hover:border-accent/50 hover:bg-accent/5 hover:shadow-md",
        variant === "danger" && "bg-gradient-to-l from-bad to-[#c5443c] text-white shadow-md hover:-translate-y-0.5 hover:brightness-110",
        className,
      )}
      {...rest}
    >
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

export function Card({ className, children, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx("rounded-xl border border-line/80 bg-surface p-4 shadow-sm transition-all duration-300 md:p-6 hover:-translate-y-0.5 hover:shadow-md", className)} {...rest}>
      {children}
    </div>
  );
}

export function SectionTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="mb-3">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <span className="inline-block h-5 w-1.5 rounded-full bg-gradient-to-b from-primary to-accent" aria-hidden />
        {title}
      </h2>
      {hint && <p className="mt-1 text-xs text-ink-soft">{hint}</p>}
    </div>
  );
}

const chipTones: Record<string, string> = {
  neutral: "bg-bg text-ink-soft border-line",
  ok: "bg-ok/10 text-ok border-ok/30",
  warn: "bg-warn/10 text-warn border-warn/30",
  bad: "bg-bad/10 text-bad border-bad/30",
  info: "bg-accent/10 text-accent border-accent/30",
  gold: "bg-gold/10 text-gold border-gold/30",
};

export function Chip({ tone = "neutral", children }: { tone?: keyof typeof chipTones; children: React.ReactNode }) {
  return <span className={clsx("inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium", chipTones[tone])}>{children}</span>;
}

export function stateTone(state: string): keyof typeof chipTones {
  if (["delivered", "applied", "published", "accepted", "active", "valid", "completed"].includes(state)) return "ok";
  if (["reserved", "approved", "pending_approval", "in_review", "simulated", "awaiting_explanation", "pending_terms"].includes(state)) return "info";
  if (["requested", "submitted", "flagged", "draft", "paused", "human_review"].includes(state)) return "warn";
  if (["rejected", "failed", "cancelled", "expired", "revoked", "left_voluntary"].includes(state)) return "bad";
  if (state === "delivered") return "gold";
  return "neutral";
}

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }>(
  function Input({ label, error, id, className, ...rest }, ref) {
    const inputId = id || `in-${label}`;
    return (
      <div className={clsx("w-full", className)}>
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium">{label}</label>
        <input
          id={inputId} ref={ref}
          className={clsx("min-h-11 w-full rounded-xl border bg-surface px-3 text-sm outline-none transition-all duration-200",
            error ? "border-bad focus:ring-2 focus:ring-bad/20" : "border-line focus:border-accent focus:ring-2 focus:ring-accent/20")}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-err` : undefined}
          {...rest}
        />
        {error && <p id={`${inputId}-err`} role="alert" className="mt-1 text-xs text-bad">{error}</p>}
      </div>
    );
  },
);

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement> & { label: string }>(
  function Select({ label, id, className, children, ...rest }, ref) {
    const selId = id || `sel-${label}`;
    return (
      <div className={clsx("w-full", className)}>
        <label htmlFor={selId} className="mb-1.5 block text-sm font-medium">{label}</label>
        <select id={selId} ref={ref} className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 text-sm outline-none transition-all duration-200 focus:border-accent focus:ring-2 focus:ring-accent/20" {...rest}>
          {children}
        </select>
      </div>
    );
  },
);

export function Table({ head, children, caption }: { head: string[]; children: React.ReactNode; caption?: string }) {
  return (
    <div className="overflow-x-auto scroll-thin rounded-xl">
      <table className="w-full text-right text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b border-line text-xs text-ink-soft">
            {head.map((h) => <th key={h} scope="col" className="px-3 py-2.5 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-line/60">{children}</tbody>
      </table>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("rounded-xl", className ?? "h-6 w-full")} style={{ background: "linear-gradient(90deg, var(--c-border) 25%, color-mix(in srgb, var(--c-border) 40%, var(--c-surface)) 50%, var(--c-border) 75%)", backgroundSize: "200% 100%", animation: "shimmer 1.6s linear infinite" }} aria-hidden />;
}

export function EmptyState({ title, body, art = "empty" }: { title: string; body: string; art?: string }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-line p-8 text-center transition-colors hover:border-accent/50">
      <svg viewBox="0 0 96 64" className="animate-bounce-soft h-16 w-24 text-accent/60" aria-hidden>
        {art === "empty" && <g fill="none" stroke="currentColor" strokeWidth="2"><rect x="14" y="14" width="68" height="40" rx="10" /><path d="M30 32h36M30 40h22" strokeLinecap="round" /><circle cx="48" cy="22" r="4" /><circle cx="24" cy="10" r="3" className="text-gold" fill="currentColor" stroke="none" /><circle cx="76" cy="54" r="3" className="text-violet" fill="currentColor" stroke="none" /></g>}
        {art === "medal" && <g fill="none" stroke="currentColor" strokeWidth="2"><circle cx="48" cy="30" r="14" /><path d="M40 42l-6 16 14-7 14 7-6-16" /><circle cx="48" cy="30" r="6" className="text-gold" fill="currentColor" stroke="none" opacity=".6" /></g>}
        {art === "trophy" && <g fill="none" stroke="currentColor" strokeWidth="2"><path d="M36 16h24v10a12 12 0 01-24 0V16z" /><path d="M36 20h-8a8 8 0 008 8M60 20h8a8 8 0 01-8 8M48 38v8M40 50h16" strokeLinecap="round" /><circle cx="70" cy="14" r="3" className="text-gold" fill="currentColor" stroke="none" /><circle cx="26" cy="14" r="3" className="text-pink" fill="currentColor" stroke="none" /></g>}
        {art === "compass" && <g fill="none" stroke="currentColor" strokeWidth="2"><circle cx="48" cy="32" r="20" /><path d="M56 24l-5 12-12 5 5-12 12-5z" className="text-gold" fill="currentColor" stroke="none" opacity=".7" /></g>}
      </svg>
      <p className="font-bold">{title}</p>
      <p className="max-w-sm text-sm text-ink-soft">{body}</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-bad/30 bg-bad/5 p-4 text-sm">
      <p className="font-bold text-bad">خطا در دریافت اطلاعات</p>
      <p className="mt-1 text-ink-soft">{message}</p>
      {onRetry && <Button variant="ghost" size="sm" className="mt-3" onClick={onRetry}>تلاش دوباره</Button>}
    </div>
  );
}

export function Toast({ toasts }: { toasts: { id: number; text: string; tone?: "ok" | "bad" }[] }) {
  return (
    <div aria-live="polite" className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 flex-col gap-2">
      {toasts.map((t) => (
        <div key={t.id} className={clsx("animate-in rounded-xl border px-4 py-2.5 text-sm shadow-lg backdrop-blur",
          t.tone === "bad" ? "border-bad/30 bg-bad/10 text-bad" : "border-ok/30 bg-ok/10 text-ok")}>
          {t.text}
        </div>
      ))}
    </div>
  );
}

/* ---- v1.4: رنگ‌های شاد کارت‌های آماری ---- */
export const HUES = {
  primary: { bubble: "bg-gradient-to-br from-[#2b3a78] to-primary", text: "text-primary", glow: "shadow-glow" },
  accent: { bubble: "bg-gradient-to-br from-accent to-[#0aa9a3]", text: "text-accent", glow: "shadow-glowAccent" },
  gold: { bubble: "bg-gradient-to-br from-gold to-[#d3a04a]", text: "text-gold", glow: "shadow-glowGold" },
  violet: { bubble: "bg-gradient-to-br from-violet to-[#8b5cf6]", text: "text-violet", glow: "shadow-glowViolet" },
  pink: { bubble: "bg-gradient-to-br from-pink to-[#ec4899]", text: "text-pink", glow: "shadow-glowPink" },
  orange: { bubble: "bg-gradient-to-br from-orange to-[#f97316]", text: "text-orange", glow: "shadow-glowGold" },
  lime: { bubble: "bg-gradient-to-br from-lime to-[#84cc16]", text: "text-lime", glow: "shadow-glowAccent" },
} as const;
export type Hue = keyof typeof HUES;

export function StatCard({ title, value, hint, tone, icon, hue = "primary" }:
  { title: string; value: string; hint?: string; tone?: "gold" | "accent"; icon?: React.ReactNode; hue?: Hue }) {
  const h = HUES[(tone === "gold" ? "gold" : tone === "accent" ? "accent" : hue)] ?? HUES.primary;
  return (
    <Card className="group relative flex flex-col gap-1.5 overflow-hidden">
      <span aria-hidden className="absolute -left-8 -top-8 size-24 rounded-full bg-gradient-to-br from-primary/10 to-accent/10 blur-xl transition-transform duration-500 group-hover:scale-150" />
      <div className="flex items-center gap-2.5">
        {icon && <span aria-hidden className={clsx("icon-bubble", h.bubble, h.glow)}>{icon}</span>}
        <p className="text-xs text-ink-soft">{title}</p>
      </div>
      <p className={clsx("text-3xl font-extrabold tracking-tight transition-transform duration-300 group-hover:scale-105", tone ? (tone === "gold" ? "text-gold" : "text-accent") : h.text)}>{value}</p>
      {hint && <p className="text-xs text-ink-soft">{hint}</p>}
    </Card>
  );
}

export function PageHeader({ title, subtitle, badge, icon }:
  { title: string; subtitle?: string; badge?: string; icon?: React.ReactNode }) {
  return (
    <header className="mb-5">
      <div className="flex flex-wrap items-center gap-2.5">
        {(icon || badge) && (
          <span aria-hidden className="grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-primary via-[#31427f] to-accent text-primary-fg shadow-glow">
            {icon}
          </span>
        )}
        <h1 className="text-xl font-extrabold md:text-2xl">{title}</h1>
        {badge && <Chip tone="warn">{badge}</Chip>}
      </div>
      {subtitle && <p className="mt-1.5 text-sm leading-6 text-ink-soft">{subtitle}</p>}
      <span aria-hidden className="mt-2 block h-1 w-24 rounded-full bg-gradient-to-l from-primary via-accent to-violet" />
    </header>
  );
}

export function Progress({ value, max }: { value: number; max: number }) {
  const pct = Math.min(100, Math.round((value / Math.max(max, 0.001)) * 100));
  return (
    <div role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}
      className="h-2.5 w-full overflow-hidden rounded-full bg-line">
      <div className="h-full rounded-full bg-gradient-to-l from-primary via-accent to-violet transition-all duration-500"
        style={{ width: `${pct}%`, backgroundSize: "200% auto" }} />
    </div>
  );
}

/** حلقهٔ پیشرفت گرادیانی — SVG با انیمیشن پرشدن (v1.4) */
export function ProgressRing({ value, max, size = 92, stroke = 9, label, children, className }:
  { value: number; max: number; size?: number; stroke?: number; label?: string; children?: React.ReactNode; className?: string }) {
  const pct = Math.min(1, Math.max(0, value / Math.max(max, 0.001)));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const gid = useMemo(() => `rg-${Math.random().toString(36).slice(2, 8)}`, []);
  return (
    <div role="progressbar" aria-valuenow={Math.round(pct * 100)} aria-valuemin={0} aria-valuemax={100}
      aria-label={label} className={clsx("relative inline-grid place-items-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <defs>
          <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--c-primary)" />
            <stop offset="55%" stopColor="var(--c-accent)" />
            <stop offset="100%" stopColor="var(--c-violet)" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} className="ring-track" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} strokeLinecap="round"
          stroke={`url(#${gid})`} className="ring-grad"
          strokeDasharray={c} strokeDashoffset={c * (1 - pct)} />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">{children}</div>
    </div>
  );
}

/** جشن کاغذرنگی — لایهٔ تزئینی یک‌بارمصرف (aria-hidden) */
export function Celebration({ pieces = 26, className }: { pieces?: number; className?: string }) {
  const conf = useMemo(() => Array.from({ length: pieces }, (_, i) => {
    const colors = ["var(--c-primary)", "var(--c-accent)", "var(--c-gold)", "var(--c-violet)", "var(--c-pink)", "var(--c-lime)"];
    return {
      left: `${(i * 37) % 100}%`,
      delay: `${(i % 9) * 0.16}s`,
      bg: colors[i % colors.length],
      rot: `${(i * 53) % 360}deg`,
    };
  }), [pieces]);
  return (
    <div aria-hidden className={clsx("pointer-events-none fixed inset-0 z-40 overflow-hidden", className)}>
      {conf.map((p, i) => (
        <span key={i} className="confetti-piece" style={{ left: p.left, animationDelay: p.delay, background: p.bg, transform: `rotate(${p.rot})` }} />
      ))}
    </div>
  );
}

export function DialogActions({ onCancel, onConfirm, confirmLabel, cancelLabel = "انصراف", loading, danger }:
  { onCancel: () => void; onConfirm: () => void; confirmLabel: string; cancelLabel?: string; loading?: boolean; danger?: boolean }) {
  return (
    <div className="mt-4 flex flex-wrap justify-end gap-2">
      <Button variant="ghost" onClick={onCancel}>{cancelLabel}</Button>
      <Button variant={danger ? "danger" : "accent"} loading={loading} onClick={onConfirm}>{confirmLabel}</Button>
    </div>
  );
}
