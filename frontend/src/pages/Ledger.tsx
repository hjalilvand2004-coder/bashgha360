import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { get } from "../lib/api";
import { Card, Chip, EmptyState, ErrorState, PageHeader, Skeleton, Table, stateTone } from "../components/ui";
import { formatPoints, formatJalali, TX_LABELS } from "../lib/format";

type Tx = { id: string; tx_type: string; reason_fa: string | null; created_at: string; trace_link: string; correction_of: string | null };
type Trace = {
  tx: { id: string; type: string; reason_fa: string | null; idempotency_key: string | null; correction_of: string | null };
  entries: { account: string; direction: string; bucket: string; amount: string; balance_after: string }[];
  compensated_by: string[];
};

export default function Ledger() {
  const [traceId, setTraceId] = useState<string | null>(null);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["ledger"], queryFn: () => get<{ items: Tx[]; total: number }>("/ledger?page=1&page_size=50"),
  });
  const { data: trace } = useQuery({
    queryKey: ["trace", traceId], enabled: !!traceId,
    queryFn: () => get<Trace>(`/ledger/${traceId}/trace`),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="دفترکل امتیاز" subtitle="هر تخصیص، عدم تخصیص و اصلاح با دلیل قابل فهم ثبت می‌شود و قابل اعتراض است." />
      {isLoading && <Skeleton className="h-64" />}
      {error && <ErrorState message={(error as Error).message} onRetry={() => refetch()} />}
      {data && (data.items.length === 0
        ? <EmptyState title="هنوز تراکنشی ثبت نشده" body="با تکمیل فعالیت‌های تأییدشده، امتیاز شما اینجا با دلیل محاسبه دیده می‌شود." />
        : (
          <Card className="!p-0">
            <div className="p-4 md:p-6 md:pb-0">
              <Table head={["نوع", "دلیل", "زمان", "جزئیات محاسبه"]} caption="فهرست تراکنش‌های دفترکل">
                {data.items.map((t) => (
                  <tr key={t.id} className="border-b border-line/70">
                    <td className="px-3 py-3"><Chip tone={stateTone(t.tx_type === "adjust" ? "warn" : "info")}>{TX_LABELS[t.tx_type] ?? t.tx_type}</Chip></td>
                    <td className="px-3 py-3">{t.reason_fa ?? "—"}{t.correction_of && <span className="ms-1 text-xs text-warn">(سند جبرانی)</span>}</td>
                    <td className="px-3 py-3 whitespace-nowrap text-xs text-ink-soft">{formatJalali(t.created_at, true)}</td>
                    <td className="px-3 py-3">
                      <button className="text-sm font-medium text-accent" onClick={() => setTraceId(t.id)}>مشاهدهٔ Trace</button>
                    </td>
                  </tr>
                ))}
              </Table>
            </div>
          </Card>
        ))}

      {traceId && trace && (
        <div role="dialog" aria-label="جزئیات محاسبه" className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setTraceId(null)}>
          <Card className="max-h-[80vh] w-full max-w-2xl overflow-y-auto scroll-thin" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-bold">جزئیات محاسبه (Calculation Trace)</h3>
              <button onClick={() => setTraceId(null)} className="min-h-11 rounded-md border border-line px-3 text-sm">بستن</button>
            </div>
            <dl className="mb-4 grid grid-cols-2 gap-2 text-sm">
              <dt className="text-ink-soft">نوع تراکنش:</dt><dd>{TX_LABELS[trace.tx.type] ?? trace.tx.type}</dd>
              <dt className="text-ink-soft">دلیل:</dt><dd>{trace.tx.reason_fa ?? "—"}</dd>
              <dt className="text-ink-soft">کلید Idempotency:</dt><dd dir="ltr" className="truncate">{trace.tx.idempotency_key ?? "—"}</dd>
              <dt className="text-ink-soft">سند مرجع:</dt><dd dir="ltr" className="truncate">{trace.tx.correction_of ?? "—"}</dd>
              {trace.compensated_by.length > 0 && (<><dt className="text-ink-soft">جبران‌شده توسط:</dt><dd dir="ltr" className="truncate">{trace.compensated_by.join("، ")}</dd></>)}
            </dl>
            <Table head={["حساب", "جهت", "جعبه", "مبلغ", "مانده پس از"]} caption="ردیف‌های دفترکل تراکنش">
              {trace.entries.map((e, i) => (
                <tr key={i} className="border-b border-line/70">
                  <td className="px-3 py-2" dir="ltr">{e.account.slice(0, 8)}…</td>
                  <td className="px-3 py-2">{e.direction === "debit" ? "بدهکار" : "بستانکار"}</td>
                  <td className="px-3 py-2">{e.bucket}</td>
                  <td className="px-3 py-2">{formatPoints(e.amount)}</td>
                  <td className="px-3 py-2">{formatPoints(e.balance_after)}</td>
                </tr>
              ))}
            </Table>
          </Card>
        </div>
      )}
    </div>
  );
}
