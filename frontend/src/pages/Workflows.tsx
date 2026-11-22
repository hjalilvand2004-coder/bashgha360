import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, post } from "../lib/api";
import { useState } from "react";
import { Button, Card, Chip, EmptyState, PageHeader } from "../components/ui";
import { formatJalali } from "../lib/format";

type Pending = { id: string; student_reference: string; event_type: string; activity_reference: string; occurred_at: string; payload: Record<string, unknown> };

/** استاد: فعالیت‌های نیازمند تأیید + شواهد و روبرک + تأیید/رد مستند (ACC-04). */
export default function Approvals() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const { data, isLoading } = useQuery({ queryKey: ["pending-verification"], queryFn: () => get<{ items: Pending[] }>("/events/pending-verification") });

  const decide = useMutation({
    mutationFn: (p: { id: string; decision: "verify" | "reject" }) =>
      post(`/events/${p.id}/verify`, { decision: p.decision === "verify" ? "approve" : "reject", reason_fa: p.decision === "reject" ? "عدم انطباق شواهد (نمونه)" : "" }),
    onSuccess: (_d, v) => { setMsg(v.decision === "verify" ? "تأیید ثبت شد؛ امتیاز در انتظار به قابل مصرف تبدیل می‌شود." : "رد مستند ثبت شد."); qc.invalidateQueries({ queryKey: ["pending-verification"] }); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="فعالیت‌های نیازمند تأیید" subtitle="فقط فعالیت‌های حوزهٔ مجاز شما (ApprovalScope) در این فهرست دیده می‌شود." />
      {msg && <p role="status" className="rounded-md bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}
      {isLoading && <Card className="text-sm text-ink-soft">بارگذاری…</Card>}
      {data && data.items.length === 0 && <EmptyState art="shield" title="فهرست خالی است" body="فعالیت در انتظار تأییدی در حوزهٔ شما وجود ندارد." />}
      <div className="space-y-3">
        {data?.items.map((p) => (
          <Card key={p.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-bold">{p.activity_reference}</p>
                <p className="mt-1 text-xs text-ink-soft">دانشجو: {p.student_reference} · نوع: {p.event_type} · زمان: {formatJalali(p.occurred_at, true)}</p>
                <p className="mt-1 text-xs text-ink-soft" dir="ltr">{JSON.stringify(p.payload)}</p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => decide.mutate({ id: p.id, decision: "verify" })}>تأیید مستند</Button>
                <Button size="sm" variant="danger" onClick={() => decide.mutate({ id: p.id, decision: "reject" })}>رد</Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

/** مشاور: دانشجویان تخصیص‌یافته + پیشنهاد مزیت حمایتی بدون برچسب‌گذاری (ACC-05, REC-02). */
export function Advisees() {
  return (
    <div className="space-y-4">
      <PageHeader title="دانشجویان تخصیص‌یافته" subtitle="داده‌های مجاز: اهداف اعلامی و پیشرفت تجمعی. هیچ برچسب عمومی «ضعیف/پرریسک» ساخته نمی‌شود." />
      <Card className="text-sm leading-7 text-ink-soft">
        <p>در این نسخهٔ MVP، نمای مشاور شامل اهداف اعلامی دانشجو و پیشرفت تأییدشده او است. پیشنهاد مزیت حمایتی
          (مثلاً معرفی کارگاه بدون هزینه) از مسیر توصیه‌گر عمومی سامانه ارائه می‌شود و هیچ دادهٔ حساس مالی/سلامتی وارد مدل نمی‌شود.</p>
        <p className="mt-2">اتصال کامل به زیرسیستم‌های مشاورهٔ دانشجو۳۶۰ در مرحلهٔ دوم (Backlog BL-05) فعال می‌شود.</p>
      </Card>
    </div>
  );
}

/** کارشناس سلامت آموزشی: صف پرونده + بررسی شواهد + تصمیم مستند (INT). */
export function ReviewCases() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const { data } = useQuery({ queryKey: ["cases-queue"], queryFn: () => get<{ items: { id: string; state: string; summary_fa: string | null; opened_at: string; sla_breached: boolean }[] }>("/reviews/cases") });

  const transition = useMutation({
    mutationFn: (p: { id: string; state: string }) => post(`/reviews/cases/${p.id}/transition`, { state: p.state }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cases-queue"] }),
  });
  const decide = useMutation({
    mutationFn: (p: { id: string; decision: string; justification_fa: string }) => post(`/reviews/cases/${p.id}/decide`, p),
    onSuccess: () => { setMsg("تصمیم مستند ثبت شد؛ هیچ اقدام خودکار گسترده‌ای انجام نمی‌شود."); qc.invalidateQueries({ queryKey: ["cases-queue"] }); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="صف پرونده‌های سلامت آموزشی" subtitle="الگوها فقط پرونده می‌سازند — تصمیم با انسان است. تفسیر متن AI و IP مشترک به‌تنهایی تخلف نیست." />
      {msg && <p role="status" className="rounded-md bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}
      {data?.items.length === 0 && <EmptyState art="shield" title="پرونده‌ای باز نیست" body="زمانی سیگنال ریسک ثبت شود، پرونده در این صفحه باز می‌شود." />}
      {data?.items.map((c) => (
        <Card key={c.id}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium">{c.summary_fa}</p>
            <div className="flex items-center gap-2">
              {c.sla_breached && <Chip tone="bad">تأخیر SLA</Chip>}
              <Chip tone="warn">{c.state}</Chip>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button size="sm" variant="ghost" onClick={() => transition.mutate({ id: c.id, state: "data_validation" })}>اعتبارسنجی داده</Button>
            <Button size="sm" variant="ghost" onClick={() => transition.mutate({ id: c.id, state: "human_review" })}>بررسی انسانی</Button>
            <Button size="sm" variant="ghost" onClick={() => transition.mutate({ id: c.id, state: "awaiting_explanation" })}>درخواست توضیح از دانشجو</Button>
            <Button size="sm" onClick={() => decide.mutate({ id: c.id, decision: "cleared", justification_fa: "بررسی انجام شد؛ تخلفی احراز نشد." })}>پاک‌سازی پرونده</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}

/** مرجع مستقل اعتراض: رسیدگی + اصلاح مجاز (ACC-07, TST-13). */
export function AppealsQueue() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const { data } = useQuery({ queryKey: ["appeals-queue"], queryFn: () => get<{ items: { id: string; state: string; subject_type: string; ground_fa: string; student_ref_id: string; reviewer_user_id: string | null }[] }>("/appeals/queue") });

  const assign = useMutation({
    mutationFn: (id: string) => post(`/appeals/${id}/assign`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["appeals-queue"] }),
  });
  const decide = useMutation({
    mutationFn: (p: { id: string; decision: string }) => post(`/appeals/${p.id}/decide`, { decision: p.decision, decision_fa: p.decision === "accepted" ? "اعتراض وارد بود؛ سند جبرانی ثبت شد." : "اعتراض وارد نبود؛ دلایل مستند شد." }),
    onSuccess: () => { setMsg("تصمیم ثبت شد؛ در صورت پذیرش، دفترکل/سطح/نشان اصلاح شده است."); qc.invalidateQueries({ queryKey: ["appeals-queue"] }); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="رسیدگی مستقل به اعتراض‌ها" subtitle="مرجع اعتراض نمی‌تواند همان کارشناس اولیه باشد؛ سامانه این استقلال را اعمال می‌کند." />
      {msg && <p role="status" className="rounded-md bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}
      {data?.items.length === 0 && <EmptyState art="shield" title="اعتراضی در صف نیست" body="اعتراض‌های دانشجویان پس از ثبت در این صف دیده می‌شوند." />}
      {data?.items.map((a) => (
        <Card key={a.id}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-medium">{a.ground_fa}</p>
              <p className="text-xs text-ink-soft" dir="ltr">{a.id}</p>
            </div>
            <Chip tone="warn">{a.state}</Chip>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {!a.reviewer_user_id && <Button size="sm" variant="ghost" onClick={() => assign.mutate(a.id)}>رسیدگی را می‌پذیرم</Button>}
            {a.reviewer_user_id && a.state === "in_review" && (
              <>
                <Button size="sm" onClick={() => decide.mutate({ id: a.id, decision: "accepted" })}>پذیرش + سند جبرانی</Button>
                <Button size="sm" variant="danger" onClick={() => decide.mutate({ id: a.id, decision: "rejected" })}>رد مستند</Button>
              </>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}
