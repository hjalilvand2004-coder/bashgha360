import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Check, ShieldCheck, ExternalLink } from "lucide-react";
import { get, put, ApiError } from "../lib/api";
import { Button, Card, Chip, Input, PageHeader } from "../components/ui";
import { toFa } from "../lib/format";

/** شکل قرینه‌ی فرم «افزودن/ویرایش سامانه» در پورتال ورود یکپارچهٔ دانشجو۳۶۰. */
type SsoSettings = {
  enabled: boolean;
  issuer: string;
  redirect_uri: string;
  app_key: string;
  display_name_fa: string;
  entry_url: string;
  description_fa: string;
  client_id: string;
  sort_order: number;
  icon_emoji: string;
  is_active: boolean;
  client_secret_in_env: boolean;
  updated_at: string;
};

const EMPTY: SsoSettings = {
  enabled: true, issuer: "", redirect_uri: "", app_key: "daneshjooclub",
  display_name_fa: "باشگاه دانشجو۳۶۰", entry_url: "", description_fa: "",
  client_id: "daneshjooclub360", sort_order: 14, icon_emoji: "🥇", is_active: true,
  client_secret_in_env: false, updated_at: "",
};

const FIELD_ERRORS: Record<string, string> = {
  app_key: "کلید سامانه لازم است.",
  display_name_fa: "نام سامانه لازم است.",
  entry_url: "آدرس ورود باید با http:// یا https:// شروع شود.",
  client_id: "Client ID لازم است.",
  sort_order: "ترتیب باید عددی نامنفی باشد.",
};

