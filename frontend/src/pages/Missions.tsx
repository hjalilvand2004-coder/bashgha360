import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, post } from "../lib/api";
import { useState } from "react";
import { createPortal } from "react-dom";
import { Copy, Check, UserPlus } from "lucide-react";
import { Button, Card, Chip, EmptyState, PageHeader, stateTone } from "../components/ui";
import { formatJalali, STATE_LABELS } from "../lib/format";
import { MISSION_KIND_LABELS, LOW_COMMITMENT_KINDS } from "../lib/experience";

type Mission = {
  id: string; title_fa: string; description_fa: string; goal_type: string;
  activities: { event_type?: string; min_count?: number }[]; starts_at: string; ends_at: string;
  is_group: boolean; my_state: string | null;
  mission_kind: string; kind_label_fa: string; output_fa: string; duration_label_fa: string;
  team_size_hint: string; interest_tags: string;
};

type Invite = { id: string; invite_code: string; state: string; mission_title_fa: string; invitee_contact: string };

type Group = {
  id: string; title_fa: string; capacity: number | null; member_count: number; my_state: string | null;
  interest_tag: string; goal_fa: string; expected_output_fa: string; duration_label_fa: string; mission_title_fa: string | null;
};

/** گروه‌های کوچک علاقه‌ای با هدف روشن، زمان محدود و خروجی مشخص. */
function GroupsSection() {
  const qc = useQueryClient();
  const [gmsg, setGmsg] = useState("");
  const { data } = useQuery({ queryKey: ["groups"], queryFn: () => get<{ items: Group[] }>("/groups") });
  const joinG = useMutation({
    mutationFn: (id: string) => post(`/groups/${id}/members`),
    onSuccess: () => { setGmsg("به گروه پیوستید — مشارکت در گروه با ثبت رضایت و سهم شما انجام می‌شود."); qc.invalidateQueries({ queryKey: ["groups"] }); },
    onError: (e) => setGmsg(e instanceof Error ? e.message : "خطا"),
  });
  if (!data || data.items.length === 0) return <EmptyState art="empty" title="گروه فعالی نیست" body="گروه‌های علاقه‌ای توسط مدیر باشگاه ساخته می‌شوند." />;
  return (
    <div className="space-y-3">
      {gmsg && <p role="status" className="rounded-xl border border-ok/30 bg-ok/10 px-3 py-2 text-sm text-ok">{gmsg}</p>}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {data.items.map((g) => (
          <Card key={g.id} className="flex flex-col gap-2">
            <div className="flex items-start justify-between gap-2">
              <p className="font-bold leading-6">{g.title_fa}</p>
              <Chip tone="gold">{g.duration_label_fa || "—"}</Chip>
            </div>
            {g.goal_fa && <p className="text-xs leading-6 text-ink-soft">{g.goal_fa}</p>}
            {g.expected_output_fa && <Chip tone="ok">خروجی: {g.expected_output_fa}</Chip>}
            <p className="mt-auto text-xs text-ink-soft">
              اعضا: {g.member_count.toLocaleString("fa-IR")}{g.capacity ? ` از ${g.capacity.toLocaleString("fa-IR")}` : ""}
            </p>
            {g.my_state === "member"
              ? <Chip tone="ok">عضو این گروهی</Chip>
              : <Button size="sm" loading={joinG.isPending} onClick={() => joinG.mutate(g.id)}>پیوستن به گروه</Button>}
          </Card>
        ))}
      </div>
    </div>
  );
}

