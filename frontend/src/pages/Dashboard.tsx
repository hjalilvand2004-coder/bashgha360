import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowLeft, TrendingUp, Wallet } from "lucide-react";
import { get } from "../lib/api";
import { useAuth, hasRole } from "../lib/auth";
import { Button, Card, Chip, ProgressRing, Skeleton, StatCard, stateTone } from "../components/ui";
import { MembershipArt } from "../components/illustrations";
import { MiniChart, type ChartDatum } from "../components/charts";
import { formatPoints, formatJalali, STATE_LABELS } from "../lib/format";
import { PROMISES } from "../lib/student_life";

type Summary = { available: string; pending: string; reserved: string; cumulative_progress: string; spent_total: string; expired_total: string };
type TierPath = { path: string; progress: number; tiers: { level_no: number; title_fa: string; min_progress: number; achieved: boolean }[] };
type Membership = { state: string | null; membership_no?: string; joined_at?: string };
type HomeFeed = {
  suggestions: {
    opportunities: { id: string; title_fa: string; starts_at: string; location_fa: string; cost_label_fa: string; is_free: boolean; prereq_fa: string; seats_left: number }[];
    peer_activities: { id: string; title_fa: string; time_label_fa: string; location_fa: string; seats_left: number }[];
    bundles: { id: string; title_fa: string; output_fa: string; seats_left: number }[];
  };
  in_progress: {
    peer: { activity_id: string; title_fa: string; time_label_fa: string }[];
    bundles: { bundle_id: string; title_fa: string; steps_done: number[]; total_steps: number }[];
    opportunities: { opportunity_id: string; title_fa: string; my_state: string }[];
  };
};

/** خانهٔ باشگاه v1.5 — به‌جای شروع با امتیاز: «امروز دوست داری چه کار کنی؟» (ارزیابی §۵)
 * امتیاز و نشان به بخش «پیشرفت و مزایا» منتقل شده‌اند؛ اعلان‌ها خبر فرصت می‌دهند، نه احساس عقب‌ماندن. */
