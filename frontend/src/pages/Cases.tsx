import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, post } from "../lib/api";
import { useState } from "react";
import { Button, Card, Chip, EmptyState, PageHeader, stateTone } from "../components/ui";
import { formatJalali, STATE_LABELS } from "../lib/format";
import { hasRole, useAuth } from "../lib/auth";

type CaseItem = { id: string; state: string; summary_fa: string | null; opened_at: string; sla_due_at: string | null; sla_breached: boolean; student_ref_id?: string | null };
type Appeal = { id: string; subject_type: string; state: string; decision_fa: string | null; submitted_at: string };

/** Student view: own cases + appeals. Reviewer view is /review-cases, referee is /appeals-queue. */
export default function Cases() {
  const { me } = useAuth();
  const qc = useQueryClient();
  const [ground, setGround] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [msg, setMsg] = useState("");
  const { data: cases } = useQuery({ queryKey: ["my-cases"], queryFn: () => get<{ items: CaseItem[] }>("/reviews/cases"), enabled: hasRole(me, "edtech_specialist") || hasRole(me, "club_manager") });
  const { data: appeals } = useQuery({ queryKey: ["my-appeals"], queryFn: () => get<{ items: Appeal[] }>("/appeals/mine") });

  const submit = useMutation({
    mutationFn: () => post("/appeals", { subject_type: subjectId ? "review_decision" : "points_not_awarded", subject_id: subjectId || null, ground_fa: ground }),
    onSuccess: () => { setMsg("اعتراض شما ثبت شد و به مرجع مستقل ارجاع می‌شود."); setGround(""); qc.invalidateQueries({ queryKey: ["my-appeals"] }); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });

  return (
    <div className="space-y-5">
      <PageHeader title="پرونده و اعتراض" subtitle="هشدار احتمالی حکم تخلف نیست؛ شما همیشه حق توضیح و اعتراض دارید." />

      <Card>
        <h2 className="mb-2 font-bold">ثبت اعتراض جدید</h2>
        <p className="mb-3 text-xs text-ink-soft">می‌توانید به تصمیم پرونده، اصلاح دفترکل یا عدم تخصیص امتیاز اعتراض کنید. مرجع اعتراض مستقل از کارشناس اولیه است.</p>
        <div className="grid gap-3 md:grid-cols-[2fr_2fr_auto]">
          <input aria-label="شناسه موضوع (اختیاری)" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}
            placeholder="شناسه پرونده/تراکنش (اختیاری)" className="min-h-11 rounded-md border border-line bg-surface px-3 text-sm" />
          <input aria-label="دلیل اعتراض" value={ground} onChange={(e) => setGround(e.target.value)}
            placeholder="دلیل اعتراض خود را بنویسید…" className="min-h-11 rounded-md border border-line bg-surface px-3 text-sm" />
          <Button loading={submit.isPending} disabled={ground.length < 5} onClick={() => submit.mutate()}>ثبت اعتراض</Button>
        </div>
        {msg && <p role="status" className="mt-3 rounded-md bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}
      </Card>

      <section>
        <h2 className="mb-2 text-lg font-bold">اعتراض‌های من</h2>
        {appeals?.items.length ? (
          <div className="space-y-2">
            {appeals.items.map((a) => (
              <Card key={a.id} className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium">{a.subject_type === "review_decision" ? "اعتراض به تصمیم پرونده" : "اعتراض به امتیاز/اصلاح"}</p>
                  <p className="text-xs text-ink-soft">{formatJalali(a.submitted_at, true)}</p>
                  {a.decision_fa && <p className="mt-1 text-xs">{a.decision_fa}</p>}
                </div>
                <Chip tone={stateTone(a.state)}>{STATE_LABELS[a.state] ?? a.state}</Chip>
              </Card>
            ))}
          </div>
        ) : <EmptyState art="shield" title="اعتراضی ثبت نشده" body="در صورت نیاز، از فرم بالا اعتراض خود را ثبت کنید." />}
      </section>

      {(hasRole(me, "edtech_specialist") || hasRole(me, "club_manager")) && (
        <section>
          <h2 className="mb-2 text-lg font-bold">پرونده‌های بررسی (نمای کارشناسی)</h2>
          {cases?.items.map((c) => (
            <Card key={c.id} className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-medium">{c.summary_fa}</p>
                <p className="text-xs text-ink-soft">گشوده: {formatJalali(c.opened_at)} — مهلت SLA: {formatJalali(c.sla_due_at)}</p>
              </div>
              <div className="flex items-center gap-2">
                {c.sla_breached && <Chip tone="bad">تأخیر رسیدگی</Chip>}
                <Chip tone={stateTone(c.state)}>{STATE_LABELS[c.state] ?? c.state}</Chip>
              </div>
            </Card>
          ))}
        </section>
      )}
    </div>
  );
}
