import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { get, patch, post } from "../lib/api";
import { Button, Card, Chip, DialogActions, PageHeader } from "../components/ui";
import { formatJalali } from "../lib/format";

type Consent = Record<string, { value: boolean; decided_at: string } | null>;
type Pref = { channels: Record<string, boolean>; quiet_start: string | null; quiet_end: string | null; daily_cap: number; mute_until: string | null };

export default function Privacy() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const { data: my } = useQuery({ queryKey: ["membership-me"], queryFn: () => get<{ state: string | null; consents?: Consent }>("/memberships/me") });
  const { data: prefs } = useQuery({ queryKey: ["notif-prefs"], queryFn: () => get<Pref>("/notifications/preferences") });

  const setConsent = useMutation({
    mutationFn: (p: { type: string; value: boolean }) => patch(`/consents/${p.type}`, { value: p.value }),
    onSuccess: (_d, v) => { setMsg(v.value ? "رضایت ثبت شد و بلافاصله اعمال گردید." : "لغو رضایت انجام شد — اثر واقعی و فوری."); qc.invalidateQueries(); },
  });
  const savePrefs = useMutation({
    mutationFn: (p: Pref) => patch("/notifications/preferences", p),
    onSuccess: () => { setMsg("ترجیحات اعلان ذخیره شد."); qc.invalidateQueries({ queryKey: ["notif-prefs"] }); },
  });
  const exit = useMutation({
    mutationFn: () => post("/memberships/exit", { reason_fa: "خروج داوطلبانه از رابط" }),
    onSuccess: () => { setMsg("از باشگاه خارج شدید. خدمات پایهٔ آموزشی شما دست‌نخورده باقی می‌ماند."); qc.invalidateQueries(); },
  });
  const exportData = useMutation({
    mutationFn: () => get<Record<string, unknown>>("/memberships/export"),
    onSuccess: (d) => {
      const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "bashgah360-personal-data.json";
      a.click();
      setMsg("خروجی اطلاعات شخصی شما دانلود شد.");
    },
  });

  const consentItems = [
    { key: "personalization", label: "شخصی‌سازی پیشنهادها" },
    { key: "public_badge", label: "نمایش عمومی نشان‌ها" },
    { key: "notifications", label: "اعلان‌های اختیاری" },
  ];

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <PageHeader title="حریم خصوصی، اعلان‌ها و خروج" subtitle="منشأ داده، زمان به‌روزرسانی و مسیر اصلاح همیشه قابل مشاهده است." />
      {msg && <p role="status" className="rounded-md bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}

      <Card>
        <h2 className="mb-3 font-bold">رضایت‌های من</h2>
        <ul className="space-y-2">
          {consentItems.map((c) => {
            const cur = my?.consents?.[c.key];
            return (
              <li key={c.key} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-line px-3 py-3">
                <div>
                  <p className="text-sm font-medium">{c.label}</p>
                  {cur && <p className="text-[11px] text-ink-soft">آخرین تصمیم: {cur.value ? "پذیرش" : "لغو"} — {formatJalali(cur.decided_at, true)}</p>}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant={cur?.value ? "ghost" : "accent"} loading={setConsent.isPending} onClick={() => setConsent.mutate({ type: c.key, value: true })}>فعال</Button>
                  <Button size="sm" variant={cur?.value ? "danger" : "ghost"} onClick={() => setConsent.mutate({ type: c.key, value: false })}>لغو</Button>
                </div>
              </li>
            );
          })}
        </ul>
      </Card>

      {prefs && (
        <Card>
          <h2 className="mb-3 font-bold">اعلان‌ها</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="flex items-center justify-between rounded-md border border-line px-3 py-3 text-sm">
              سکوت شبانه (۲۲ تا ۷)
              <input type="checkbox" className="size-5 accent-[var(--c-accent)]" defaultChecked={prefs.quiet_start === "22:00"}
                onChange={(e) => savePrefs.mutate({ ...prefs, quiet_start: e.target.checked ? "22:00" : null, quiet_end: e.target.checked ? "07:00" : null })} />
            </label>
            <label className="flex items-center justify-between rounded-md border border-line px-3 py-3 text-sm">
              سقف اعلان اختیاری روزانه
              <input type="number" min={0} max={20} defaultValue={prefs.daily_cap} className="w-16 rounded-md border border-line px-2 py-1.5"
                onChange={(e) => savePrefs.mutate({ ...prefs, daily_cap: Number(e.target.value) })} />
            </label>
          </div>
          <p className="mt-2 text-xs text-ink-soft">اعلان‌های ضروری حقوقی/تراکنشی مستقل از این تنظیمات ارسال می‌شوند و هیچ دادهٔ حساسی در متن آن‌ها نیست.</p>
        </Card>
      )}

      <Card>
        <h2 className="mb-3 font-bold">دادهٔ شخصی من</h2>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" loading={exportData.isPending} onClick={() => exportData.mutate()}>دریافت نسخهٔ قابل دانلود (JSON)</Button>
          <Chip>منشأ داده: Snapshot حداقلی دانشجو۳۶۰ با درج زمان به‌روزرسانی</Chip>
        </div>
      </Card>

      <Card className="border-bad/30">
        <h2 className="mb-1 font-bold text-bad">خروج از باشگاه</h2>
        <p className="mb-3 text-sm text-ink-soft">خروج داوطلبانه است و هیچ خدمات پایهٔ آموزشی را محدود نمی‌کند؛ فقط مزایای باشگاه متوقف می‌شود.</p>
        <Button variant="danger" loading={exit.isPending} onClick={() => exit.mutate()}>خروج از باشگاه</Button>
      </Card>
    </div>
  );
}
