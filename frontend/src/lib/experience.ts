/** ثابت‌های تجربهٔ باشگاه (v1.3) — مسیرهای انتخابی، انواع مأموریت، علاقه‌ها. */

export type Persona = {
  key: string; label_fa: string; tagline_fa: string; icon: string; maps_to: string;
};

/** مسیرهای انتخابی ملموس — هر کدام به یکی از سه مسیر سطح مصوب وصل می‌شود. */
export const PERSONA_LOCAL: Record<string, { icon: string; hint_fa: string }> = {
  creator: { icon: "🛠️", hint_fa: "پروژه و حل مسئله" },
  explorer: { icon: "🧭", hint_fa: "رویداد و موضوع تازه" },
  helper: { icon: "🤝", hint_fa: "کمک به هم‌دانشگاهی‌ها" },
  specialist: { icon: "🎯", hint_fa: "مهارت و نمونه‌کار" },
  leader: { icon: "🚩", hint_fa: "هماهنگی تیم" },
};

export const MISSION_KIND_LABELS: Record<string, string> = {
  kickoff: "رویداد آغازین", micro_challenge: "چالش ۲۰ دقیقه‌ای", one_day: "مأموریت یک‌روزه",
  trial_workshop: "کارگاه آزمایشی", skill_evening: "یک عصر، یک مهارت",
  real_problem: "مسئلهٔ واقعی", build: "ساخت", guide: "راهنما", standard: "مأموریت",
};

/** مأموریت‌های کوتاه و کم‌تعهد برای فیلتر «همین حالا شروع کن». */
export const LOW_COMMITMENT_KINDS = ["micro_challenge", "one_day", "trial_workshop", "skill_evening", "kickoff"];

export const INTEREST_LABELS: Record<string, string> = {
  build: "ساختن و پروژه", tech: "فناوری و ابزار", event: "رویداد و برنامه", help: "کمک به دیگران",
  skill: "یادگیری مهارت", guide: "راهنمایی تازه‌واردها", problem: "حل مسئلهٔ واقعی",
  portfolio: "نمونه‌کار", collab: "کار گروهی", explore: "کاوش", team: "تیم و رهبری",
};

export const STORY_KIND_LABELS: Record<string, string> = {
  build: "چیزی ساخت", help: "به کسی کمک کرد", skill: "مهارتی را تجربه کرد", event: "رویدادی اجرا کرد",
};

/** سه پیام کوتاه صفحهٔ اول — معرفی تجربه‌محور باشگاه. */
export const PITCH = [
  { icon: "❤️", title: "با علاقه‌ات شروع کن", body: "چیزی که بلدی، چیزی که دوست داری یاد بگیری و کاری که می‌توانی با دیگران بسازی — همه بخشی از تجربهٔ توست." },
  { icon: "🛠️", title: "چیزی واقعی بساز یا به دیگران کمک کن", body: "مأموریت‌های کوتاه با خروجی ملموس: یک ابزار، یک محتوا، یک راهنما، یک مسئلهٔ حل‌شده." },
  { icon: "🏅", title: "دستاوردت را ببین", body: "نشان و داستانِ کارِ تو ثبت می‌شود؛ بدون فشار، بدون رقابت فرساینده و بدون اثر بر نمره." },
] as const;