/** تنظیمات ورود یکپارچه (SSO) — ثبت این سامانه در پورتال دانشجو۳۶۰ (مدیر باشگاه/مدیر فنی). */
export default function SsoSettingsPage() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const [fieldErrs, setFieldErrs] = useState<Record<string, string>>({});
  const [copied, setCopied] = useState(false);
  const { data, isLoading } = useQuery({ queryKey: ["sso-settings"], queryFn: () => get<SsoSettings>("/admin/sso-settings") });
  const [form, setForm] = useState<SsoSettings>(EMPTY);
  useEffect(() => { if (data) setForm(data); }, [data]);

  const save = useMutation({
    mutationFn: (v: SsoSettings) => put<SsoSettings>("/admin/sso-settings", {
      app_key: v.app_key, display_name_fa: v.display_name_fa, entry_url: v.entry_url,
      description_fa: v.description_fa, client_id: v.client_id,
      sort_order: Number(v.sort_order) || 0, icon_emoji: v.icon_emoji, is_active: v.is_active,
    }),
    onSuccess: (d) => { setMsg("ذخیره شد — ثبت این سامانه در پورتال ورود یکپارچه به‌روزرسانی شد."); setFieldErrs({}); setForm(d); qc.invalidateQueries({ queryKey: ["sso-settings"] }); },
    onError: (e) => {
      const details = e instanceof ApiError ? (e.details as { fields?: Record<string, string> } | undefined) : undefined;
      if (details?.fields) setFieldErrs(Object.fromEntries(Object.entries(details.fields).map(([k, v]) => [k, FIELD_ERRORS[v] ?? v])));
      setMsg(e instanceof Error ? e.message : "خطا در ذخیرهٔ تنظیمات");
    },
  });

  const copyRedirect = async () => {
    try { await navigator.clipboard.writeText(form.redirect_uri); setCopied(true); setTimeout(() => setCopied(false), 1600); } catch { /* clipboard unavailable */ }
  };
  const set = (k: keyof SsoSettings, v: string | number | boolean) => setForm((f) => ({ ...f, [k]: v }));

  if (isLoading) return <Card><p className="text-sm text-ink-soft">در حال دریافت تنظیمات ورود یکپارچه…</p></Card>;

  return (
    <div className="space-y-4">
      <PageHeader title="تنظیمات ورود یکپارچه (SSO)"
        subtitle="قرینهٔ فرم «افزودن/ویرایش سامانه» در پورتال ورود یکپارچهٔ دانشجو۳۶۰ — پیش‌فرض‌ها همان ثبت رسمی این سامانه در پورتال است."
        badge={form.enabled ? undefined : "ورود یکپارچه غیرفعال"} />

      {msg && <p role="status" className="rounded-xl border border-ok/30 bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="font-bold">افزودن / ویرایش ثبت این سامانه</h2>
            <Chip tone={form.is_active ? "ok" : "warn"}>{form.is_active ? "فعال" : "غیرفعال"}</Chip>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="کلید سامانه (appKey)" dir="ltr" value={form.app_key}
              onChange={(e) => set("app_key", e.target.value)} error={fieldErrs.app_key} />
            <Input label="نام سامانه" value={form.display_name_fa}
              onChange={(e) => set("display_name_fa", e.target.value)} error={fieldErrs.display_name_fa} />
            <div className="sm:col-span-2">
              <Input label="آدرس ورود (نقطهٔ ورود OIDC این سامانه)" dir="ltr" value={form.entry_url}
                onChange={(e) => set("entry_url", e.target.value)} error={fieldErrs.entry_url}
                placeholder="http://…/api/v1/auth/sso/login" />
              <p className="mt-1 text-[11px] leading-5 text-ink-soft">
                نکته: برای ورود یکپارچه، آدرس ورود باید نقطهٔ شروع جریان OIDC این سامانه باشد.
              </p>
            </div>
            <div className="sm:col-span-2">
              <Input label="توضیح" value={form.description_fa} onChange={(e) => set("description_fa", e.target.value)} />
            </div>
            <Input label="Client ID در SSO" dir="ltr" value={form.client_id}
              onChange={(e) => set("client_id", e.target.value)} error={fieldErrs.client_id} />
            <div className="w-full">
              <label className="mb-1.5 block text-sm font-medium" htmlFor="ss-order">ترتیب</label>
              <input id="ss-order" type="number" min={0} dir="ltr" value={form.sort_order}
                onChange={(e) => set("sort_order", Number(e.target.value))}
                className={`min-h-11 w-full rounded-xl border bg-surface px-3 text-sm outline-none ${fieldErrs.sort_order ? "border-bad" : "border-line focus:border-accent"}`} />
              {fieldErrs.sort_order && <p role="alert" className="mt-1 text-xs text-bad">{fieldErrs.sort_order}</p>}
            </div>
            <Input label="آیکن (emoji)" value={form.icon_emoji} onChange={(e) => set("icon_emoji", e.target.value)} />
            <label className="flex min-h-11 cursor-pointer items-center gap-2 self-end rounded-xl border border-line bg-surface px-3 text-sm">
              <input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)}
                className="size-4.5 accent-[var(--c-accent)]" />
              فعال
            </label>
          </div>
          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <Button variant="ghost" onClick={() => { if (data) { setForm(data); setFieldErrs({}); setMsg("تغییرات بازگردانی شد."); } }}>
              انصراف از ویرایش
            </Button>
            <Button onClick={() => save.mutate(form)} loading={save.isPending}>
              ذخیرهٔ تغییرات
            </Button>
          </div>
          <p className="mt-3 rounded-xl bg-bg p-3 text-[11px] leading-6 text-ink-soft">
            نکتهٔ امنیتی: راز Client (client_secret) هرگز در این فرم ذخیره یا نمایش داده نمی‌شود —
            فقط از طریق فایل <code dir="ltr">.env</code> استقرار (<code dir="ltr">SSO_CLIENT_SECRET</code>).
          </p>
        </Card>

        <div className="space-y-4">
          <Card>
            <h2 className="mb-3 flex items-center gap-2 font-bold"><ShieldCheck className="size-5 text-accent" aria-hidden /> وضعیت اتصال</h2>
            <ul className="space-y-2.5 text-sm">
              <li className="flex items-center justify-between gap-2">
                <span className="text-ink-soft">ورود یکپارچه</span>
                <Chip tone={form.enabled && form.is_active ? "ok" : "warn"}>
                  {form.enabled && form.is_active ? "فعال" : "غیرفعال"}
                </Chip>
              </li>
              <li className="flex items-center justify-between gap-2">
                <span className="text-ink-soft">سامانهٔ مرکزی (Issuer)</span>
                <code dir="ltr" className="text-xs">{form.issuer || "—"}</code>
              </li>
              <li className="flex items-center justify-between gap-2">
                <span className="text-ink-soft">راز Client در env</span>
                <Chip tone={form.client_secret_in_env ? "ok" : "warn"}>{form.client_secret_in_env ? "تنظیم شده" : "تنظیم نشده"}</Chip>
              </li>
              <li className="flex items-center justify-between gap-2">
                <span className="text-ink-soft">ترتیب ثبت در پورتال</span>
                <span>{toFa(String(form.sort_order))}</span>
              </li>
            </ul>
            <p className="mt-3 text-[11px] text-ink-soft">آخرین به‌روزرسانی: {form.updated_at ? toFa(form.updated_at.slice(0, 10)) : "—"}</p>
          </Card>

          <Card>
            <h2 className="mb-2 font-bold">Redirect URI ثبت‌شده در پورتال</h2>
            <div dir="ltr" className="break-all rounded-xl bg-bg p-3 font-mono text-xs leading-5">{form.redirect_uri || "—"}</div>
            <Button size="sm" variant="ghost" className="mt-2 w-full" onClick={copyRedirect}>
              {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
              {copied ? "کپی شد" : "کپی برای ثبت در پورتال"}
            </Button>
            <p className="mt-2 text-[11px] leading-5 text-ink-soft">
              در پورتال مرکزی (مدیریت سامانه‌ها) همین مقدار به‌عنوان نقطهٔ بازگشت جریان OIDC ثبت می‌شود.
            </p>
          </Card>

          <Card className="border-accent/30 bg-gradient-to-bl from-accent/5 to-transparent">
            <h2 className="mb-2 flex items-center gap-2 font-bold"><ExternalLink className="size-5 text-accent" aria-hidden /> نمایش در صفحهٔ ورود</h2>
            <div className="flex items-center gap-3 rounded-xl border border-line bg-surface p-3">
              <span className="grid size-11 place-items-center rounded-xl bg-gradient-to-br from-primary to-accent text-xl" aria-hidden>{form.icon_emoji}</span>
              <div>
                <p className="text-sm font-bold">{form.display_name_fa}</p>
                <p className="text-[11px] text-ink-soft">{form.description_fa || "—"}</p>
              </div>
            </div>
            <p className="mt-2 text-[11px] leading-5 text-ink-soft">
              دکمهٔ «ورود یکپارچه» در صفحهٔ ورود دقیقاً با همین نام و آیکن نمایش داده می‌شود.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
