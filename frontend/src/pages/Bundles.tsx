import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Hammer, Link2 } from "lucide-react";
import { get, post } from "../lib/api";
import { Button, Card, Chip, EmptyState, Input, PageHeader, Progress, Skeleton } from "../components/ui";

type Bundle = {
  id: string; title_fa: string; output_fa: string; tools_fa: string; guide_fa: string;
  feedback_note_fa: string; steps: { label_fa: string }[]; estimated_hours: number;
  capacity: number; seats_left: number; newcomer_seats_left: number;
  my_state: string | null; my_steps_done: number[]; my_output_url: string | null; my_output_verified: boolean;
};

/** وعدهٔ «آیندهٔ من» — «از صفر تا چیزی که بتوانم نشان بدهم»: ابزار + راهنما + بازخورد + خروجی. */
export default function Bundles() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const [url, setUrl] = useState("");
  const [linking, setLinking] = useState<string | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ["bundles"], queryFn: () => get<{ items: Bundle[] }>("/student-life/bundles") });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["bundles"] });
  const enroll = useMutation({
    mutationFn: ({ id, seat }: { id: string; seat: boolean }) => post(`/student-life/bundles/${id}/enroll`, { use_newcomer_seat: seat }),
    onSuccess: () => { invalidate(); setMsg("ثبت‌نام انجام شد — قدم‌ها را یکی‌یکی انجام بده؛ عجله‌ای نیست."); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });
  const step = useMutation({
    mutationFn: ({ id, i }: { id: string; i: number }) => post(`/student-life/bundles/${id}/steps`, { step_index: i }),
    onSuccess: () => invalidate(),
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });
  const output = useMutation({
    mutationFn: () => post(`/student-life/bundles/${linking}/output`, { output_url: url }),
    onSuccess: () => { invalidate(); setLinking(null); setUrl(""); setMsg("خروجی ثبت شد؛ پس از بازخورد راهنما «تأییدشده» می‌گیرد."); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });

  return (
    <div className="space-y-5">
      <PageHeader title="بستهٔ ساخت نمونه‌کار" icon={<Hammer className="size-5" />}
        subtitle="از صفر تا چیزی که بتوانی نشان بدهی: ابزار لازم + همراه یا راهنما + بازخورد واقعی + خروجی قابل‌نمایش — نه فقط فهرست کارها." />
      {msg && <p role="status" className="rounded-xl border border-ok/30 bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}

      {isLoading && <div className="grid gap-4">{[1, 2].map((i) => <Skeleton key={i} className="h-52" />)}</div>}
      {data && data.items.length === 0 && (
        <EmptyState art="compass" title="هنوز بسته‌ای منتشر نشده" body="بسته‌های ساخت توسط مدیر باشگاه و راهنماها ساخته می‌شوند؛ چند روز دیگر سر بزن." />
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {data?.items.map((b) => (
          <Card key={b.id} className={b.my_state ? "grad-border rounded-xl" : undefined}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-extrabold leading-6">{b.title_fa}</p>
                <p className="mt-1 text-sm text-accent">🎁 خروجی: {b.output_fa}</p>
              </div>
              {b.my_state === "completed" && <Chip tone="ok">تأییدشده ✓</Chip>}
              {b.my_state === "active" && <Chip tone="info">در جریان</Chip>}
            </div>

            <dl className="mt-3 space-y-1.5 rounded-xl bg-bg p-3 text-xs leading-6 text-ink-soft">
              {b.tools_fa && <div>🧰 ابزار لازم: <span className="text-ink">{b.tools_fa}</span></div>}
              {b.guide_fa && <div>🧭 راهنما/همراه: <span className="text-ink">{b.guide_fa}</span></div>}
              {b.feedback_note_fa && <div>💬 بازخورد: <span className="text-ink">{b.feedback_note_fa}</span></div>}
              <div>⏱ برآورد زمان: <span className="text-ink">{b.estimated_hours.toLocaleString("fa-IR")} ساعت</span> · بدون نیاز به امتیاز</div>
            </dl>

            {b.my_state ? (
              <div className="mt-3 space-y-2">
                <Progress value={b.my_steps_done.length} max={b.steps.length} />
                <ol className="space-y-1.5">
                  {b.steps.map((s, i) => (
                    <li key={i}>
                      <button disabled={b.my_state !== "active"} onClick={() => step.mutate({ id: b.id, i })}
                        className={`flex w-full items-center gap-2 rounded-xl border px-3 py-2 text-sm text-right transition-all disabled:cursor-default ${b.my_steps_done.includes(i) ? "border-ok/40 bg-ok/5" : "border-line hover:border-accent/50"}`}>
                        <span aria-hidden className={`grid size-7 shrink-0 place-items-center rounded-full text-xs font-extrabold ${b.my_steps_done.includes(i) ? "bg-gradient-to-br from-accent to-lime text-white shadow-glowAccent" : "bg-bg text-ink-soft"}`}>{b.my_steps_done.includes(i) ? "✓" : i + 1}</span>
                        <span className={b.my_steps_done.includes(i) ? "text-ink-soft line-through" : ""}>{s.label_fa}</span>
                      </button>
                    </li>
                  ))}
                </ol>
                {b.my_output_url ? (
                  <p className="flex items-center gap-1.5 text-xs text-ink-soft" dir="ltr"><Link2 className="size-3.5" /> {b.my_output_url} {b.my_output_verified && <Chip tone="ok">تأیید شد</Chip>}</p>
                ) : b.my_state === "active" && (
                  <Button size="sm" variant="gold" onClick={() => { setLinking(b.id); setUrl(""); }}>ثبت لینک خروجی</Button>
                )}
              </div>
            ) : (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button size="sm" loading={enroll.isPending} onClick={() => enroll.mutate({ id: b.id, seat: false })}>شروع می‌کنم</Button>
                {b.newcomer_seats_left > 0 && (
                  <Button size="sm" variant="ghost" loading={enroll.isPending} onClick={() => enroll.mutate({ id: b.id, seat: true })}>
                    صندلی تازه‌وارد ({b.newcomer_seats_left.toLocaleString("fa-IR")})
                  </Button>
                )}
                <span className="text-[11px] text-ink-soft">{b.seats_left.toLocaleString("fa-IR")} جای خالی از {b.capacity.toLocaleString("fa-IR")}</span>
              </div>
            )}
          </Card>
        ))}
      </div>
      <p className="text-center text-[11px] leading-6 text-ink-soft">
        صندلی‌های تازه‌وارد برای دانشجوهایی با پیشرفت تجمعی کم محفوظ است — تازه‌واردها اول نمی‌مانند. نشان خوشامدگویی جدا از این دستاوردها نمایش داده می‌شود.
      </p>

      {linking && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4 backdrop-blur-sm" onClick={() => setLinking(null)}>
          <div className="animate-pop-in w-full max-w-md rounded-xl border border-line bg-surface p-5 shadow-lg" onClick={(e) => e.stopPropagation()}>
            <p className="mb-3 text-lg font-extrabold">لینک خروجی را بفرست</p>
            <Input label="لینک (GitHub، Drive، …)" dir="ltr" placeholder="https://…" value={url} onChange={(e) => setUrl(e.target.value)} />
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setLinking(null)}>انصراف</Button>
              <Button variant="accent" loading={output.isPending} onClick={() => output.mutate()} disabled={!url.trim()}>ثبت</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
