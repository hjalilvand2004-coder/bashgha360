import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createPortal } from "react-dom";
import { Megaphone } from "lucide-react";
import { get, post } from "../lib/api";
import { Button, Card, Chip, EmptyState, Input, PageHeader, Skeleton } from "../components/ui";
import { formatJalali } from "../lib/format";
import { PROPOSAL_KIND_LABELS, VOICE_FLOW, VOICE_STATE_LABELS } from "../lib/student_life";

type Proposal = {
  id: string; title_fa: string; body_fa: string; support_fa: string; kind: string;
  state: string; decision_note_fa: string; vote_count: number; my_vote: boolean;
  is_mine: boolean; created_at: string;
};

function ProposeDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState({ title_fa: "", body_fa: "", support_fa: "", kind: "program" });
  const [err, setErr] = useState("");
  const create = useMutation({
    mutationFn: () => post("/student-life/voice", f),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["voice"] }); onClose(); },
    onError: (e) => setErr(e instanceof Error ? e.message : "ثبت ناموفق بود"),
  });
  return createPortal(
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="animate-pop-in w-full max-w-md rounded-xl border border-line bg-surface p-5 shadow-lg" onClick={(e) => e.stopPropagation()}>
        <p className="mb-1 text-lg font-extrabold">ایدهٔ خودت را پیشنهاد بده</p>
        <p className="mb-4 text-xs leading-6 text-ink-soft">مثال: «می‌خواهم یک دورهمی عکاسی برگزار کنم؛ به فضا، دو همراه و یک راهنما نیاز دارم.» وضعیت پیشنهاد تا اجرا قابل‌پیگیری است.</p>
        <div className="space-y-3">
          <Input label="عنوان" placeholder="دورهمی عکاسی دوشنبه‌ها" value={f.title_fa} onChange={(e) => setF({ ...f, title_fa: e.target.value })} />
          <Input label="شرح" placeholder="چه می‌خواهی برگزار کنی یا چه چیزی را تغییر دهی؟" value={f.body_fa} onChange={(e) => setF({ ...f, body_fa: e.target.value })} />
          <Input label="چه حمایتی لازم داری؟" placeholder="فضا، تجهیزات، بودجه محدود، معرفی همراه، تبلیغ…" value={f.support_fa} onChange={(e) => setF({ ...f, support_fa: e.target.value })} />
          <label className="w-full"><span className="mb-1.5 block text-sm font-medium">نوع</span>
            <select className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 text-sm" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
              {Object.entries(PROPOSAL_KIND_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
        </div>
        {err && <p role="alert" className="mt-3 text-xs text-bad">{err}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>انصراف</Button>
          <Button variant="accent" loading={create.isPending} onClick={() => create.mutate()} disabled={!f.title_fa.trim()}>ثبت پیشنهاد</Button>
        </div>
      </div>
    </div>, document.body);
}

function FlowChip({ state }: { state: string }) {
  const tone = state === "accepted" || state === "executed" ? "ok" : state === "rejected" ? "bad" : state === "in_review" ? "info" : "warn";
  return <Chip tone={tone}>{VOICE_STATE_LABELS[state] ?? state}</Chip>;
}

/** وعدهٔ «اثر من» — پیشنهاد + رأیِ برابر + پیگیری وضعیت تا اجرا. */
export default function Voice() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const [proposing, setProposing] = useState(false);
  const { data, isLoading } = useQuery({ queryKey: ["voice"], queryFn: () => get<{ items: Proposal[] }>("/student-life/voice") });

  const vote = useMutation({
    mutationFn: (id: string) => post(`/student-life/voice/${id}/vote`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["voice"] }),
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });

  return (
    <div className="space-y-5">
      <PageHeader title="صدای دانشجو" icon={<Megaphone className="size-5" />}
        subtitle="پیشنهاد بده، به گزینه‌ها رأی بده و وضعیت را تا اجرا دنبال کن. رأی همه برابر است — امتیاز بیشتر صدای قوی‌تر نمی‌سازد." />
      {msg && <p role="status" className="rounded-xl border border-bad/30 bg-bad/10 px-3 py-2 text-sm text-bad">{msg}</p>}

      <div className="flex justify-end">
        <Button variant="accent" onClick={() => setProposing(true)}>ایدهٔ خودت را پیشنهاد بده</Button>
      </div>

      {/* مسیر پیگیری مصوب */}
      <Card className="bg-bg/60 py-3">
        <ol className="flex flex-wrap items-center justify-center gap-2 text-xs">
          {VOICE_FLOW.map((s, i) => (
            <li key={s} className="flex items-center gap-2">
              <span className={`rounded-full border px-2.5 py-1 ${s === "executed" ? "border-ok/40 bg-ok/10 text-ok" : "border-line bg-surface text-ink-soft"}`}>{VOICE_STATE_LABELS[s]}</span>
              {i < VOICE_FLOW.length - 1 && <span aria-hidden className="text-line">←</span>}
            </li>
          ))}
        </ol>
      </Card>

      {isLoading && <div className="grid gap-4">{[1, 2].map((i) => <Skeleton key={i} className="h-36" />)}</div>}
      {data && data.items.length === 0 && (
        <EmptyState art="compass" title="هنوز پیشنهادی ثبت نشده" body="اولین ایده را تو بده؛ حتی ایده‌های کوچک هم مسیر پیگیری دارند." />
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {data?.items.map((p) => (
          <Card key={p.id} className={p.is_mine ? "border-accent/40" : undefined}>
            <div className="flex items-start justify-between gap-2">
              <p className="font-bold leading-6">{p.title_fa}</p>
              <FlowChip state={p.state} />
            </div>
            {p.body_fa && <p className="mt-1.5 text-sm leading-6 text-ink-soft">{p.body_fa}</p>}
            {p.support_fa && <p className="mt-1.5 text-xs text-ink">🤲 حمایتی که لازم دارد: {p.support_fa}</p>}
            {p.decision_note_fa && <p className="mt-1.5 rounded-lg bg-bg px-3 py-2 text-xs leading-6 text-ink-soft">پیام مسئول: {p.decision_note_fa}</p>}
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button aria-pressed={p.my_vote}
                onClick={() => vote.mutate(p.id)}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-all ${p.my_vote ? "border-transparent bg-gradient-to-l from-primary to-accent text-primary-fg shadow-glow" : "border-line bg-surface text-ink-soft hover:border-accent/50 hover:text-ink"}`}>
                👍 {p.my_vote ? "رأی دادی (برابر)" : "رأی می‌دهم"} · {p.vote_count.toLocaleString("fa-IR")}
              </button>
              <span className="text-[11px] text-ink-soft">{PROPOSAL_KIND_LABELS[p.kind] ?? p.kind} · {formatJalali(p.created_at)}</span>
              {p.is_mine && <Chip tone="gold">پیشنهاد تو</Chip>}
            </div>
          </Card>
        ))}
      </div>
      <p className="text-center text-[11px] leading-6 text-ink-soft">
        مسیر رسمی: دریافت شد ← بررسی شد ← پذیرفته یا رد شد ← اجرا شد. رأی پایه برای همه برابر است و به امتیاز هیچ ربطی ندارد.
      </p>

      {proposing && <ProposeDialog onClose={() => setProposing(false)} />}
    </div>
  );
}
