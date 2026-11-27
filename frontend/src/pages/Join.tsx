import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { get, post } from "../lib/api";
import { Button, Card, Chip, PageHeader } from "../components/ui";
import { formatJalali } from "../lib/format";
import { PITCH } from "../lib/experience";

type Terms = { id: string; version_no: number; title_fa: string; content_fa: string; data_policy_fa: string };
type ConsentMap = Record<string, { value: boolean; decided_at: string } | null>;

const CONSENT_ITEMS = [
  { key: "personalization", label: "پیشنهادهای شخصی‌سازی‌شده", hint: "برای پیشنهاد پاداش متناسب با هدف شما. بدون این رضایت، پیشنهادهای عمومی ارائه می‌شود." },
  { key: "public_badge", label: "نمایش عمومی نشان‌ها", hint: "امکان ساخت لینک عمومیِ لغوشدنی برای نشان‌ها. در هر لحظه قابل لغو است." },
  { key: "notifications", label: "اعلان‌های باشگاه", hint: "اعلان‌های اختیاری؛ اعلان‌های تراکنشی حقوقی همیشه ارسال می‌شوند." },
] as const;

export default function Join() {
  const qc = useQueryClient();
  const nav = useNavigate();
  const [consents, setConsents] = useState<Record<string, boolean>>({ personalization: false, public_badge: false, notifications: true });
  const [goalType, setGoalType] = useState("skill");
  const [err, setErr] = useState("");
  const { data: terms } = useQuery({ queryKey: ["terms"], queryFn: () => get<Terms>("/memberships/terms") });
  const { data: my } = useQuery({ queryKey: ["membership-me"], queryFn: () => get<{ state: string | null; membership_no?: string; consents?: ConsentMap }>("/memberships/me") });

  const join = useMutation({
    mutationFn: () => post<{ state: string; membership_no: string }>("/memberships/join", {
      terms_version_id: terms?.id, consents,
    }),
    onSuccess: async () => {
      await post("/goals", { goal_type: goalType, title_fa: document.getElementById("goal-title") ? (document.getElementById("goal-title") as HTMLInputElement).value : "هدف من در باشگاه" }).catch(() => undefined);
      await qc.invalidateQueries();
      nav("/onboarding"); // سه دقیقه وقت بگذار، علاقه‌ات را انتخاب کن و مأموریت شروع را باز کن
    },
    onError: (e) => setErr(e instanceof Error ? e.message : "عضویت ناموفق بود"),
  });

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="عضویت در باشگاه" subtitle="مشارکت کاملاً داوطلبانه است؛ عدم عضویت هیچ خدمات پایهٔ آموزشی را محدود نمی‌کند."
        badge={my?.state && my.state !== "draft" ? undefined : undefined} />

      {/* پیام معرفی تجربه‌محور — پنل شبِ Aurora در هر دو تم (v1.6) */}
      <div className="mb-5 rounded-xl bg-gradient-to-bl from-[#0f0c29] via-[#2a1f5c] to-[#7c3aed] p-6 text-white shadow-lg">
        <p className="text-xs opacity-80">چیزی که بلدی، چیزی که دوست داری یاد بگیری، و کاری که می‌توانی با دیگران بسازی — همه‌اش می‌تواند بخشی از تجربهٔ تو در باشگاه باشد.</p>
        <p className="mt-2 text-lg font-extrabold">در باشگاه۳۶۰ مأموریت‌های کوتاه را امتحان می‌کنی، با هم‌علاقه‌ها همکاری می‌کنی و دستاوردهای واقعی‌ات را ثبت می‌کنی.</p>
        <p className="mt-2 text-xs leading-6 opacity-80">عضویت داوطلبانه است؛ امتیازها روی نمره و وضعیت تحصیلی‌ات اثری ندارند و هر وقت بخواهی می‌توانی خارج شوی.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {PITCH.map((p) => (
            <div key={p.title} className="rounded-xl bg-white/12 p-3 backdrop-blur">
              <p className="text-lg" aria-hidden>{p.icon}</p>
              <p className="mt-1 text-sm font-bold">{p.title}</p>
              <p className="mt-1 text-[11px] leading-5 opacity-75">{p.body}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 rounded-xl border border-white/25 bg-white/10 p-3 text-[11px] leading-6">
          🎪 <b>رویداد آغازین:</b> جلسهٔ کوتاه و تعاملی معرفی باشگاه — به‌جای توضیح، همان‌جا یک مأموریت کوچک را تجربه می‌کنی، با چند عضو آشنا می‌شوی و در پایان نشان «اولین قدم» را می‌گیری. عضویت بلندمدت در آن لازم نیست.
        </p>
      </div>

      {my?.state && my.state !== "draft" && (
        <Card className="mb-4 border-ok/30 bg-ok/5">
          <p className="text-sm">وضعیت فعلی عضویت شما: <b>فعال</b> — شمارهٔ عضویت: <code dir="ltr">{my.membership_no}</code></p>
        </Card>
      )}
      <Card className="mb-4">
        <div className="mb-2 flex items-center gap-2">
          <h2 className="font-bold">{terms?.title_fa ?? "شرایط عضویت"}</h2>
          <Chip>نسخهٔ {terms?.version_no ? terms.version_no : "—"}</Chip>
        </div>
        <p className="whitespace-pre-line text-sm leading-7 text-ink-soft">{terms?.content_fa}</p>
        <p className="mt-3 whitespace-pre-line rounded-md bg-bg p-3 text-xs leading-6 text-ink-soft">{terms?.data_policy_fa}</p>
      </Card>

      <Card className="mb-4">
        <h2 className="mb-3 font-bold">رضایت‌های جداگانه (قابل لغو در هر زمان)</h2>
        <ul className="space-y-3">
          {CONSENT_ITEMS.map((c) => (
            <li key={c.key} className="flex items-start gap-3 rounded-md border border-line p-3">
              <input id={`c-${c.key}`} type="checkbox" checked={!!consents[c.key]}
                onChange={(e) => setConsents({ ...consents, [c.key]: e.target.checked })}
                className="mt-1 size-5 accent-[var(--c-accent)]" />
              <div>
                <label htmlFor={`c-${c.key}`} className="text-sm font-medium">{c.label}</label>
                <p className="mt-0.5 text-xs text-ink-soft">{c.hint}</p>
                {my?.consents?.[c.key] && (
                  <p className="mt-1 text-[11px] text-ink-soft">آخرین تصمیم ثبت‌شده: {my.consents[c.key]!.value ? "پذیرش" : "لغو"} در {formatJalali(my.consents[c.key]!.decided_at, true)}</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="mb-4">
        <h2 className="mb-3 font-bold">هدف شما در باشگاه چیست؟</h2>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
          {[["skill", "رشد مهارت"], ["exam_prep", "آمادگی امتحان"], ["weakness", "رفع ضعف"], ["collaboration", "همکاری"], ["other", "هدف دیگر"]].map(([k, label]) => (
            <label key={k} className={`flex min-h-11 cursor-pointer items-center justify-center rounded-md border px-3 text-sm ${goalType === k ? "border-accent bg-accent/10 font-bold text-accent" : "border-line bg-surface"}`}>
              <input type="radio" name="goal" className="sr-only" checked={goalType === k} onChange={() => setGoalType(k)} />
              {label}
            </label>
          ))}
        </div>
        <input id="goal-title" className="mt-3 min-h-11 w-full rounded-md border border-line bg-surface px-3 text-sm" placeholder="مثلاً: تقویت مهارت برنامه‌نویسی وب" />
      </Card>

      {err && <p role="alert" className="mb-3 rounded-md bg-bad/10 px-3 py-2 text-sm text-bad">{err}</p>}
      <Button loading={join.isPending} onClick={() => join.mutate()} className="w-full md:w-auto">
        شرایط را می‌پذیرم و عضو می‌شوم
      </Button>
    </div>
  );
}