/** مأموریت‌های کوتاه، تیمی و دارای خروجی ملموس + دعوت دوست برای مأموریت مشترک. */
export default function Missions() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const [tab, setTab] = useState<"all" | "quick" | "team">("all");
  const [inviteFor, setInviteFor] = useState<Mission | null>(null);
  const [contact, setContact] = useState("");
  const [inviteMsg, setInviteMsg] = useState<{ text: string; code?: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const { data } = useQuery({ queryKey: ["missions"], queryFn: () => get<{ items: Mission[] }>("/missions") });
  const { data: invites } = useQuery({ queryKey: ["my-invites"], queryFn: () => get<{ items: Invite[] }>("/club-experience/invites/mine") });

  const join = useMutation({
    mutationFn: (id: string) => post(`/missions/${id}/join`),
    onSuccess: () => { setMsg("به مأموریت پیوستید — حالا می‌توانی دوستت را برای مأموریت مشترک دعوت کنی."); qc.invalidateQueries({ queryKey: ["missions"] }); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });
  const quit = useMutation({
    mutationFn: (id: string) => post(`/missions/${id}/quit`),
    onSuccess: () => { setMsg("خروج انجام شد — هیچ تنبیهی برای شما ثبت نمی‌شود."); qc.invalidateQueries({ queryKey: ["missions"] }); },
    onError: (e) => setMsg(e instanceof Error ? e.message : "خطا"),
  });
  const createInvite = useMutation({
    mutationFn: (m: Mission) => post<{ invite_code: string; share_text_fa: string; note_fa: string }>("/club-experience/invites", { mission_id: m.id, invitee_contact: contact }),
    onSuccess: (d) => { setInviteMsg({ text: "دعوت ساخته شد — پاداش به مشارکت مشترک شماست، نه تعداد دعوت‌ها.", code: d.invite_code }); qc.invalidateQueries({ queryKey: ["my-invites"] }); },
    onError: (e) => setInviteMsg({ text: e instanceof Error ? e.message : "خطا در ساخت دعوت" }),
  });

  const items = (data?.items ?? []).filter((m) => {
    if (tab === "quick") return LOW_COMMITMENT_KINDS.includes(m.mission_kind);
    if (tab === "team") return m.is_group || (m.team_size_hint && m.team_size_hint !== "فردی");
    return true;
  });
  const kickoffs = (data?.items ?? []).filter((m) => m.mission_kind === "kickoff");

  const copyCode = async (code: string) => {
    try { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* noop */ }
  };

  return (
    <div className="space-y-4">
      <PageHeader title="مأموریت‌ها" subtitle="کوتاه شروع کن، چیزی واقعی بساز و هر وقت خواستی خارج شو — خروج از هر مأموریت بدون تنبیه است." />

      {kickoffs.length > 0 && !kickoffs[0].my_state && (
        <Card className="relative overflow-hidden border-accent/40 bg-gradient-to-bl from-accent/10 to-transparent">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-bold">🚀 رویداد آغازین: {kickoffs[0].title_fa}</p>
              <p className="mt-1 text-xs leading-6 text-ink-soft">{kickoffs[0].description_fa}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Chip tone="ok">خروجی: {kickoffs[0].output_fa || "نشان اولین قدم"}</Chip>
                {kickoffs[0].duration_label_fa && <Chip>{kickoffs[0].duration_label_fa}</Chip>}
              </div>
            </div>
            <Button loading={join.isPending} onClick={() => join.mutate(kickoffs[0].id)}>همین حالا تجربه کن</Button>
          </div>
        </Card>
      )}

      {msg && <p role="status" className="rounded-xl border border-ok/30 bg-ok/10 px-3 py-2 text-sm text-ok">{msg}</p>}

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="فیلتر مأموریت‌ها">
        {([["all", "همهٔ مأموریت‌ها"], ["quick", "⏱ کوتاه و کم‌تعهد"], ["team", "👥 تیمی و واقعی"]] as const).map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`rounded-full border px-4 py-2 text-xs transition ${tab === k ? "border-transparent bg-gradient-to-l from-primary to-[#31427f] font-bold text-primary-fg shadow-glow" : "border-line bg-surface text-ink-soft hover:border-accent/50"}`}>
            {label}
          </button>
        ))}
      </div>

      {data && items.length === 0 && (
        <EmptyState art="flag" title="در این دسته مأموریتی فعال نیست" body="مأموریت‌های کوتاه و تیمی توسط مدیر باشگاه تعریف می‌شوند." />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((m) => (
          <Card key={m.id} className={m.mission_kind === "kickoff" ? "border-accent/40" : undefined}>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <p className="font-bold">{m.title_fa}</p>
              <Chip tone={m.mission_kind === "kickoff" ? "gold" : "info"}>{m.kind_label_fa || MISSION_KIND_LABELS[m.mission_kind] || "مأموریت"}</Chip>
              {m.is_group && <Chip tone="info">گروهی</Chip>}
            </div>
            <p className="text-sm leading-6 text-ink-soft">{m.description_fa}</p>
            <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
              {m.duration_label_fa && <Chip>⏱ {m.duration_label_fa}</Chip>}
              {m.team_size_hint && <Chip>👥 {m.team_size_hint}</Chip>}
              {m.output_fa && <Chip tone="ok">خروجی: {m.output_fa}</Chip>}
            </div>
            {m.activities.length > 0 && (
              <ul className="mt-2 space-y-1 text-xs text-ink-soft">
                {m.activities.map((a, i) => <li key={i}>• {a.event_type} — حداقل {a.min_count} بار</li>)}
              </ul>
            )}
            <p className="mt-2 text-xs text-ink-soft">بازه: {formatJalali(m.starts_at)} تا {formatJalali(m.ends_at)}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {m.my_state ? (
                <>
                  <Chip tone={stateTone(m.my_state)}>{STATE_LABELS[m.my_state] ?? m.my_state}</Chip>
                  {m.my_state === "active" && <Button size="sm" variant="ghost" onClick={() => quit.mutate(m.id)}>ترک مأموریت (بدون تنبیه)</Button>}
                  {m.my_state === "active" && m.team_size_hint !== "فردی" && (
                    <Button size="sm" variant="accent" onClick={() => { setInviteFor(m); setInviteMsg(null); setContact(""); }}>
                      <UserPlus className="size-4" aria-hidden /> دعوت دوست
                    </Button>
                  )}
                </>
              ) : (
                <Button size="sm" loading={join.isPending} onClick={() => join.mutate(m.id)}>پیوستن</Button>
              )}
            </div>
          </Card>
        ))}
      </div>

      <section aria-label="گروه‌های علاقه‌ای" className="space-y-3">
        <h2 className="text-lg font-bold">گروه‌های علاقه‌ای — «یک هفته، سه نفر، یک ایدهٔ قابل‌ارائه»</h2>
        <GroupsSection />
      </section>

      {invites && invites.items.length > 0 && (
        <Card>
          <h2 className="mb-2 font-bold">دعوت‌های من</h2>
          <ul className="space-y-2 text-sm">
            {invites.items.map((i) => (
              <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line px-3 py-2">
                <span>{i.mission_title_fa}{i.invitee_contact ? ` → ${i.invitee_contact}` : ""}</span>
                <span className="flex items-center gap-2">
                  <code dir="ltr" className="rounded bg-bg px-2 py-0.5 text-xs">{i.invite_code}</code>
                  <Chip tone={i.state === "joined" ? "ok" : "warn"}>{i.state === "joined" ? "پیوسته" : "در انتظار"}</Chip>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] text-ink-soft">هیچ امتیازی برای تعداد دعوت‌ها نیست؛ پاداش وقتی است که با هم مأموریت را انجام بدهید.</p>
        </Card>
      )}

      {inviteFor && createPortal(
        <div role="dialog" aria-modal="true" aria-label={`دعوت دوست به ${inviteFor.title_fa}`} className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setInviteFor(null)}>
          <Card className="w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold">دعوت دوست به مأموریت مشترک</h3>
            <p className="mt-1 text-sm text-ink-soft">{inviteFor.title_fa}</p>
            <label htmlFor="inv-contact" className="mt-4 block text-sm font-medium">ایمیل یا شمارهٔ دوست (اختیاری)</label>
            <input id="inv-contact" dir="ltr" value={contact} onChange={(e) => setContact(e.target.value)}
              className="mt-1.5 min-h-11 w-full rounded-xl border border-line bg-surface px-3 text-sm outline-none focus:border-accent" placeholder="friend@university.ir" />
            {inviteMsg && (
              <div className="mt-3 rounded-xl border border-ok/30 bg-ok/10 p-3 text-sm text-ok">
                <p>{inviteMsg.text}</p>
                {inviteMsg.code && (
                  <p className="mt-2 flex items-center gap-2">
                    کد دعوت: <code dir="ltr" className="rounded bg-surface px-2 py-0.5 font-bold">{inviteMsg.code}</code>
                    <button onClick={() => copyCode(inviteMsg.code!)} className="grid size-8 place-items-center rounded-lg border border-line bg-surface" aria-label="کپی کد دعوت">
                      {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
                    </button>
                  </p>
                )}
              </div>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setInviteFor(null)}>بستن</Button>
              {!inviteMsg && <Button loading={createInvite.isPending} onClick={() => createInvite.mutate(inviteFor)}>ساخت دعوت</Button>}
            </div>
            <p className="mt-2 text-[11px] text-ink-soft">این دعوت برای «مأموریت مشترک» است، نه مسابقهٔ جذب — هیچ امتیازی برای تعداد دعوت‌ها وجود ندارد.</p>
          </Card>
        </div>,
        document.body,
      )}
    </div>
  );
}
