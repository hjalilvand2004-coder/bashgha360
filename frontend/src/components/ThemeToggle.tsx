/** کلید تغییر تم شب/روز — Aurora Premium (v1.6).
 * حالت شب پیش‌فرض است؛ انتخاب در localStorage("theme") ذخیره و با اسکریپت no-flash
 * در index.html قبل از رندر اعمال می‌شود (الگوی تم اکوسیستم: upload/aurora-theme.css). */
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export type Theme = "dark" | "light";

/** تم فعلی از localStorage — هر چیز غیر از "light" یعنی شب (پیش‌فرض). */
export const getStoredTheme = (): Theme =>
  (typeof localStorage !== "undefined" && localStorage.getItem("theme") === "light" ? "light" : "dark");

export function applyTheme(theme: Theme) {
  const h = document.documentElement;
  h.classList.toggle("dark", theme === "dark");
  h.classList.toggle("light", theme === "light");
  try { localStorage.setItem("theme", theme); } catch { /* محیط بدون localStorage */ }
}

export default function ThemeToggle({ className = "" }: { className?: string }) {
  const [dark, setDark] = useState(() => getStoredTheme() === "dark");

  useEffect(() => { applyTheme(dark ? "dark" : "light"); }, [dark]);

  return (
    <button
      onClick={() => setDark(!dark)}
      aria-label={dark ? "تغییر به حالت روز" : "تغییر به حالت شب"}
      title={dark ? "حالت روز" : "حالت شب"}
      className={`grid size-11 shrink-0 place-items-center rounded-xl border border-line bg-surface transition hover:border-accent hover:text-accent ${className}`}
    >
      {dark ? <Sun className="size-5" /> : <Moon className="size-5" />}
    </button>
  );
}
