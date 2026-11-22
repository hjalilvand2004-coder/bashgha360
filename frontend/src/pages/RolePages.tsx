import { useQuery } from "@tanstack/react-query";
import { get } from "../lib/api";
import { Card, Chip, EmptyState, PageHeader, Table } from "../components/ui";
import { formatJalali } from "../lib/format";

/** ارائه‌دهندهٔ پاداش: فقط درخواست‌های مربوط به خود با فیلد-کمینه (ACC-06, TST-16). */
export function Provider() {
  const { data } = useQuery({ queryKey: ["provider-queue"], queryFn: () => get<{ items: { request_ref: string; state: string; requested_at: string }[] }>("/providers/queue") });
  return (
    <div className="space-y-4">
      <PageHeader title="پنل ارائه‌دهندهٔ پاداش" subtitle="فقط اطلاعات ضروریِ درخواست‌های مربوط به خود را می‌بینید؛ دادهٔ شخصی دانشجو نمایش داده نمی‌شود." />
      {data?.items.length === 0 && <EmptyState art="store" title="درخواستی برای شما نیست" body="درخواست‌های تأییدشدهٔ پاداش‌های شما اینجا نمایش داده می‌شوند." />}
      {data && data.items.length > 0 && (
        <Card className="!p-0">
          <div className="p-4 md:p-6 md:pb-0">
            <Table head={["شناسهٔ درخواست", "وضعیت", "زمان"]} caption="درخواست‌های ارائه‌دهنده">
              {data.items.map((r) => (
                <tr key={r.request_ref} className="border-b border-line/70">
                  <td className="px-3 py-3" dir="ltr">{r.request_ref.slice(0, 8)}…</td>
                  <td className="px-3 py-3"><Chip tone="warn">{r.state}</Chip></td>
                  <td className="px-3 py-3 text-xs text-ink-soft">{formatJalali(r.requested_at, true)}</td>
                </tr>
              ))}
            </Table>
          </div>
        </Card>
      )}
      <Card className="text-xs leading-6 text-ink-soft">
        <p>ثبت تحویل/شکست از طریق Callback امضاشدهٔ ارائه‌دهنده انجام می‌شود (POST /api/v1/providers/&lt;id&gt;/callback با X-Signature).
          نتیجهٔ «نامعلوم» به‌جای استرداد خودکار، پروندهٔ آشتی‌سازی می‌سازد.</p>
      </Card>
    </div>
  );
}

/** حسابرس: Audit Trail و تغییرات حساس (SEC-11). */
export function Audit() {
  const { data } = useQuery({ queryKey: ["audit"], queryFn: () => get<{ items: { id: string; actor: string; action: string; entity: string; entity_id: string | null; created_at: string; correlation_id: string | null }[] }>("/audit?page=1&page_size=60") });
  return (
    <div className="space-y-4">
      <PageHeader title="آدیت (Audit Trail)" subtitle="تغییر سیاست، تعدیل امتیاز و تصمیم پرونده به‌صورت بی‌ردپا ثبت می‌شود." />
      {data?.items.length === 0 && <EmptyState art="empty" title="رکوردی ثبت نشده" body="اقدامات حساس سامانه اینجا لاگ می‌شوند." />}
      {data && data.items.length > 0 && (
        <Card className="!p-0">
          <div className="p-4 md:p-6 md:pb-0">
            <Table head={["انجام‌دهنده", "اقدام", "موجودیت", "زمان", "Correlation"]} caption="رخدادهای حسابرسی">
              {data.items.map((a) => (
                <tr key={a.id} className="border-b border-line/70">
                  <td className="px-3 py-2.5" dir="ltr">{a.actor}</td>
                  <td className="px-3 py-2.5" dir="ltr">{a.action}</td>
                  <td className="px-3 py-2.5">{a.entity}{a.entity_id ? ` (${a.entity_id.slice(0, 6)}…)` : ""}</td>
                  <td className="px-3 py-2.5 whitespace-nowrap text-xs text-ink-soft">{formatJalali(a.created_at, true)}</td>
                  <td className="px-3 py-2.5 text-xs" dir="ltr">{a.correlation_id ?? "—"}</td>
                </tr>
              ))}
            </Table>
          </div>
        </Card>
      )}
    </div>
  );
}

/** مدیر فنی: اتصال‌ها، صف‌ها، Jobها — بدون دادهٔ آموزشی (ACC-08). */
export function Tech() {
  const { data: sys } = useQuery({ queryKey: ["sys"], queryFn: () => get<{ integration_mode: string; queue_backend: string; environment: string; require_mfa: boolean; policy_signoff_required: boolean }>("/system/info") });
  const { data: dead } = useQuery({ queryKey: ["dead-letter"], queryFn: () => get<{ items: { id: string; message_id: string; reason: string | null }[] }>("/events/dead-letter") });
  return (
    <div className="space-y-4">
      <PageHeader title="پایش فنی" subtitle="این نقش به‌طور پیش‌فرض هیچ دسترسی‌ای به دادهٔ آموزشی ندارد (TST-17)." />
      <Card>
        <div className="flex flex-wrap gap-2">
          <Chip tone="info">integration_mode: {sys?.integration_mode}</Chip>
          <Chip tone="info">queue: {sys?.queue_backend}</Chip>
          <Chip>env: {sys?.environment}</Chip>
          <Chip tone={sys?.require_mfa ? "ok" : "warn"}>MFA: {sys?.require_mfa ? "اجباری" : "خاموش (برای عملیات واقعی اجباری شود)"}</Chip>
        </div>
      </Card>
      <Card>
        <h2 className="mb-2 font-bold">Dead-letter</h2>
        <p className="text-sm text-ink-soft">{dead?.items.length ?? 0} پیام در قرنطینه</p>
      </Card>
      <Card>
        <h2 className="mb-2 font-bold">Metrics</h2>
        <pre dir="ltr" className="scroll-thin overflow-auto rounded-md bg-bg p-3 text-[11px]">GET /api/v1/metrics — bashgah_outbox_pending / bashgah_outbox_dead / bashgah_inbox_pending / bashgah_jobs_pending</pre>
      </Card>
    </div>
  );
}
