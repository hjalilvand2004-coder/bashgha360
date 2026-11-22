import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createPortal } from "react-dom";
import { get, post } from "../lib/api";
import { Button, Card, Chip, DialogActions, PageHeader } from "../components/ui";
import { formatPoints } from "../lib/format";

type Reward = {
  id: string; type: string; title_fa: string; description_fa: string; cost_points: string;
  capacity_total: number | null; delivery: string; is_essential: boolean; auto_grant: boolean;
  validity_fa: string | null; refund_policy_fa: string; data_consent_note: string | null; kind: string;
};

const TYPE_LABEL: Record<string, string> = {
  resource_access: "دسترسی به منبع", workshop: "کارگاه", counseling: "مشاورهٔ تشویقی",
  project: "پروژهٔ آموزشی", internship_invite: "دعوت به کارآموزی", professional_perk: "مزیت حرفه‌ای",
  auto_perk: "مزیت خودکار", badge_auto: "نشان خودکار",
};

const KIND_LABEL: Record<string, { fa: string; tone: "gold" | "info" | "neutral" }> = {
  experience: { fa: "تجربه", tone: "gold" },
  choice: { fa: "حق انتخاب", tone: "info" },
  resource: { fa: "منبع", tone: "neutral" },
  physical: { fa: "مادی", tone: "neutral" },
};

export default function Rewards() {
  const qc = useQueryClient();
  const [detail, setDetail] = useState<Reward | null>(null);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [onlyExp, setOnlyExp] = useState(false);
  const { data } = useQuery({ queryKey: ["rewards"], queryFn: () => get<{ items: Reward[] }>("/rewards") });
  const items = (data?.items ?? []).filter((r) => (onlyExp ? r.kind === "experience" || r.kind === "choice" : true));

  const request = useMutation({
    mutationFn: (reward: Reward) => post<{ request_id: string; state: string; ttl_expires_at: string }>(
      "/reward-requests", { reward_id: reward.id }, `rw-${reward.id}`),
    onSuccess: (d) => {
      setMsg({ text: `درخواست ثبت و امتیاز/ظرفیت رزرو شد — تا تأیید نهایی ۳۰ دقیقه مهلت دارید.`, ok: true });
      setDetail(null);
      qc.invalidateQueries({ queryKey: ["rewards"] });
      qc.invalidateQueries({ queryKey: ["my-requests"] });
      qc.invalidateQueries({ queryKey: ["points"] });
    },
    onError: (e) => setMsg({ text: e instanceof Error ? e.message : "خطا", ok: false }),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="کاتالوگ پاداش" subtitle="پاداش‌های تجربه‌ساز: کارگاه، بازدید، منتورینگ و فرصت ارائه — همهٔ منابع ضروری هرگز پشت شرط امتیاز قرار نمی‌گیرند." />
      {msg && <p role="status" className={`rounded-md px-3 py-2 text-sm ${msg.ok ? "bg-ok/10 text-ok" : "bg-bad/10 text-bad"}`}>{msg.text}</p>}
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={() => setOnlyExp(!onlyExp)} aria-pressed={onlyExp}
          className={`rounded-full border px-4 py-2 text-xs transition ${onlyExp ? "border-transparent bg-gradient-to-l from-gold to-[#d3a04a] font-bold text-white shadow-md" : "border-line bg-surface text-ink-soft hover:border-gold/50"}`}>
          🎫 فقط پاداش‌های تجربه‌ساز
        </button>
        <span className="text-[11px] text-ink-soft">تجربه‌ها ارزشمند، قابل‌دسترس و غیرضروری برای تحصیل‌اند — همان مرز آیین‌نامهٔ باشگاه.</span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((r) => (
          <Card key={r.id} className={`flex flex-col gap-2 ${r.kind === "experience" ? "border-gold/30" : ""}`}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="font-bold">{r.title_fa}</p>
              <Chip tone={KIND_LABEL[r.kind]?.tone ?? "neutral"}>{KIND_LABEL[r.kind]?.fa ?? r.kind}</Chip>
            </div>
            <p className="line-clamp-2 text-sm text-ink-soft">{r.description_fa}</p>
            <div className="mt-auto flex items-center justify-between pt-2">
              <p className="text-sm">{Number(r.cost_points) > 0 ? `${formatPoints(r.cost_points)} امتیاز` : "بدون هزینهٔ امتیازی"}</p>
              <Button size="sm" onClick={() => setDetail(r)}>جزئیات و درخواست</Button>
            </div>
          </Card>
        ))}
      </div>

      {detail && createPortal(
        <div role="dialog" aria-modal="true" aria-label={`جزئیات ${detail.title_fa}`} className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setDetail(null)}>
          <Card className="w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold">{detail.title_fa}</h3>
            <p className="mt-1 text-sm text-ink-soft">{detail.description_fa}</p>
            <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
              <dt className="text-ink-soft">هزینهٔ امتیازی:</dt><dd>{formatPoints(detail.cost_points)}</dd>
              <dt className="text-ink-soft">ظرفیت:</dt><dd>{detail.capacity_total === null ? "نامحدود" : `${detail.capacity_total} نفر`}</dd>
              <dt className="text-ink-soft">شیوهٔ تحویل:</dt><dd>{detail.delivery === "in_app" ? "درون سامانه (کد مصرف)" : "خارجی با تأیید ارائه‌دهنده"}</dd>
              <dt className="text-ink-soft">اعتبار:</dt><dd>{detail.validity_fa ?? "—"}</dd>
              <dt className="text-ink-soft">لغو و استرداد:</dt><dd className="col-span-1">{detail.refund_policy_fa}</dd>
            </dl>
            {detail.data_consent_note && <p className="mt-2 rounded-md bg-bg p-2 text-xs text-ink-soft">اشتراک داده: {detail.data_consent_note}</p>}
            {detail.type === "internship_invite" && <p className="mt-2 text-xs text-warn">توجه: دعوت به کارآموزی تضمین پذیرش نیست.</p>}
            <DialogActions onCancel={() => setDetail(null)} confirmLabel={`درخواست با ${formatPoints(detail.cost_points)} امتیاز`}
              onConfirm={() => request.mutate(detail)} loading={request.isPending}
              cancelLabel="انصراف" />
          </Card>
        </div>,
        document.body,
      )}
    </div>
  );
}
