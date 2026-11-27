import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createPortal } from "react-dom";
import { Users, ShieldAlert, Plus } from "lucide-react";
import { get, post } from "../lib/api";
import { Button, Card, Chip, DialogActions, EmptyState, Input, PageHeader, Skeleton } from "../components/ui";
import { PEER_KIND_ICONS, PEER_KIND_LABELS } from "../lib/student_life";

type PeerActivity = {
  id: string; title_fa: string; activity_kind: string; time_label_fa: string; starts_at: string | null;
  location_fa: string; capacity: number; trial_ok: boolean; interest_tags: string[];
  state: string; active_count: number; seats_left: number;
  my_state: string | null; my_mode: string | null; is_host: boolean;
};

function HostDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState({ title_fa: "", activity_kind: "study", time_label_fa: "", location_fa: "", capacity: 4 });
  const [err, setErr] = useState("");
  const create = useMutation({
    mutationFn: () => post("/student-life/peer-up", { ...f, capacity: Number(f.capacity), trial_ok: true, interest_tags: [] }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["peers"] }); onClose(); },
    onError: (e) => setErr(e instanceof Error ? e.message : "ثبت ناموفق بود"),
  });
  return createPortal(
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="animate-pop-in w-full max-w-md rounded-xl border border-line bg-surface p-5 shadow-lg" onClick={(e) => e.stopPropagation()}>
        <p className="mb-1 text-lg font-extrabold">میزبانی یک جمع کوچک</p>
        <p className="mb-4 text-xs leading-6 text-ink-soft">محل باید عمومی دانشگاه باشد؛ ۲ تا ۸ نفر؛ هم‌دانشگاهی‌ها می‌توانند «آزمایشی» بیایند. پیام خصوصی درون‌سیستمی وجود ندارد.</p>
        <div className="space-y-3">
          <Input label="عنوان فعالیت" placeholder="مثلاً همراه تمرین زبان انگلیسی" value={f.title_fa} onChange={(e) => setF({ ...f, title_fa: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <label className="w-full"><span className="mb-1.5 block text-sm font-medium">نوع</span>
              <select className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 text-sm" value={f.activity_kind} onChange={(e) => setF({ ...f, activity_kind: e.target.value })}>
                {Object.entries(PEER_KIND_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </label>
            <Input label="ظرفیت (۲ تا ۸)" type="number" min={2} max={8} value={f.capacity} onChange={(e) => setF({ ...f, capacity: Number(e.target.value) })} />
          </div>
          <Input label="زمان اعلام‌شده" placeholder="مثلاً سه‌شنبه ۱۷:۰۰" value={f.time_label_fa} onChange={(e) => setF({ ...f, time_label_fa: e.target.value })} />
          <Input label="محل عمومی دانشگاه" placeholder="مثلاً کافه دانشجویی" value={f.location_fa} onChange={(e) => setF({ ...f, location_fa: e.target.value })} />
        </div>
        {err && <p role="alert" className="mt-3 text-xs text-bad">{err}</p>}
        <DialogActions onCancel={onClose} onConfirm={() => create.mutate()} confirmLabel="ایجاد جمع" loading={create.isPending} />
      </div>
    </div>, document.body);
}

/** وعدهٔ «آدم‌های من» — همراهِ فعالیت مشخص، بدون الزام به پروژه و بدون برچسب شخصیت. */
export default function Peers() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const [reporting, setReporting] = useState<PeerActivity | null>(null);
  const [reason, setReason] = useState("");
  const [hosting, setHosting] = useState(false);
  const { data, isLoading } = useQuery({ queryKey: ["peers"], queryFn: () => get<{ items: PeerActivity[] }>("/student-life/peer-up") });

  const join = useMutation({
    mutationFn: ({ id, mode }: { id: string; mode: "trial" | "committed" }) => post(`/student-life/peer-up/${id}/join`, { mode }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["peers"] }); setMsg("به جمع پیوستید — شرکت آزمایشی یعنی بدون تعهد، هر وقت بخواهی می‌توانی بیرون بیایی."); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });
  const leave = useMutation({
    mutationFn: (id: string) => post(`/student-life/peer-up/${id}/leave`, {}),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["peers"] }); setMsg("خارج شدی — بدون هیچ جریمه‌ای. 🌱"); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });
  const report = useMutation({
    mutationFn: () => post(`/student-life/peer-up/${reporting!.id}/report`, { reason_fa: reason }),
    onSuccess: () => { setReporting(null); setReason(""); setMsg("گزارش ثبت شد و فقط برای مدیر باشگاه محرمانه می‌ماند."); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });

  return (
    <div className="space-y-5">
      <PageHeader title="هم‌پایه‌ها" icon={<Users className="size-5" />}
        subtitle="همراهِ یک فعالیت مشخص پیدا کن — بدون پروژه، بدون امتیاز، فقط آدم‌ها. تطبیق بر پایهٔ علاقه و زمان اعلام‌شده است، نه هیچ برچسبی دربارهٔ تو." />
      {msg && <p role="status" className="rounded-xl border border-ok/30 bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}

      <div className="flex justify-end">
        <Button variant="accent" onClick={() => setHosting(true)}><Plus className="size-4" /> میزبانی جمع جدید</Button>
      </div>

      {isLoading && <div className="grid gap-4 md:grid-cols-2">{[1, 2].map((i) => <Skeleton key={i} className="h-44" />)}</div>}
      {data && data.items.length === 0 && (
        <EmptyState art="compass" title="هنوز جمعی باز نیست" body="اولین جمع را تو میزبانی کن؛ فقط یک فعالیت، یک ساعت و یک محل عمومی کافی است." />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {data?.items.map((a) => (
          <Card key={a.id} className="flex flex-col gap-2.5">
            <div className="flex items-start gap-2.5">
              <span aria-hidden className="icon-bubble bg-gradient-to-br from-cyan to-accent shadow-glowAccent">{PEER_KIND_ICONS[a.activity_kind] ?? "✨"}</span>
              <div className="min-w-0 flex-1">
                <p className="font-bold leading-6">{a.title_fa}</p>
                <p className="text-xs text-ink-soft">{PEER_KIND_LABELS[a.activity_kind] ?? a.activity_kind}</p>
              </div>
              {a.trial_ok && <Chip tone="info">شرکت آزمایشی ✓</Chip>}
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs text-ink-soft">
              <span>🕐 {a.time_label_fa}</span>
              <span>📍 {a.location_fa}</span>
              <span>👥 {a.active_count.toLocaleString("fa-IR")} از {a.capacity.toLocaleString("fa-IR")} نفر</span>
              {a.interest_tags.length > 0 && <span>🏷 {a.interest_tags.join("، ")}</span>}
            </div>
            {a.state === "closed" && <Chip tone="warn">این جمع بسته شده است</Chip>}
            <div className="mt-1 flex flex-wrap items-center gap-2">
              {a.my_state === "joined" ? (
                <>
                  <Chip tone="ok">{a.my_mode === "trial" ? "عضویت آزمایشی" : "عضو"}</Chip>
                  {a.is_host && <Chip tone="gold">میزبان</Chip>}
                  <Button size="sm" variant="ghost" loading={leave.isPending} onClick={() => leave.mutate(a.id)}>خروج امن</Button>
                </>
              ) : a.state === "open" && a.seats_left > 0 ? (
                <>
                  {a.trial_ok && <Button size="sm" variant="accent" loading={join.isPending} onClick={() => join.mutate({ id: a.id, mode: "trial" })}>آزمایشی می‌آیم</Button>}
                  <Button size="sm" loading={join.isPending} onClick={() => join.mutate({ id: a.id, mode: "committed" })}>قطعی می‌آیم</Button>
                </>
              ) : a.state === "open" ? (
                <Chip tone="warn">ظرفیت پر است</Chip>
              ) : null}
              {!a.is_host && (
                <button className="mr-auto inline-flex items-center gap-1 text-xs text-ink-soft underline decoration-dotted hover:text-bad"
                  onClick={() => setReporting(a)} aria-label={`گزارش مشکل دربارهٔ ${a.title_fa}`}>
                  <ShieldAlert className="size-3.5" /> گزارش مشکل
                </button>
              )}
            </div>
          </Card>
        ))}
      </div>
      <p className="text-center text-[11px] leading-6 text-ink-soft">
        هیچ پیام خصوصی درون‌سامانه‌ای وجود ندارد؛ گزارش‌ها فقط برای مدیر باشگاه نمایش داده می‌شوند و از هویت گزارش‌دهنده محرمانه می‌مانند.
      </p>

      {hosting && <HostDialog onClose={() => setHosting(false)} />}
      {reporting && createPortal(
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4 backdrop-blur-sm" onClick={() => setReporting(null)}>
          <div className="animate-pop-in w-full max-w-md rounded-xl border border-line bg-surface p-5 shadow-lg" onClick={(e) => e.stopPropagation()}>
            <p className="mb-1 text-lg font-extrabold">گزارش مشکل</p>
            <p className="mb-3 text-xs text-ink-soft">دربارهٔ «{reporting.title_fa}» — فقط مدیر باشگاه می‌بیند.</p>
            <Input label="شرح مشکل" value={reason} onChange={(e) => setReason(e.target.value)} />
            <DialogActions onCancel={() => setReporting(null)} onConfirm={() => report.mutate()} confirmLabel="ثبت گزارش" loading={report.isPending} danger />
          </div>
        </div>, document.body)}
    </div>
  );
}
