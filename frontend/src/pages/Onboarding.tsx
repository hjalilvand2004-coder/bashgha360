import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, PartyPopper, Map as MapIcon } from "lucide-react";
import { get, post, ApiError } from "../lib/api";
import { Button, Card, Chip, Celebration, PageHeader } from "../components/ui";
import { PATH_LABELS, formatJalali } from "../lib/format";
import { PERSONA_LOCAL, INTEREST_LABELS, MISSION_KIND_LABELS } from "../lib/experience";

type State = {
  completed: boolean;
  persona: string | null;
  persona_label_fa: string | null;
  interests: string[];
  first_mission: { id: string; title_fa: string; description_fa: string; mission_kind: string; output_fa: string; duration_label_fa: string } | null;
  first_mission_joined: boolean;
  first_badge_awarded: boolean;
  personas: { key: string; label_fa: string; tagline_fa: string; icon: string; maps_to: string }[];
  interest_options: { key: string; label_fa: string }[];
};

/** شروع فوری «اولین دستاورد در ۱۵ دقیقه»: انتخاب مسیر → انتخاب علاقه → اولین مأموریت و نشان. */
export default function Onboarding() {
  const qc = useQueryClient();
  const [step, setStep] = useState(1);
  const [persona, setPersona] = useState("");
  const [interests, setInterests] = useState<string[]>([]);
  const [result, setResult] = useState<State | null>(null);
  const [err, setErr] = useState("");
  const { data } = useQuery({ queryKey: ["onboarding"], queryFn: () => get<State>("/club-experience/onboarding") });

  const save = useMutation({
    mutationFn: () => post<{ completed: boolean; first_mission_id: string | null; first_badge_awarded: boolean; mapped_path: string; persona_label_fa: string }>(
      "/club-experience/onboarding", { persona, interests }),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["onboarding"] });
      qc.invalidateQueries({ queryKey: ["badges"] });
      qc.invalidateQueries({ queryKey: ["missions"] });
      setResult({ ...(data as State), completed: true, persona, interests,
        first_badge_awarded: d.first_badge_awarded,
        persona_label_fa: d.persona_label_fa,
        first_mission: (data as State)?.first_mission ?? null });
      setStep(3);
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "ثبت مسیر ناموفق بود"),
  });

  if (data && data.completed && step === 1) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <PageHeader title="مسیر تو در باشگاه" subtitle="هر وقت بخواهی می‌توانی مسیر و علاقه‌هایت را عوض کنی." />
        <Card className="relative overflow-hidden">
          <span aria-hidden className="absolute -left-10 -top-10 size-40 rounded-full bg-accent/15 blur-2xl" />
          <div className="relative flex flex-wrap items-center gap-3">
            <span className="grid size-16 place-items-center rounded-2xl bg-gradient-to-br from-primary to-accent text-3xl text-primary-fg shadow-glow" aria-hidden>
              {PERSONA_LOCAL[data.persona ?? ""]?.icon ?? "🎓"}
            </span>
            <div>
              <p className="text-lg font-extrabold">مسیر فعلی تو: {data.persona_label_fa}</p>
              <p className="text-xs text-ink-soft">علاقه‌ها: {data.interests.map((i) => INTEREST_LABELS[i] ?? i).join("، ") || "—"}</p>
            </div>
            <Button variant="ghost" className="mr-auto" onClick={() => { setStep(1); setResult(null); }}>
              تغییر مسیر و علاقه‌ها
            </Button>
          </div>
          {data.first_mission && (
            <div className="mt-4 rounded-xl border border-line bg-bg p-4">
              <p className="text-sm font-bold">{data.first_mission.title_fa}</p>
              <p className="mt-1 text-xs leading-6 text-ink-soft">{data.first_mission.description_fa}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Chip tone="info">{MISSION_KIND_LABELS[data.first_mission.mission_kind] ?? "مأموریت"}</Chip>
                {data.first_mission.duration_label_fa && <Chip>{data.first_mission.duration_label_fa}</Chip>}
                {data.first_mission_joined && <Chip tone="ok"><Check className="size-3.5" aria-hidden /> پیوستی</Chip>}
                <Link to="/missions"><Button size="sm">مشاهدهٔ مأموریت‌ها</Button></Link>
              </div>
            </div>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <PageHeader title="شروع ۱۵ دقیقه‌ای — اولین دستاوردت را همین امروز بگیر"
        subtitle="سه قدم کوتاه: مسیرت را انتخاب کن، علاقه‌هایت را بگو و اولین مأموریتت را باز کن. هر وقت بخواهی می‌توانی خارج شوی؛ امتیازها هم هیچ اثری روی نمره ندارند." />
      <div className="flex items-center gap-2 text-xs">
        {[["۱", "مسیر"], ["۲", "علاقه"], ["۳", "اولین دستاورد"]].map(([n, label], i) => (
          <div key={n} className="flex items-center gap-2">
            <span className={`step-dot ${step > i ? "done" : step === i + 1 ? "" : "!bg-line !shadow-none"}`} aria-hidden>{step > i + 1 ? "✓" : n}</span>
            <span className={step > i ? "font-bold" : "text-ink-soft"}>{label}</span>
            {i < 2 && <span className="mx-1 h-px w-8 bg-line" aria-hidden />}
          </div>
        ))}
      </div>

      {step === 1 && (
        <Card className="animate-fade-up">
          <h2 className="mb-1 font-bold">این ترم دوست داری چه تجربه‌ای داشته باشی؟</h2>
          <p className="mb-4 text-xs text-ink-soft">مسیر انتخابی فقط برچسب تجربهٔ توست — امتیاز و سطح همان سه مسیر مصوب (یادگیری، مهارت، همکاری) می‌ماند.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {(data?.personas ?? []).map((p) => (
              <button key={p.key} onClick={() => { setPersona(p.key); setStep(2); }}
                className={`flex items-start gap-3 rounded-xl border p-4 text-right transition-all hover:-translate-y-0.5 ${persona === p.key ? "border-accent bg-accent/5 shadow-glowAccent" : "border-line bg-surface hover:border-accent/40"}`}>
                <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-bg text-2xl" aria-hidden>{p.icon}</span>
                <span>
                  <span className="block font-bold">{p.label_fa}</span>
                  <span className="mt-0.5 block text-xs leading-5 text-ink-soft">{p.tagline_fa}</span>
                </span>
              </button>
            ))}
          </div>
        </Card>
      )}

      {step === 2 && (
        <Card className="animate-fade-up">
          <h2 className="mb-1 font-bold">چه چیزهایی این روزها برایت جذاب است؟</h2>
          <p className="mb-4 text-xs text-ink-soft">تا ۵ مورد — با همین‌ها اولین مأموریت مناسب تو پیشنهاد می‌شود.</p>
          <div className="flex flex-wrap gap-2">
            {(data?.interest_options ?? []).map((o) => (
              <button key={o.key} onClick={() => setInterests((s) => s.includes(o.key) ? s.filter((x) => x !== o.key) : s.length < 5 ? [...s, o.key] : s)}
                className={`rounded-full border px-3.5 py-2 text-xs transition ${interests.includes(o.key) ? "border-transparent bg-gradient-to-l from-primary to-[#31427f] font-bold text-primary-fg shadow-glow" : "border-line bg-surface text-ink-soft hover:border-accent/50"}`}>
                {INTEREST_LABELS[o.key] ?? o.label_fa}
              </button>
            ))}
          </div>
          {err && <p role="alert" className="mt-3 rounded-xl bg-bad/10 px-3 py-2 text-sm text-bad">{err}</p>}
          <div className="mt-5 flex flex-wrap justify-between gap-2">
            <Button variant="ghost" onClick={() => setStep(1)}>بازگشت</Button>
            <Button loading={save.isPending} onClick={() => save.mutate()}>
              ثبت و بازکردن اولین مأموریت
            </Button>
          </div>
        </Card>
      )}

      {step === 3 && result && (
        <Card className="grad-border animate-fade-up rounded-xl text-center">
          {result.first_badge_awarded && <Celebration />}
          <PartyPopper className="mx-auto size-10 animate-wiggle text-gold" aria-hidden />
          <h2 className="mt-2 text-xl font-extrabold">اولین دستاوردت ثبت شد! 🎉</h2>
          <p className="mt-1 text-sm text-ink-soft">مسیر تو: <b>{result.persona_label_fa}</b> — به مسیر «{PATH_LABELS[result.personas.find((p) => p.key === persona)?.maps_to ?? "learning"]}» وصل می‌شود.</p>
          {result.first_badge_awarded && (
            <div className="mx-auto mt-4 max-w-sm rounded-xl border border-gold/30 bg-gold/5 p-4">
              <p className="font-bold text-gold">🏅 نشان «اولین قدم» برای تو صادر شد</p>
              <p className="mt-1 text-xs leading-6 text-ink-soft">یعنی اولین مأموریت خودت را شروع کرده‌ای — مهم‌ترین قدم، همین بود.</p>
            </div>
          )}
          {result.first_mission && (
            <div className="mx-auto mt-4 max-w-md rounded-xl border border-line bg-bg p-4 text-right">
              <div className="flex items-center gap-2">
                <MapIcon className="size-4 text-accent" aria-hidden />
                <p className="text-sm font-bold">{result.first_mission.title_fa}</p>
              </div>
              <p className="mt-1 text-xs leading-6 text-ink-soft">{result.first_mission.description_fa}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Chip tone="info">{MISSION_KIND_LABELS[result.first_mission.mission_kind] ?? "مأموریت"}</Chip>
                {result.first_mission.duration_label_fa && <Chip>{result.first_mission.duration_label_fa}</Chip>}
                {result.first_mission.output_fa && <Chip tone="ok">خروجی: {result.first_mission.output_fa}</Chip>}
              </div>
            </div>
          )}
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <Link to="/missions"><Button>رفتن به مأموریت‌ها</Button></Link>
            <Link to="/badges"><Button variant="ghost">دیدن نشان من</Button></Link>
            <Link to="/showcase"><Button variant="ghost">فضای دستاوردها</Button></Link>
          </div>
          <p className="mt-3 text-[11px] text-ink-soft">تاریخ عضویت در مسیر: {formatJalali(new Date().toISOString(), true)}</p>
        </Card>
      )}
    </div>
  );
}
