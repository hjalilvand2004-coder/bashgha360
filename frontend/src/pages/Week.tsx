import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays } from "lucide-react";
import { get, post } from "../lib/api";
import { Button, Card, Chip, EmptyState, PageHeader, Skeleton } from "../components/ui";
import { formatJalali } from "../lib/format";
import { OPPORTUNITY_KIND_ICONS, OPPORTUNITY_KIND_LABELS } from "../lib/student_life";

type Opportunity = {
  id: string; title_fa: string; what_fa: string; location_fa: string; starts_at: string;
  duration_minutes: number; cost_label_fa: string; is_free: boolean; prereq_fa: string;
  solo_friendly: boolean; kind: string; capacity: number; confirmed_count: number;
  seats_left: number; waitlist_count: number; my_state: string | null;
};

/** وعدهٔ «تجربه‌های من» — «امروز در دانشگاه چه خبر؟»: فرصت‌های نزدیک با فقط اطلاعات تصمیم‌گیری. */
export default function Week() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const [free, setFree] = useState(false);
  const [solo, setSolo] = useState(false);
  const [short, setShort] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["week", free, solo, short],
    queryFn: () => get<{ items: Opportunity[] }>(`/student-life/week?free=${free}&solo=${solo}&short=${short}`),
  });

  const register = useMutation({
    mutationFn: (id: string) => post<{ state: string; note_fa?: string }>(`/student-life/week/${id}/register`, {}),
    onSuccess: (r: { state: string; note_fa?: string }) => {
      qc.invalidateQueries({ queryKey: ["week"] });
      setMsg(r.state === "waitlisted" ? (r.note_fa ?? "در صف انتظار قرار گرفتی.")
        : "ثبت‌نام انجام شد — این برنامه ارزش فوری است و امتیازی نمی‌برد. 😉");
    },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });
  const cancel = useMutation({
    mutationFn: (id: string) => post(`/student-life/week/${id}/cancel`, {}),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["week"] }); setMsg("ثبت‌نامت لغو شد؛ اگر کسی در صف بود، جایش را گرفت."); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });

  const F = ({ on, set, label }: { on: boolean; set: (v: boolean) => void; label: string }) => (
    <button aria-pressed={on} onClick={() => set(!on)}
      className={`rounded-full border px-3.5 py-2 text-xs transition-all ${on ? "border-transparent bg-gradient-to-l from-primary to-[#31427f] font-bold text-primary-fg shadow-glow" : "border-line bg-surface text-ink-soft hover:border-accent/50 hover:text-ink"}`}>
      {label}
    </button>
  );

  return (
    <div className="space-y-5">
      <PageHeader title="همین هفته در دانشگاه" icon={<CalendarDays className="size-5" />}
        subtitle="فرصت‌های نزدیک، با فقط اطلاعات تصمیم‌گیری: چه اتفاقی می‌افتد؟ کجا؟ کِی؟ چقدر هزینه دارد؟ باید چیزی بلد باشم؟" />

      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="فیلترها">
        <F on={free} set={setFree} label="رایگان" />
        <F on={solo} set={setSolo} label="برای شرکت به‌تنهایی" />
        <F on={short} set={setShort} label="بین دو کلاس جا می‌شود (کمتر از ۹۰ دقیقه)" />
      </div>
      {msg && <p role="status" className="rounded-xl border border-ok/30 bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}

      {isLoading && <div className="grid gap-4 md:grid-cols-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-40" />)}</div>}
      {data && data.items.length === 0 && (
        <EmptyState art="trophy" title="این هفته برنامه‌ای با این فیلترها نیست"
          body="فیلترها را بردار یا صفحه را چند روز دیگر دوباره ببین — برنامه‌ها را باشگاه و دانشجوها می‌سازند." />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {data?.items.map((o) => {
          const dur = o.duration_minutes <= 45 ? "☕ بین دو کلاس" : o.duration_minutes <= 90 ? "🌤 یک عصر کوتاه" : "🌙 یک برنامهٔ کامل";
          return (
            <Card key={o.id} className="group relative flex flex-col gap-2.5 overflow-hidden pt-5">
              <span aria-hidden className="absolute inset-x-0 top-0 h-1.5 bg-gradient-to-l from-violet to-accent" />
              <div className="flex items-start gap-2.5">
                <span aria-hidden className="grid size-12 shrink-0 place-items-center rounded-2xl bg-bg text-2xl transition-transform group-hover:animate-wiggle">{OPPORTUNITY_KIND_ICONS[o.kind] ?? "📍"}</span>
                <div className="min-w-0 flex-1">
                  <p className="font-bold leading-6">{o.title_fa}</p>
                  <p className="text-[11px] text-ink-soft">{OPPORTUNITY_KIND_LABELS[o.kind] ?? o.kind}</p>
                </div>
                {o.is_free && <Chip tone="ok">رایگان</Chip>}
              </div>
              {o.what_fa && <p className="text-sm leading-6 text-ink-soft">{o.what_fa}</p>}
              <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 rounded-xl bg-bg p-3 text-xs text-ink-soft">
                <div>🕐 <span className="text-ink">{formatJalali(o.starts_at)}</span> · {dur}</div>
                <div>📍 <span className="text-ink">{o.location_fa}</span></div>
                <div>💰 <span className="text-ink">{o.cost_label_fa}</span></div>
                <div>🎒 پیش‌نیاز: <span className="text-ink">{o.prereq_fa || "هیچ"}</span></div>
              </dl>
              <div className="flex flex-wrap items-center gap-2">
                {o.solo_friendly && <Chip tone="info">تنهایی‌پسند ✓</Chip>}
                {o.my_state === "registered" ? (
                  <>
                    <Chip tone="ok">ثبت‌نام شدی 🎉</Chip>
                    <Button size="sm" variant="ghost" loading={cancel.isPending} onClick={() => cancel.mutate(o.id)}>لغو</Button>
                  </>
                ) : o.my_state === "waitlisted" ? (
                  <Chip tone="warn">در صف انتظار (شفاف، به‌ترتیب)</Chip>
                ) : (
                  <Button size="sm" variant="accent" loading={register.isPending} onClick={() => register.mutate(o.id)}>ثبت‌نام</Button>
                )}
                <span className="mr-auto text-[11px] text-ink-soft">
                  {o.seats_left > 0
                    ? `${o.seats_left.toLocaleString("fa-IR")} جای خالی`
                    : `${o.waitlist_count.toLocaleString("fa-IR")} نفر در صف`}
                </span>
              </div>
            </Card>
          );
        })}
      </div>
      <p className="text-center text-[11px] leading-6 text-ink-soft">
        ظرفیت پر = صف انتظار شفاف به‌ترتیب ثبت‌نام؛ «زودتر کلیک‌کردن» یا «امتیاز بیشتر» هیچ مزیت ساختگی‌ای نمی‌سازد.
      </p>
    </div>
  );
}
