/** Persian formatting helpers: numbers, points, Jalali dates (UX-09). */
const faDigits = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];

export function toFa(input: string | number): string {
  return String(input).replace(/\d/g, (d) => faDigits[Number(d)]);
}

export function formatPoints(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  const s = n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return toFa(s);
}

export function formatInt(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return toFa(Number(value).toLocaleString("en-US"));
}

/** Jalali display via built-in Intl (fa-IR Persian calendar); input is ISO UTC. */
export function formatJalali(iso: string | null | undefined, withTime = false): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const opts: Intl.DateTimeFormatOptions = { calendar: "persian", year: "numeric", month: "long", day: "numeric" };
    if (withTime) { opts.hour = "2-digit"; opts.minute = "2-digit"; }
    return new Intl.DateTimeFormat("fa-IR", opts).format(d);
  } catch {
    return iso;
  }
}

export const GOAL_LABELS: Record<string, string> = {
  weakness: "رفع ضعف درسی",
  exam_prep: "آمادگی امتحان",
  skill: "رشد مهارت",
  collaboration: "همکاری آموزشی",
  other: "هدف دیگر",
};

export const STATE_LABELS: Record<string, string> = {
  requested: "ثبت‌شده",
  reserved: "رزروشده",
  approved: "تأییدشده",
  fulfilling: "در حال تحویل",
  delivered: "تحویل‌شده",
  rejected: "ردشده",
  cancelled: "لغوشده",
  expired: "منقضی‌شده",
  failed: "ناموفق",
  refunded: "مسترد‌شده",
  unknown: "نامعلوم",
  flagged: "نشانه‌گذاری‌شده",
  data_validation: "اعتبارسنجی داده",
  human_review: "بررسی انسانی",
  awaiting_explanation: "در انتظار توضیح",
  decided: "تصمیم گرفته‌شده",
  notified: "اطلاع‌رسانی‌شده",
  appealed: "اعتراض‌شده",
  final_review: "بررسی نهایی",
  closed: "بسته‌شده",
  dismissed: "مختومه",
  submitted: "ثبت‌شده",
  in_review: "در حال بررسی",
  accepted: "پذیرفته‌شده",
  active: "فعال",
  quit: "خروج بدون تنبیه",
  completed: "تکمیل‌شده",
  applied: "اعمال‌شده",
  valid: "معتبر",
  revoked: "باطل‌شده",
  corrected: "اصلاح‌شده",
  draft: "پیش‌نویس",
  simulated: "شبیه‌سازی‌شده",
  pending_approval: "در انتظار تأیید",
  published: "منتشرشده",
  retired: "بازنشسته",
  left_voluntary: "خروج داوطلبانه",
  paused: "موقتاً متوقف",
  graduated: "فارغ‌التحصیل",
};

export const PATH_LABELS: Record<string, string> = {
  learning: "استمرار یادگیری",
  skill: "رشد مهارت",
  collaboration: "همکاری آموزشی",
};

export const TX_LABELS: Record<string, string> = {
  award: "کسب امتیاز",
  reserve: "رزرو امتیاز",
  release: "آزادسازی رزرو",
  spend: "مصرف پاداش",
  expire: "انقضا",
  adjust: "سند جبرانی",
};
