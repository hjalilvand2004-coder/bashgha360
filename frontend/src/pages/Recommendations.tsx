import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { get, post } from "../lib/api";
import { Button, Card, Chip, PageHeader } from "../components/ui";
import { formatPoints } from "../lib/format";

type Rec = { run_id: string; basis: string; items: { reward_id: string; title_fa: string; type: string; cost_points: string; score: number; reasons_fa: string[]; rank: number }[] };

export default function Recommendations() {
  const qc = useQueryClient();
  const [fb, setFb] = useState("");
  const { data, isLoading } = useQuery({ queryKey: ["recs"], queryFn: () => get<Rec>("/recommendations") });

  const send = useMutation({
    mutationFn: (p: { item_id: string; feedback: string }) => post("/recommendations/feedback", p),
    onSuccess: () => setFb("بازخورد شما ثبت شد و به بهبود پیشنهادها کمک می‌کند."),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="پیشنهادهای پاداش"
        subtitle={data?.basis === "consent_personal"
          ? "پیشنهادهای شخصی بر اساس هدف اعلامی و رضایت شخصی‌سازی شما"
          : "پیشنهادهای عمومی — برای پیشنهاد شخصی، رضایت شخصی‌سازی را در حریم خصوصی فعال کنید"} />
      {fb && <p role="status" className="rounded-md bg-ok/10 px-3 py-2 text-sm text-ok">{fb}</p>}
      {isLoading && <Card className="text-sm text-ink-soft">در حال محاسبهٔ پیشنهادها…</Card>}
      <div className="grid gap-4 md:grid-cols-2">
        {data?.items.map((it, idx) => (
          <Card key={idx}>
            <div className="flex items-start justify-between gap-2">
              <p className="font-bold">{it.title_fa}</p>
              <Chip tone="info">{formatPoints(it.cost_points)} امتیاز</Chip>
            </div>
            {/* دلیل‌ها از محاسبهٔ واقعی توصیه‌گر تولید شده‌اند — نه متن ساختگی */}
            <ul className="mt-2 space-y-1 text-xs text-ink-soft">
              {it.reasons_fa.map((r, i) => <li key={i}>• {r}</li>)}
            </ul>
            <div className="mt-3 flex gap-2">
              <Button size="sm" variant="ghost" onClick={() => send.mutate({ item_id: `${data.run_id}:${it.reward_id}`, feedback: "like" })}>مفید بود</Button>
              <Button size="sm" variant="ghost" onClick={() => send.mutate({ item_id: `${data.run_id}:${it.reward_id}`, feedback: "not_now" })}>الان نه</Button>
              <Button size="sm" variant="ghost" onClick={() => send.mutate({ item_id: `${data.run_id}:${it.reward_id}`, feedback: "dismiss" })}>نمایش نده</Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
