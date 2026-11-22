import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, post } from "../lib/api";
import { useState } from "react";
import { Button, Card, Chip, EmptyState, PageHeader, Select, Table, stateTone } from "../components/ui";
import { MiniChart } from "../components/charts";
import { formatJalali, formatPoints, STATE_LABELS } from "../lib/format";

/** مدیر باشگاه: نمای کلی واقعی از داده (ANA). */
export function AdminOverview() {
  const { data } = useQuery({ queryKey: ["analytics"], queryFn: () => get<{ metrics: { key: string; title_fa: string; value: number | null; definition_fa: string; hidden_small_group: boolean }[]; note: string }>("/analytics/overview") });
  return (
    <div className="space-y-4">
      <PageHeader title="نمای کلی باشگاه" subtitle="همهٔ اعداد از دادهٔ واقعی سامانه تولید می‌شوند؛ برای هر شاخص، تعریف و پوشش داده درج شده است." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {data?.metrics.map((m) => (
          <Card key={m.key}>
            <p className="text-xs text-ink-soft">{m.title_fa}</p>
            <p className="mt-1 text-2xl font-extrabold">{m.value === null ? "—" : m.value.toLocaleString("fa-IR")}</p>
            {m.hidden_small_group && <Chip tone="warn">گروه کوچک — پنهان‌سازی k=۵</Chip>}
            <p className="mt-2 text-[11px] leading-5 text-ink-soft">{m.definition_fa}</p>
          </Card>
        ))}
      </div>
      {data && <p className="rounded-md bg-bg p-3 text-xs text-ink-soft">{data.note}</p>}
      <MiniChart title="شاخص‌های عددی" data={(data?.metrics ?? []).filter((m) => m.value !== null).map((m) => ({ label: m.title_fa, value: m.value as number }))}
        unit_fa="تعداد" tableCaption="شاخص‌های تجمیعی باشگاه" />
    </div>
  );
}