export default function Dashboard() {
  const { me } = useAuth();
  const isStudent = !!me?.student_ref_id;
  const { data: summary } = useQuery({ queryKey: ["points"], queryFn: () => get<Summary>("/points/summary"), enabled: isStudent });
  const { data: tiers } = useQuery({ queryKey: ["tiers"], queryFn: () => get<{ paths: TierPath[] }>("/tiers/me"), enabled: isStudent });
  const { data: membership } = useQuery({ queryKey: ["membership-me"], queryFn: () => get<Membership>("/memberships/me"), enabled: isStudent });
  const { data: requests } = useQuery({ queryKey: ["my-requests"], queryFn: () => get<{ items: { id: string; reward_title_fa: string; state: string; requested_at: string }[] }>("/reward-requests"), enabled: isStudent });
  const { data: sys } = useQuery({ queryKey: ["sys"], queryFn: () => get<{ integration_mode: string; seed_label: string }>("/system/info") });
  const { data: onb } = useQuery({
    queryKey: ["onboarding"], queryFn: () => get<{ completed: boolean; first_badge_awarded: boolean; persona_label_fa: string | null }>("/club-experience/onboarding"),
    enabled: isStudent,
  });
  const { data: feed } = useQuery({
    queryKey: ["home-feed"], queryFn: () => get<HomeFeed>("/student-life/home"),
    enabled: isStudent && !!membership?.state,
  });

  const learning = tiers?.paths.find((p) => p.path === "learning");
  const nextTier = learning?.tiers.find((t) => !t.achieved && t.min_progress >= (learning.progress ?? 0)) ?? learning?.tiers.at(-1);
  const chart: ChartDatum[] = [
    { label: "قابل مصرف", value: Number(summary?.available ?? 0) },
    { label: "در انتظار", value: Number(summary?.pending ?? 0) },
    { label: "رزروشده", value: Number(summary?.reserved ?? 0) },
    { label: "مصرف‌شده", value: Number(summary?.spent_total ?? 0) },
  ];
  const suggestions = feed?.suggestions;
  const inProgress = feed?.in_progress;
  const started = (inProgress?.peer.length ?? 0) + (inProgress?.bundles.length ?? 0) + (inProgress?.opportunities.length ?? 0);
  const admin = hasRole(me, "club_manager") || hasRole(me, "policy_officer") || hasRole(me, "auditor");

  return (
    <div className="space-y-6">
      {/* هیروی وعده‌محور */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-bl from-primary via-[#2b3a78] to-[#155e63] p-6 text-primary-fg shadow-lg">
        <span aria-hidden className="pointer-events-none absolute -left-14 -top-14 size-48 rounded-full bg-accent/25 blur-3xl" />
        <span aria-hidden className="pointer-events-none absolute -bottom-16 right-10 size-56 rounded-full bg-white/10 blur-3xl" />
        <div className="relative">
          <p className="text-xs opacity-75">سلام {me?.display_name ?? ""} 👋</p>
          <h1 className="text-shine mt-1 text-2xl font-extrabold md:text-3xl">امروز دوست داری چه کار کنی؟</h1>
          <p className="mt-1.5 max-w-lg text-xs leading-6 opacity-80">اینجا جای «فعالیت نکردی» نیست؛ چهار وعدهٔ ما این است — هر وقت خواستی، هر کدام را که خواستی.</p>
          {sys?.seed_label === "demo" && <span className="mt-2 inline-block rounded-full border border-white/25 bg-white/10 px-3 py-1 text-[11px]">دادهٔ نمونه — محیط آزمایشی</span>}
        </div>
      </div>

      {!isStudent && admin && (
        <Card>
          <p className="text-sm">شما با نقش مدیریتی وارد شده‌اید. از منوی کنار، «نمای کلی باشگاه»، «سیاست‌ها» و گزارش‌ها در دسترس است.</p>
        </Card>
      )}

      {/* چهار وعدهٔ محصول */}
      {isStudent && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {PROMISES.map((q) => (
            <Link key={q.to} to={q.to}
              className={`group flex flex-col gap-3 rounded-xl bg-gradient-to-bl ${q.grad} p-4 text-white ${q.shadow} transition-all duration-300 hover:-translate-y-1 hover:shadow-lg`}>
              <span aria-hidden className="text-3xl transition-transform duration-300 group-hover:scale-110 group-hover:animate-wiggle">{q.icon}</span>
              <span>
                <span className="block text-base font-extrabold">{q.title}</span>
                <span className="mt-0.5 block text-[11px] leading-5 opacity-85">{q.say}</span>
              </span>
            </Link>
          ))}
        </div>
      )}

      {isStudent && !membership?.state && (
        <Card className="border-accent/40 bg-accent/5">
          <p className="text-sm font-bold">هنوز عضو باشگاه نشده‌اید.</p>
          <p className="mt-1 text-sm text-ink-soft">عضویت داوطلبانه است و خدمات پایهٔ آموزشی شما بدون آن کامل می‌ماند.</p>
          <Link to="/join"><Button className="mt-3">مشاهدهٔ شرایط و عضویت</Button></Link>
        </Card>
      )}

      {isStudent && membership?.state && onb && !onb.completed && (
        <Card className="relative overflow-hidden border-gold/40 bg-gradient-to-bl from-gold/10 to-transparent">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-bold">⏱ شروع ۱۵ دقیقه‌ای: اولین تجربه‌ات را همین امروز بگیر</p>
              <p className="mt-1 text-xs leading-6 text-ink-soft">
                سه دقیقه وقت بگذار، علاقه‌ات را انتخاب کن — می‌توانی یک جمع کوچک پیدا کنی، یک برنامهٔ رایگان ببینی یا اولین نمونه‌کارت را بسازی.
              </p>
            </div>
            <Link to="/onboarding"><Button>شروع کن</Button></Link>
          </div>
        </Card>
      )}
      {isStudent && onb?.completed && (
        <Card className="border-accent/30 bg-accent/5">
          <p className="text-sm">مسیر فعلی تو: <b>{onb.persona_label_fa}</b> — هر وقت بخواهی می‌توانی از <Link className="text-accent underline" to="/onboarding">اینجا</Link> عوضش کنی.</p>
        </Card>
      )}

      {/* سه پیشنهاد مناسب همین هفته */}
      {isStudent && membership?.state && (
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-extrabold">✨ سه پیشنهاد مناسب همین هفته</p>
            <Link to="/week" className="text-xs text-accent">همین هفته در دانشگاه ←</Link>
          </div>
          {suggestions ? (
            suggestions.opportunities.length + suggestions.peer_activities.length + suggestions.bundles.length === 0 ? (
              <p className="py-4 text-center text-sm text-ink-soft">فعلاً پیشنهاد تازه‌ای نیست — خودت می‌توانی یک جمع میزبانی کنی یا ایده‌ات را پیشنهاد بدهی.</p>
            ) : (
              <div className="grid gap-3 md:grid-cols-3">
                {suggestions.opportunities.slice(0, 1).map((o) => (
                  <Link key={`o-${o.id}`} to="/week" className="group rounded-xl border border-line p-3 transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md">
                    <p className="text-[11px] text-violet">🎪 همین هفته</p>
                    <p className="mt-1 text-sm font-bold leading-6">{o.title_fa}</p>
                    <p className="mt-1 text-[11px] text-ink-soft">📍 {o.location_fa} · {o.is_free ? "رایگان" : o.cost_label_fa} · پیش‌نیاز: {o.prereq_fa || "هیچ"}</p>
                    <p className="mt-1 text-[11px] text-ok">{o.seats_left > 0 ? `هنوز ظرفیت هست (${o.seats_left.toLocaleString("fa-IR")} جا)` : "در صف انتظار قرار بگیر"}</p>
                  </Link>
                ))}
                {suggestions.peer_activities.slice(0, 1).map((a) => (
                  <Link key={`a-${a.id}`} to="/peers" className="group rounded-xl border border-line p-3 transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md">
                    <p className="text-[11px] text-accent">🧑‍🤝‍🧑 همراه پیدا کن</p>
                    <p className="mt-1 text-sm font-bold leading-6">{a.title_fa}</p>
                    <p className="mt-1 text-[11px] text-ink-soft">🕐 {a.time_label_fa} · 📍 {a.location_fa}</p>
                    <p className="mt-1 text-[11px] text-ok">{a.seats_left > 0 ? `${a.seats_left.toLocaleString("fa-IR")} جای خالی · شرکت آزمایشی ✓` : "ظرفیت پر"}</p>
                  </Link>
                ))}
                {suggestions.bundles.slice(0, 1).map((b) => (
                  <Link key={`b-${b.id}`} to="/bundles" className="group rounded-xl border border-line p-3 transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md">
                    <p className="text-[11px] text-gold">🛠️ چیزی بسازم</p>
                    <p className="mt-1 text-sm font-bold leading-6">{b.title_fa}</p>
                    <p className="mt-1 text-[11px] text-ink-soft">خروجی: {b.output_fa}</p>
                    <p className="mt-1 text-[11px] text-ok">{b.seats_left > 0 ? `${b.seats_left.toLocaleString("fa-IR")} جای خالی` : "ظرفیت پر"}</p>
                  </Link>
                ))}
              </div>
            )
          ) : <Skeleton className="h-28" />}
        </Card>
      )}

      {/* فعالیت‌های در جریان + میان‌برها */}
      {isStudent && membership?.state && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <p className="mb-2 text-sm font-extrabold">🌱 فعالیتی که شروع کرده‌ای</p>
            {started > 0 ? (
              <ul className="space-y-2">
                {inProgress?.bundles.map((b) => (
                  <li key={`b-${b.bundle_id}`}>
                    <Link to="/bundles" className="flex items-center justify-between rounded-xl border border-line px-3 py-2.5 text-sm transition-colors hover:border-accent/50">
                      <span className="min-w-0 truncate">{b.title_fa}</span>
                      <Chip tone="info">{b.steps_done.length.toLocaleString("fa-IR")} از {b.total_steps.toLocaleString("fa-IR")} قدم</Chip>
                    </Link>
                  </li>
                ))}
                {inProgress?.peer.map((a) => (
                  <li key={`a-${a.activity_id}`}>
                    <Link to="/peers" className="flex items-center justify-between rounded-xl border border-line px-3 py-2.5 text-sm transition-colors hover:border-accent/50">
                      <span className="min-w-0 truncate">{a.title_fa}</span>
                      <Chip tone="ok">{a.time_label_fa}</Chip>
                    </Link>
                  </li>
                ))}
                {inProgress?.opportunities.map((o) => (
                  <li key={`o-${o.opportunity_id}`}>
                    <Link to="/week" className="flex items-center justify-between rounded-xl border border-line px-3 py-2.5 text-sm transition-colors hover:border-accent/50">
                      <span className="min-w-0 truncate">{o.title_fa}</span>
                      <Chip tone={o.my_state === "waitlisted" ? "warn" : "ok"}>{o.my_state === "waitlisted" ? "در صف" : "ثبت‌نام شدی"}</Chip>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-3 text-sm leading-7 text-ink-soft">
                هنوز چیزی را شروع نکرده‌ای — <Link className="text-accent underline" to="/peers">همراه یا جمع کوچک پیدا کن</Link> یا <Link className="text-accent underline" to="/voice">ایدهٔ خودت را پیشنهاد بده</Link>.
              </p>
            )}
          </Card>
          <Card>
            <p className="mb-2 text-sm font-extrabold">🧳 نمونه‌کارها و تجربه‌های من</p>
            <p className="text-xs leading-6 text-ink-soft">آنچه ساخته‌ای، تجربه‌هایی که داشتی و رضایت‌های ثبت‌شده — قابل جمع‌شدن در یک صفحه.</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <Link to="/showcase" className="rounded-xl border border-line px-3 py-2.5 text-sm transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md">🏆 فضای دستاوردها</Link>
              <Link to="/bundles" className="rounded-xl border border-line px-3 py-2.5 text-sm transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md">🛠️ بسته‌های ساخت</Link>
              <Link to="/missions" className="rounded-xl border border-line px-3 py-2.5 text-sm transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md">🚩 مأموریت‌ها</Link>
              <Link to="/voice" className="rounded-xl border border-line px-3 py-2.5 text-sm transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md">📣 ایدهٔ خودت</Link>
            </div>
            <p className="mt-3 text-[11px] leading-5 text-ink-soft">اعلان‌ها همیشه خبرِ فرصت می‌دهند — مثلاً: «برای بازدید پنجشنبه هنوز ظرفیت هست.»</p>
          </Card>
        </div>
      )}

      {/* پیشرفت و مزایا — امتیاز زیرساخت پشتیبان است، نه مرکز تجربه */}
      {isStudent && membership?.state && (
        <section aria-labelledby="progress-heading">
          <h2 id="progress-heading" className="mb-3 text-sm font-extrabold text-ink-soft">— پیشرفت و مزایا (زیرساخت پشتیبان)</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <p className="mb-1 text-xs text-ink-soft">کارت عضویت دیجیتال</p>
              <div className="rounded-lg bg-gradient-to-l from-primary to-[#2c3d7a] p-4 text-primary-fg shadow-md">
                <MembershipArt className="mb-2 w-full opacity-70" />
                <p className="text-sm font-extrabold">{me?.display_name}</p>
                <p className="mt-1 text-[11px] opacity-80" dir="ltr">{membership?.membership_no ?? "—"}</p>
                {membership?.state && <Chip tone="gold">{STATE_LABELS[membership.state] ?? membership.state}</Chip>}
              </div>
              {membership?.joined_at && <p className="mt-3 text-xs text-ink-soft">عضو از {formatJalali(membership.joined_at)}</p>}
            </Card>

            <Card>
              <p className="mb-2 text-xs text-ink-soft">دو مفهوم مستقل — مصرف پاداش، پیشرفت شما را کم نمی‌کند</p>
              <div className="grid gap-3">
                {summary ? (
                  <>
                    <StatCard title="امتیاز قابل مصرف (پاداش)" value={formatPoints(summary.available)} icon={<Wallet className="size-5" />} hue="accent"
                      hint={`در انتظار تأیید: ${formatPoints(summary.pending)} · رزروشده: ${formatPoints(summary.reserved)}`} />
                    <StatCard title="پیشرفت تجمعی تأییدشده (سطح و نشان)" value={formatPoints(summary.cumulative_progress)} icon={<TrendingUp className="size-5" />} hue="gold"
                      hint={`مصرف‌شده تا امروز: ${formatPoints(summary.spent_total)}`} />
                  </>
                ) : <Skeleton className="h-24" />}
              </div>
            </Card>

            <Card>
              <div className="mb-2 flex items-center gap-3">
                {learning && (
                  <ProgressRing value={Number(learning.progress ?? 0)} max={nextTier?.min_progress ?? Math.max(1, Number(learning.progress ?? 0))} size={64} stroke={7}
                    label="پیشرفت مسیر یادگیری">
                    <span className="text-xs font-extrabold text-accent">{Math.min(100, Math.round((Number(learning.progress ?? 0) / Math.max(1, nextTier?.min_progress ?? 1)) * 100))}٪</span>
                  </ProgressRing>
                )}
                <div>
                  <p className="text-sm font-bold">مسیر سطح</p>
                  {learning && <p className="text-xs text-ink-soft">{nextTier ? `تا «${nextTier.title_fa}»: ${formatPoints(Math.max(0, nextTier.min_progress - Number(learning.progress)))}` : "بالاترین سطح 🎉"}</p>}
                </div>
              </div>
              <Link to="/badges" className="inline-block text-sm font-medium text-accent">سطوح و نشان‌ها ←</Link>
            </Card>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <MiniChart title="ترکیب حساب امتیاز شما" data={chart} tableCaption="ترکیب حساب امتیاز" />
            <Card>
              <p className="mb-2 text-sm font-bold">آخرین درخواست‌های پاداش</p>
              {requests?.items?.length ? (
                <ul className="space-y-2">
                  {requests.items.slice(0, 4).map((r) => (
                    <li key={r.id} className="flex items-center justify-between rounded-md border border-line px-3 py-2.5 text-sm">
                      <span>{r.reward_title_fa}</span>
                      <Chip tone={stateTone(r.state)}>{STATE_LABELS[r.state] ?? r.state}</Chip>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="py-4 text-center text-sm text-ink-soft">هنوز درخواست پاداشی ثبت نکرده‌اید — از <Link className="text-accent underline" to="/rewards">کاتالوگ پاداش</Link> شروع کنید.</p>
              )}
            </Card>
          </div>
        </section>
      )}

      {isStudent && membership?.state && (
        <p className="flex items-center justify-center gap-1 text-center text-[11px] text-ink-soft">
          پیشنهاد می‌کنی چیزی را تغییر دهیم؟ <Link className="text-accent underline" to="/voice">صدای دانشجو</Link> <ArrowLeft className="size-3" />
        </p>
      )}
    </div>
  );
}
