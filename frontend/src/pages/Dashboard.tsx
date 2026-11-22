import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { get } from "../lib/api";
import { useAuth, hasRole } from "../lib/auth";
import { Button, Card, Chip, Skeleton, StatCard, stateTone } from "../components/ui";
import { MembershipArt } from "../components/illustrations";
import { MiniChart, type ChartDatum } from "../components/charts";
import { formatPoints, formatJalali, STATE_LABELS } from "../lib/format";

type Summary = { available: string; pending: string; reserved: string; cumulative_progress: string; spent_total: string; expired_total: string };
type TierPath = { path: string; progress: number; tiers: { level_no: number; title_fa: string; min_progress: number; achieved: boolean }[] };
type Membership = { state: string | null; membership_no?: string; joined_at?: string };

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

  const learning = tiers?.paths.find((p) => p.path === "learning");
  const nextTier = learning?.tiers.find((t) => !t.achieved && t.min_progress >= (learning.progress ?? 0)) ?? learning?.tiers.at(-1);
  const chart: ChartDatum[] = [
    { label: "قابل مصرف", value: Number(summary?.available ?? 0) },
    { label: "در انتظار", value: Number(summary?.pending ?? 0) },
    { label: "رزروشده", value: Number(summary?.reserved ?? 0) },
    { label: "مصرف‌شده", value: Number(summary?.spent_total ?? 0) },
  ];

  const admin = hasRole(me, "club_manager") || hasRole(me, "policy_officer") || hasRole(me, "auditor");

  return (
    <div className="space-y-5">
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-bl from-primary via-[#2b3a78] to-[#155e63] p-6 text-primary-fg shadow-lg">
        <span aria-hidden className="pointer-events-none absolute -left-14 -top-14 size-48 rounded-full bg-accent/25 blur-3xl" />
        <span aria-hidden className="pointer-events-none absolute -bottom-16 right-10 size-56 rounded-full bg-white/10 blur-3xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs opacity-75">داشبورد باشگاه</p>
            <h1 className="mt-1 text-2xl font-extrabold">سلام {me?.display_name ?? ""} 👋</h1>
            <p className="mt-1.5 max-w-md text-xs leading-6 opacity-80">پیشرفت فردی شما نسبت به خط پایهٔ خودتان — نه مقایسه با دیگران.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {isStudent && summary && (
              <>
                <div className="rounded-xl bg-white/12 px-4 py-2.5 text-center backdrop-blur">
                  <p className="text-[10px] opacity-80">امتیاز قابل مصرف</p>
                  <p className="text-lg font-extrabold">{formatPoints(summary.available)}</p>
                </div>
                <div className="rounded-xl bg-white/12 px-4 py-2.5 text-center backdrop-blur">
                  <p className="text-[10px] opacity-80">پیشرفت تجمعی</p>
                  <p className="text-lg font-extrabold">{formatPoints(summary.cumulative_progress)}</p>
                </div>
              </>
            )}
            {sys?.seed_label === "demo" && <span className="rounded-full border border-white/25 bg-white/10 px-3 py-1.5 text-[11px]">دادهٔ نمونه — محیط آزمایشی</span>}
          </div>
        </div>
      </div>

      {!isStudent && admin && (
        <Card>
          <p className="text-sm">شما با نقش مدیریتی وارد شده‌اید. از منوی کنار، «نمای کلی باشگاه»، «سیاست‌ها» و گزارش‌ها در دسترس است.</p>
        </Card>
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
              <p className="font-bold">⏱ شروع ۱۵ دقیقه‌ای: اولین دستاوردت را همین امروز بگیر</p>
              <p className="mt-1 text-xs leading-6 text-ink-soft">
                سه دقیقه وقت بگذار، علاقه‌ات را انتخاب کن و مأموریت شروع را باز کن — نشان «اولین قدم» بلافاصله صادر می‌شود.
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

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-1">
          <p className="mb-1 text-xs text-ink-soft">کارت عضویت دیجیتال</p>
          <div className="rounded-lg bg-gradient-to-l from-primary to-[#2c3d7a] p-4 text-primary-fg shadow-md">
            <MembershipArt className="mb-2 w-full opacity-70" />
            <p className="text-sm font-extrabold">{me?.display_name}</p>
            <p className="mt-1 text-[11px] opacity-80" dir="ltr">{membership?.membership_no ?? "—"}</p>
            {membership?.state && <Chip tone="gold">{STATE_LABELS[membership.state] ?? membership.state}</Chip>}
          </div>
        </Card>

        <Card className="md:col-span-2">
          <p className="mb-2 text-xs text-ink-soft">دو مفهوم مستقل — مصرف پاداش، پیشرفت شما را کم نمی‌کند</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {summary ? (
              <>
                <StatCard title="امتیاز قابل مصرف (پاداش)" value={formatPoints(summary.available)}
                  hint={`در انتظار تأیید: ${formatPoints(summary.pending)} · رزروشده: ${formatPoints(summary.reserved)}`} />
                <StatCard title="پیشرفت تجمعی تأییدشده (سطح و نشان)" value={formatPoints(summary.cumulative_progress)} tone="gold"
                  hint={`مصرف‌شده تا امروز: ${formatPoints(summary.spent_total)}`} />
              </>
            ) : <Skeleton className="h-24" />}
          </div>
          {membership?.joined_at && <p className="mt-3 text-xs text-ink-soft">عضو از {formatJalali(membership.joined_at)}</p>}
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <MiniChart title="ترکیب حساب امتیاز شما" data={chart} tableCaption="ترکیب حساب امتیاز" />
        <Card>
          <p className="mb-2 text-sm font-bold">مسیر سطح (استمرار یادگیری)</p>
          {learning ? (
            <>
              <div className="mb-2 flex items-center justify-between text-xs text-ink-soft">
                <span>پیشرفت: {formatPoints(learning.progress)}</span>
                <span>{nextTier ? `تا سطح «${nextTier.title_fa}»: ${formatPoints(Math.max(0, nextTier.min_progress - Number(learning.progress)))}` : "بالاترین سطح"}</span>
              </div>
              <ol className="mt-3 space-y-2">
                {learning.tiers.map((t) => (
                  <li key={t.level_no} className="flex items-center justify-between rounded-md border border-line px-3 py-2 text-sm">
                    <span>سطح {t.level_no} — {t.title_fa}</span>
                    {t.achieved ? <Chip tone="ok">کسب‌شده</Chip> : <Chip>از {formatPoints(t.min_progress)}</Chip>}
                  </li>
                ))}
              </ol>
            </>
          ) : <Skeleton className="h-28" />}
          <Link to="/badges" className="mt-3 inline-block text-sm font-medium text-accent">سطوح و نشان‌ها ←</Link>
        </Card>
      </div>

      {isStudent && (
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
            <p className="py-4 text-center text-sm text-ink-soft">هنوز درخواست پاداشی ثبت نکرده‌اید — از «کاتالوگ پاداش» شروع کنید.</p>
          )}
        </Card>
      )}
    </div>
  );
}
