/** ثابت‌های «زندگی دانشجویی» v1.5 — چهار وعده: هم‌پایه، همین هفته، بستهٔ ساخت، صدای دانشجو. */

/** وعده‌های محصول — هویت تازهٔ باشگاه (ارزیابی v1.5 §۲) */
export const PROMISES: { to: string; title: string; say: string; icon: string; grad: string; shadow: string }[] = [
  { to: "/peers", title: "آدم‌های من", say: "آدم‌های هم‌علاقه‌ام را پیدا می‌کنم", icon: "🧑‍🤝‍🧑", grad: "from-[#155e63] to-accent", shadow: "shadow-glowAccent" },
  { to: "/week", title: "تجربه‌های من", say: "دانشگاه را جذاب‌تر و متنوع‌تر تجربه می‌کنم", icon: "🎪", grad: "from-violet to-[#8b5cf6]", shadow: "shadow-glowViolet" },
  { to: "/bundles", title: "آیندهٔ من", say: "مهارت، نمونه‌کار و فرصت واقعی می‌سازم", icon: "🛠️", grad: "from-gold to-[#d3a04a]", shadow: "shadow-glowGold" },
  { to: "/voice", title: "اثر من", say: "ایده‌ام شنیده می‌شود و می‌توانم چیزی را تغییر بدهم", icon: "📣", grad: "from-pink to-[#ec4899]", shadow: "shadow-glowPink" },
];

export const PEER_KIND_LABELS: Record<string, string> = {
  language: "همراه تمرین زبان", study: "هم‌مطالعه", outing: "همراه بازدید و پیاده‌روی",
  games: "بازی فکری", presentation: "تمرین ارائه", other: "فعالیت مشترک",
};
export const PEER_KIND_ICONS: Record<string, string> = {
  language: "🗣️", study: "📚", outing: "🚶", games: "🎲", presentation: "🎤", other: "✨",
};

export const OPPORTUNITY_KIND_LABELS: Record<string, string> = {
  visit: "بازدید", workshop: "کارگاه", game: "بازی", talk: "گفت‌وگو",
  volunteer: "داوطلبی", tour: "تور", other: "برنامه",
};
export const OPPORTUNITY_KIND_ICONS: Record<string, string> = {
  visit: "🏭", workshop: "🎨", game: "🎲", talk: "💬", volunteer: "🤲", tour: "🚌", other: "📍",
};

export const VOICE_STATE_LABELS: Record<string, string> = {
  received: "دریافت شد", in_review: "در حال بررسی", accepted: "پذیرفته شد",
  rejected: "رد شد", executed: "اجرا شد",
};
/** مسیر پیگیری — وضعیت‌های رسمی به ترتیب مصوب */
export const VOICE_FLOW: string[] = ["received", "in_review", "accepted", "executed"];

export const PROPOSAL_KIND_LABELS: Record<string, string> = {
  program: "برنامه", space: "فضا و تجهیزات", improvement: "بهبود سامانه", other: "سایر",
};
