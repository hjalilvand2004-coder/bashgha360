import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, post } from "../lib/api";
import { Button, Card, Chip, PageHeader, Skeleton } from "../components/ui";
import { BadgeIcon } from "../components/illustrations";
import { PATH_LABELS, formatPoints, formatJalali } from "../lib/format";

type TierPath = { path: string; progress: number; tiers: { level_no: number; title_fa: string; min_progress: number; achieved: boolean }[] };
type Badge = { id: string; title_fa: string; svg_id: string; path: string; issuer_fa: string; story_fa: string; issued_at: string; state: string; reason_fa: string | null; share_token: string | null; note: string };

export default function Badges() {
  const qc = useQueryClient();
  const { data: tiers } = useQuery({ queryKey: ["tiers"], queryFn: () => get<{ paths: TierPath[] }>("/tiers/me") });
  const { data: badges } = useQuery({ queryKey: ["badges"], queryFn: () => get<{ items: Badge[] }>("/badges/me") });

  const share = useMutation({
    mutationFn: (badge_award_id: string) => post<{ share_token: string; expires_at: string }>("/badges/share", { badge_award_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["badges"] }),
  });
  const revoke = useMutation({
    mutationFn: (id: string) => post(`/badges/${id}/revoke-share`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["badges"] }),
  });

  return (
    <div className="space-y-5">
      <PageHeader title="سطح و نشان‌ها" subtitle="سه مسیر مستقل: استمرار یادگیری، رشد مهارت، همکاری آموزشی. نشان باشگاه مدرک رسمی مهارت نیست." />

      <div className="grid gap-4 md:grid-cols-3">
        {tiers ? tiers.paths.map((p) => {
          const next = p.tiers.find((t) => !t.achieved);
          return (
            <Card key={p.path}>
              <div className="mb-2 flex items-center justify-between">
                <p className="text-sm font-bold">{PATH_LABELS[p.path]}</p>
                <Chip tone="info">{formatPoints(p.progress)}</Chip>
              </div>
              <ol className="space-y-2">
                {p.tiers.map((t) => (
                  <li key={t.level_no} className="flex items-center justify-between rounded-md border border-line px-3 py-2 text-sm">
                    <span>{t.title_fa}</span>
                    {t.achieved ? <Chip tone="gold">کسب‌شده</Chip> : <Chip>از {formatPoints(t.min_progress)}</Chip>}
                  </li>
                ))}
                {p.tiers.length === 0 && <p className="text-xs text-ink-soft">سطوحی برای این مسیر تعریف نشده است.</p>}
              </ol>
              {next && <p className="mt-2 text-xs text-ink-soft">تا سطح بعدی: {formatPoints(Math.max(0, next.min_progress - Number(p.progress)))} پیشرفت</p>}
            </Card>
          );
        }) : [1, 2, 3].map((i) => <Skeleton key={i} className="h-40" />)}
      </div>

      <section aria-label="نشان‌های من">
        <h2 className="mb-3 text-lg font-bold">نشان‌های من</h2>
        {badges && badges.items.length === 0 && (
          <Card className="text-sm text-ink-soft">هنوز نشانی کسب نکرده‌اید — نشان‌ها بر اساس معیار مصوب و شواهد تأییدشده صادر می‌شوند.</Card>
        )}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {badges?.items.map((b) => (
            <Card key={b.id} className="flex flex-col items-center gap-2 text-center">
              <BadgeIcon svgId={b.svg_id} className="size-16 text-gold" />
              <p className="font-bold">{b.title_fa}</p>
              <p className="text-xs text-ink-soft">{PATH_LABELS[b.path] ?? b.path} · صادرکننده: {b.issuer_fa}</p>
              <p className="text-xs text-ink-soft">صدور: {formatJalali(b.issued_at)}</p>
              {b.story_fa && (
                <p className="rounded-xl border border-gold/25 bg-gold/5 p-3 text-xs leading-6 text-ink-soft">
                  <span className="font-bold text-gold">داستان این نشان: </span>{b.story_fa}
                </p>
              )}
              {b.reason_fa && <Chip tone="bad">{b.reason_fa}</Chip>}
              {b.share_token ? (
                <div className="flex flex-wrap items-center justify-center gap-2">
                  <Chip tone="ok">لینک عمومی فعال</Chip>
                  <Button size="sm" variant="ghost" onClick={() => revoke.mutate(b.id)}>لغو لینک</Button>
                </div>
              ) : (
                <Button size="sm" variant="ghost" loading={share.isPending}
                  onClick={() => share.mutate(b.id)} disabled={b.state !== "valid"}>
                  ساخت لینک عمومی (لغوشدنی)
                </Button>
              )}
              <p className="text-[10px] text-ink-soft">{b.note}</p>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