/** سیاست‌ها + شبیه‌سازی (PNT-07). */
export function AdminPolicies() {
  const qc = useQueryClient();
  const [simOut, setSimOut] = useState<string>("");
  const { data } = useQuery({ queryKey: ["policies"], queryFn: () => get<{ items: { id: string; code: string; title_fa: string; exclusive_group: string | null; priority: number; versions: { id: string; version_no: number; status: string; effective_from: string }[] }[] }>("/policies") });
  const simulate = useMutation({
    mutationFn: (version_id: string) => post<{ candidate_points: string; matched: boolean; note: string }>("/simulations", { version_id, payload: { duration_minutes: 60, quality: "high" } }),
    onSuccess: (d) => setSimOut(`نتیجهٔ شبیه‌سازی: امتیاز پیشنهادی ${formatPoints(d.candidate_points)} — ${d.note}`),
    onError: (e) => setSimOut(e instanceof Error ? e.message : "خطا"),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="سیاست‌ها و نسخه‌ها" subtitle="نسخهٔ منتشرشده تغییرناپذیر است؛ تغییر = نسخهٔ جدید با تأیید دوم." badge={undefined} />
      {simOut && <p role="status" className="rounded-md bg-accent/10 px-3 py-2 text-sm text-accent">{simOut}</p>}
      {data?.items.map((p) => (
        <Card key={p.id}>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <p className="font-bold">{p.title_fa}</p>
            <span dir="ltr"><Chip>{p.code}</Chip></span>
            {p.exclusive_group && <Chip tone="info">گروه انحصاری: {p.exclusive_group} · تقدم {p.priority}</Chip>}
          </div>
          <Table head={["نسخه", "وضعیت", "اعتبار از", "شبیه‌سازی"]} caption="نسخه‌های سیاست">
            {p.versions.map((v) => (
              <tr key={v.id} className="border-b border-line/70">
                <td className="px-3 py-2.5">v{v.version_no}</td>
                <td className="px-3 py-2.5"><Chip tone={stateTone(v.status)}>{STATE_LABELS[v.status] ?? v.status}</Chip></td>
                <td className="px-3 py-2.5 whitespace-nowrap text-xs text-ink-soft">{formatJalali(v.effective_from)}</td>
                <td className="px-3 py-2.5">
                  <Button size="sm" variant="ghost" onClick={() => simulate.mutate(v.id)}>اجرای شبیه‌سازی (بدون اثر دفترکل)</Button>
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      ))}
    </div>
  );
}

/** کاتالوگ + درخواست‌ها + تحویل (RWD). */
export function AdminCatalog() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const { data: rewards } = useQuery({ queryKey: ["rewards-admin"], queryFn: () => get<{ items: { id: string; title_fa: string; cost_points: string; capacity_total: number | null; state: string; delivery: string }[] }>("/rewards") });
  const { data: attempts } = useQuery({ queryKey: ["attempts"], queryFn: () => get<{ items: { id: string; request_id: string; state: string; attempt_no: number }[] }>("/reward-requests/attempts") });
  const { data: recon } = useQuery({ queryKey: ["recon"], queryFn: () => get<{ items: { id: string; request_id: string; detected_at: string }[] }>("/providers/reconciliation") });

  const deliver = useMutation({
    mutationFn: (request_id: string) => post<{ one_time_code: string }>(`/reward-requests/${request_id}/deliver`),
    onSuccess: (d) => { setMsg(`تحویل شد — کد مصرف یک‌بارمصرف: ${d.one_time_code}`); qc.invalidateQueries(); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });
  const resolve = useMutation({
    mutationFn: (p: { id: string; resolution: string }) => post(`/providers/reconciliation/${p.id}/resolve`, { resolution: p.resolution }),
    onSuccess: () => { setMsg("آشتی‌سازی انجام شد."); qc.invalidateQueries(); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="کاتالوگ، درخواست‌ها و تحویل" subtitle="تحویل نامعلوم هرگز به‌صورت خودکار مسترد نمی‌شود؛ تصمیم انسانی لازم است." />
      {msg && <p role="status" className="rounded-md bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}
      <Card>
        <h2 className="mb-2 font-bold">کاتالوگ</h2>
        <Table head={["عنوان", "هزینه", "ظرفیت", "تحویل", "وضعیت"]} caption="کاتالوگ پاداش">
          {rewards?.items.map((r) => (
            <tr key={r.id} className="border-b border-line/70">
              <td className="px-3 py-2.5 font-medium">{r.title_fa}</td>
              <td className="px-3 py-2.5">{formatPoints(r.cost_points)}</td>
              <td className="px-3 py-2.5">{r.capacity_total === null ? "نامحدود" : r.capacity_total}</td>
              <td className="px-3 py-2.5">{r.delivery === "in_app" ? "درون سامانه" : "خارجی"}</td>
              <td className="px-3 py-2.5"><Chip tone={stateTone(r.state)}>{r.state === "active" ? "فعال" : "متوقف"}</Chip></td>
            </tr>
          ))}
        </Table>
      </Card>
      <Card>
        <h2 className="mb-2 font-bold">تلاش‌های تحویل</h2>
        {attempts?.items.length === 0 && <p className="text-sm text-ink-soft">تلاشی ثبت نشده است.</p>}
        <Table head={["درخواست", "تلاش", "وضعیت"]} caption="تلاش‌های تحویل">
          {attempts?.items.map((a) => (
            <tr key={a.id} className="border-b border-line/70">
              <td className="px-3 py-2.5" dir="ltr">{a.request_id.slice(0, 8)}…</td>
              <td className="px-3 py-2.5">#{a.attempt_no}</td>
              <td className="px-3 py-2.5"><Chip tone={stateTone(a.state)}>{a.state}</Chip></td>
            </tr>
          ))}
        </Table>
      </Card>
      <Card>
        <h2 className="mb-2 font-bold">پرونده‌های آشتی‌سازی (تحویل نامعلوم)</h2>
        {recon?.items.length === 0 && <p className="text-sm text-ink-soft">موردی باز نیست.</p>}
        {recon?.items.map((c) => (
          <div key={c.id} className="mb-2 flex flex-wrap items-center justify-between gap-2 rounded-md border border-line px-3 py-2.5 text-sm">
            <span dir="ltr">{c.request_id.slice(0, 8)}…</span>
            <span className="text-xs text-ink-soft">{formatJalali(c.detected_at, true)}</span>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => resolve.mutate({ id: c.id, resolution: "delivered" })}>تحویل تأیید شد</Button>
              <Button size="sm" variant="danger" onClick={() => resolve.mutate({ id: c.id, resolution: "failed" })}>تحویل ناموفق</Button>
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}

/** سلامت اتصال و صف‌ها (OBS-04). */
export function AdminHealth() {
  const { data: sys } = useQuery({ queryKey: ["sys"], queryFn: () => get<{ integration_mode: string; queue_backend: string; environment: string; notes: string[] }>("/system/info") });
  const { data: dead } = useQuery({ queryKey: ["dead-letter"], queryFn: () => get<{ items: { id: string; message_id: string; reason: string | null; created_at: string }[] }>("/events/dead-letter") });
  const requeue = useMutation({
    mutationFn: (id: string) => post(`/events/dead-letter/${id}/requeue`),
    onSuccess: () => window.location.reload(),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="سلامت اتصال، صف‌ها و Dead-letter" subtitle="وضعیت اتصال واقعی یا آزمایشی شفاف اعلام می‌شود." />
      {sys && (
        <Card>
          <div className="flex flex-wrap gap-2">
            <Chip tone="info">حالت اتصال: {sys.integration_mode === "simulator" ? "آزمایشی (Simulator)" : sys.integration_mode}</Chip>
            <Chip tone="info">صف: {sys.queue_backend === "celery" ? "Celery + Redis" : "اجرای درون‌فرآیندی (توسعه)"}</Chip>
            <Chip>محیط: {sys.environment === "production" ? "تولید" : "توسعه/آزمایش"}</Chip>
          </div>
          <ul className="mt-3 list-inside list-disc text-xs leading-6 text-ink-soft">
            {sys.notes.map((n, i) => <li key={i}>{n}</li>)}
          </ul>
        </Card>
      )}
      <Card>
        <h2 className="mb-2 font-bold">قرنطینه / Dead-letter رویدادها</h2>
        {dead?.items.length === 0 && <EmptyState art="empty" title="Dead-letter خالی است" body="پیام‌های نامعتبر یا دیررس خارج از پنجره اینجا نگهداری می‌شوند و قابل بازپردازش‌اند." />}
        {dead?.items.map((d) => (
          <div key={d.id} className="mb-2 flex flex-wrap items-center justify-between gap-2 rounded-md border border-line px-3 py-2.5 text-sm">
            <span dir="ltr" className="text-xs">{d.message_id}</span>
            <span className="text-xs text-ink-soft">{d.reason}</span>
            <Button size="sm" variant="ghost" onClick={() => requeue.mutate(d.id)}>بازپردازش</Button>
          </div>
        ))}
      </Card>
    </div>
  );
}

/** مسئول سیاست‌گذاری: تأیید دوم (ACC-09/10). */
export function PolicyApprovals() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const { data } = useQuery({ queryKey: ["pending-policies"], queryFn: () => get<{ items: { id: string; version_no: number; policy_id: string; dsl: Record<string, unknown>; created_by: string }[] }>("/policy-approvals/pending") });

  const decide = useMutation({
    mutationFn: (p: { decision: string }) => post("/policy-approvals", p),
    onSuccess: (_d, v) => { setMsg(v.decision === "approve" ? "نسخه منتشر شد و تغییرناپذیر است." : "نسخه به پیش‌نویس بازگشت."); qc.invalidateQueries(); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا — اگر خودتان درخواست‌دهنده باشید، اجازهٔ تأیید ندارید."),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="تأیید سیاست‌ها (تأیید دوم)" subtitle="درخواست‌کننده نمی‌تواند درخواست حساس خودش را تأیید کند." />
      {msg && <p role="status" className="rounded-md bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}
      {data?.items.length === 0 && <EmptyState art="empty" title="نسخه‌ای در انتظار تأیید نیست" body="نسخه‌های جدید سیاست پس از ارسال، اینجا نمایش داده می‌شوند." />}
      {data?.items.map((v) => (
        <Card key={v.id}>
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <p className="font-bold">نسخهٔ v{v.version_no} — {v.dsl.rule_id as string}</p>
            <Chip tone="warn">{STATE_LABELS.pending_approval}</Chip>
          </div>
          <pre dir="ltr" className="scroll-thin max-h-44 overflow-auto rounded-md bg-bg p-3 text-[11px] leading-5">{JSON.stringify(v.dsl, null, 2)}</pre>
          <div className="mt-3 flex gap-2">
            <Button onClick={() => decide.mutate({ decision: "approve" })}>تأیید و انتشار</Button>
            <Button variant="danger" onClick={() => decide.mutate({ decision: "reject" })}>رد با بازگشت به پیش‌نویس</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}
