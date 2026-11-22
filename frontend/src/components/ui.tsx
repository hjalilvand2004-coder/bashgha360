/** UI kit — accessible, RTL-friendly base components (Component Inventory docs/07).
 * v1.2 — modern look: gradients, glow, rounded-xl, motion; API unchanged for pages. */
import clsx from "clsx";
import { forwardRef } from "react";
import { Loader2 } from "lucide-react";
import { toFa } from "../lib/format";

export function Button({ variant = "primary", size = "md", loading, className, children, ...rest }:
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "accent" | "ghost" | "danger" | "gold"; size?: "sm" | "md" | "lg"; loading?: boolean }) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200 active:scale-[.98] disabled:pointer-events-none disabled:opacity-50",
        { sm: "min-h-9 px-3 text-xs", md: "min-h-11 px-4 text-sm", lg: "min-h-12 px-6 text-base" }[size],
        variant === "primary" && "bg-gradient-to-l from-primary to-[#31427f] text-primary-fg shadow-glow hover:brightness-110 hover:shadow-lg dark:from-primary dark:to-[#31427f]",
        variant === "accent" && "bg-gradient-to-l from-accent to-[#0aa9a3] text-white shadow-glowAccent hover:brightness-110 dark:text-[#0b1020]",
        variant === "gold" && "bg-gradient-to-l from-gold to-[#d3a04a] text-white shadow-md hover:brightness-110 dark:text-[#0b1020]",
        variant === "ghost" && "border border-line bg-surface text-ink transition hover:border-accent/50 hover:bg-accent/5",
        variant === "danger" && "bg-gradient-to-l from-bad to-[#c5443c] text-white shadow-md hover:brightness-110",
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
    <div className={clsx("rounded-xl border border-line/80 bg-surface p-4 shadow-sm transition-shadow md:p-6 hover:shadow-md", className)} {...rest}>
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
  return <div className={clsx("animate-pulse rounded-xl bg-line/70", className)} aria-hidden />;
}

export function EmptyState({ title, body, art = "empty" }: { title: string; body: string; art?: string }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-line p-8 text-center">
      <svg viewBox="0 0 96 64" className="h-16 w-24 text-accent/60" aria-hidden>
        {art === "empty" && <g fill="none" stroke="currentColor" strokeWidth="2"><rect x="14" y="14" width="68" height="40" rx="6" /><path d="M30 32h36M30 40h22" strokeLinecap="round" /><circle cx="48" cy="22" r="4" /></g>}
        {art === "medal" && <g fill="none" stroke="currentColor" strokeWidth="2"><circle cx="48" cy="30" r="14" /><path d="M40 42l-6 16 14-7 14 7-6-16" /></g>}
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

export function StatCard({ title, value, hint, tone }: { title: string; value: string; hint?: string; tone?: "gold" | "accent" }) {
  return (
    <Card className="relative flex flex-col gap-1 overflow-hidden">
      <span aria-hidden className="absolute -left-6 -top-6 size-20 rounded-full bg-gradient-to-br from-primary/10 to-accent/10 blur-xl" />
      <p className="text-xs text-ink-soft">{title}</p>
      <p className={clsx("text-2xl font-extrabold", tone === "gold" && "text-gold", tone === "accent" && "text-accent")}>{value}</p>
      {hint && <p className="text-xs text-ink-soft">{hint}</p>}
    </Card>
  );
}

export function PageHeader({ title, subtitle, badge }: { title: string; subtitle?: string; badge?: string }) {
  return (
    <header className="mb-5">
      <div className="flex flex-wrap items-center gap-2">
        <span aria-hidden className="inline-block h-8 w-1.5 rounded-full bg-gradient-to-b from-primary to-accent shadow-glow" />
        <h1 className="text-xl font-extrabold md:text-2xl">{title}</h1>
        {badge && <Chip tone="warn">{badge}</Chip>}
      </div>
      {subtitle && <p className="mt-1.5 text-sm leading-6 text-ink-soft">{subtitle}</p>}
    </header>
  );
}

export function Progress({ value, max }: { value: number; max: number }) {
  const pct = Math.min(100, Math.round((value / Math.max(max, 0.001)) * 100));
  return (
    <div role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}
      className="h-2.5 w-full overflow-hidden rounded-full bg-line">
      <div className="h-full rounded-full bg-gradient-to-l from-primary via-accent to-primary transition-all duration-500"
        style={{ width: `${pct}%`, backgroundSize: "200% auto" }} />
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
