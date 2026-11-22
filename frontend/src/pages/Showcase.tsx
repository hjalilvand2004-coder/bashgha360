import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { get } from "../lib/api";
import { Button, Card, Chip, EmptyState, PageHeader, Skeleton } from "../components/ui";
import { formatJalali } from "../lib/format";
import { STORY_KIND_LABELS } from "../lib/experience";

type Story = { id: string; title_fa: string; body_fa: string; kind: string; kind_label_fa: string; subject_label_fa: string; published_at: string };

const KIND_ICON: Record<string, string> = { build: "🛠️", help: "🤝", skill: "🎯", event: "🎪" };
/** رنگ لبهٔ بالای هر روایت بر اساس نوع — تشخیص سریع و ظاهر شاد */
const KIND_BAR: Record<string, string> = {
  build: "bg-gradient-to-l from-violet to-pink",
  help: "bg-gradient-to-l from-accent to-lime",
  skill: "bg-gradient-to-l from-primary to-accent",
  event: "bg-gradient-to-l from-gold to-orange",
};

/** فضای دستاوردها — روایت‌های کوتاه و الهام‌بخش به‌جای جدول رتبه‌بندی؛ فقط با رضایت افراد. */
export default function Showcase() {
  const { data, isLoading } = useQuery({ queryKey: ["showcase"], queryFn: () => get<{ items: Story[] }>("/club-experience/showcase") });

  return (
    <div className="space-y-5">
      <PageHeader title="فضای دستاوردها" icon={<Sparkles className="size-5" />} subtitle="اینجا جای جدول رتبه‌بندی نیست؛ روایتِ کاری که واقعاً انجام شده را می‌خوانید. هر روایت فقط با رضایت صاحبش نمایش داده می‌شود." />

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="grad-border rounded-xl md:col-span-1">
          <span aria-hidden className="icon-bubble bg-gradient-to-br from-accent to-lime shadow-glowAccent animate-bounce-soft"><Sparkles className="size-5" /></span>
          <p className="mt-3 font-bold">داستان بعدی از آنِ توست</p>
          <p className="mt-1 text-xs leading-6 text-ink-soft">یک مأموریت کوتاه را همین هفته امتحان کن؛ خروجی‌ات اگر اجازهٔ بدهی، همین‌جا روایت می‌شود.</p>
          <Link to="/missions"><Button size="sm" className="mt-3">انتخاب مأموریت</Button></Link>
        </Card>

        <div className="md:col-span-2">
          {isLoading && <div className="grid gap-4 sm:grid-cols-2">{[1, 2].map((i) => <Skeleton key={i} className="h-40" />)}</div>}
          {data && data.items.length === 0 && (
            <EmptyState art="medal" title="هنوز روایتی منتشر نشده" body="اولین دستاوردِ ثبت‌شده با رضایت صاحبش، همین‌جا دیده می‌شود." />
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            {data?.items.map((s) => (
              <Card key={s.id} className="animate-fade-up group relative flex flex-col gap-2 overflow-hidden pt-5">
                <span aria-hidden className={`absolute inset-x-0 top-0 h-1.5 ${KIND_BAR[s.kind] ?? "bg-gradient-to-l from-primary to-accent"}`} />
                <div className="flex items-center justify-between gap-2">
                  <span aria-hidden className="grid size-12 place-items-center rounded-2xl bg-bg text-2xl shadow-sm transition-transform duration-300 group-hover:scale-110 group-hover:animate-wiggle">{KIND_ICON[s.kind] ?? "🌟"}</span>
                  <Chip tone="info">{STORY_KIND_LABELS[s.kind] ?? s.kind_label_fa}</Chip>
                </div>
                <p className="font-bold leading-6">{s.title_fa}</p>
                <p className="text-sm leading-6 text-ink-soft">{s.body_fa}</p>
                <div className="mt-auto flex items-center justify-between border-t border-dashed border-line pt-2 text-[11px] text-ink-soft">
                  <span>{s.subject_label_fa}</span>
                  <span>{formatJalali(s.published_at)}</span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
      <p className="text-center text-[11px] text-ink-soft">
        نمایش عمومی دستاورد فقط با رضایت جداگانه انجام می‌شود و در هر لحظه قابل لغو است — هیچ رتبه، ترتیب رقابتی یا مقایسه‌ای بین دانشجوها وجود ندارد.
      </p>
    </div>
  );
}
