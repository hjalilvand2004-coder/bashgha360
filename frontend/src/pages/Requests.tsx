import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, post } from "../lib/api";
import { useState } from "react";
import { Button, Card, Chip, EmptyState, PageHeader, Table, stateTone } from "../components/ui";
import { formatJalali, STATE_LABELS } from "../lib/format";

type Req = { id: string; reward_title_fa: string; state: string; requested_at: string; ttl_expires_at: string | null; cancel_reason_fa: string | null; has_receipt: boolean };

export default function Requests() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const { data } = useQuery({ queryKey: ["my-requests"], queryFn: () => get<{ items: Req[] }>("/reward-requests") });
  const cancel = useMutation({
    mutationFn: (id: string) => post(`/reward-requests/${id}/cancel`),
    onSuccess: () => { setMsg("درخواست لغو شد و رزرو امتیاز/ظرفیت آزاد گردید."); qc.invalidateQueries(); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="درخواست‌ها و رسید تحویل" subtitle="رزرو امتیاز تا تأیید نهایی موقتی است؛ پس از مهلت، طبق سیاست آزاد می‌شود." />
      {msg && <p role="status" className="rounded-md bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}
      {data && data.items.length === 0 && <EmptyState art="empty" title="درخواستی ثبت نشده" body="از کاتالوگ پاداش، درخواست خود را ثبت کنید." />}
      {data && data.items.length > 0 && (
        <Card className="!p-0">
          <div className="p-4 md:p-6 md:pb-0">
            <Table head={["پاداش", "وضعیت", "زمان ثبت", "مهلت تأیید", "اقدام"]} caption="درخواست‌های پاداش من">
              {data.items.map((r) => (
                <tr key={r.id} className="border-b border-line/70">
                  <td className="px-3 py-3 font-medium">{r.reward_title_fa}</td>
                  <td className="px-3 py-3"><Chip tone={stateTone(r.state)}>{STATE_LABELS[r.state] ?? r.state}</Chip>
                    {r.cancel_reason_fa && <p className="mt-1 text-[11px] text-ink-soft">{r.cancel_reason_fa}</p>}</td>
                  <td className="px-3 py-3 whitespace-nowrap text-xs text-ink-soft">{formatJalali(r.requested_at, true)}</td>
                  <td className="px-3 py-3 whitespace-nowrap text-xs text-ink-soft">{r.ttl_expires_at ? formatJalali(r.ttl_expires_at, true) : "—"}</td>
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-2">
                      {["requested", "reserved", "approved"].includes(r.state) && (
                        <Button size="sm" variant="ghost" onClick={() => cancel.mutate(r.id)}>لغو</Button>
                      )}
                      {r.has_receipt && <Chip tone="ok">رسید تحویل موجود است</Chip>}
                    </div>
                  </td>
                </tr>
              ))}
            </Table>
          </div>
        </Card>
      )}
    </div>
  );
}
