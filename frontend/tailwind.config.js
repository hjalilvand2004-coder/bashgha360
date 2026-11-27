/** Tailwind config — design tokens of باشگاه۳۶۰ (docs/07). RTL-first.
 * v1.4 — «جذاب دانشجویی»: پالت شاد چندرنگ، شعاع بزرگ‌تر، درخشش‌های رنگی، انیمیشن جشن.
 * v1.6 — پالت و سایه‌ها بر پایهٔ «Aurora Premium» (شب پیش‌فرض / روز)؛ مقادیر در index.css. */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--c-bg)",
        surface: "var(--c-surface)",
        primary: { DEFAULT: "var(--c-primary)", fg: "var(--c-primary-contrast)" },
        accent: { DEFAULT: "var(--c-accent)" },
        gold: { DEFAULT: "var(--c-gold)" },
        violet: { DEFAULT: "var(--c-violet)" },
        pink: { DEFAULT: "var(--c-pink)" },
        orange: { DEFAULT: "var(--c-orange)" },
        lime: { DEFAULT: "var(--c-lime)" },
        cyan: { DEFAULT: "var(--c-cyan)" },
        ink: { DEFAULT: "var(--c-text)", soft: "var(--c-text-muted)" },
        line: "var(--c-border)",
        ok: "var(--c-success)",
        warn: "var(--c-warning)",
        bad: "var(--c-danger)",
      },
      fontFamily: { sans: ["Vazirmatn", "Tahoma", "sans-serif"] },
      borderRadius: { sm: "10px", md: "16px", lg: "22px", xl: "28px" },
      boxShadow: {
        /* v1.6 — سایه‌ها از توکن‌های Aurora می‌آیند تا بین شب و روز درست جابه‌جا شوند (index.css) */
        sm: "var(--sh-sm)",
        md: "var(--sh-md)",
        lg: "var(--sh-lg)",
        glow: "var(--sh-glow)",
        glowAccent: "0 4px 18px rgba(244, 114, 182, 0.30)",
        glowViolet: "0 4px 20px rgba(167, 139, 250, 0.30)",
        glowPink: "0 4px 20px rgba(244, 114, 182, 0.28)",
        glowGold: "0 4px 20px rgba(251, 191, 36, 0.32)",
        lift: "var(--sh-lift)",
      },
      keyframes: {
        "pop-in": { "0%": { opacity: "0", transform: "scale(.96)" }, "100%": { opacity: "1", transform: "scale(1)" } },
        shimmer: { "0%": { backgroundPosition: "200% center" }, "100%": { backgroundPosition: "-200% center" } },
        "bounce-soft": { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-4px)" } },
        wiggle: { "0%,100%": { transform: "rotate(-3deg)" }, "50%": { transform: "rotate(3deg)" } },
        "confetti-fall": {
          "0%": { transform: "translateY(-10vh) rotate(0deg)", opacity: "1" },
          "100%": { transform: "translateY(85vh) rotate(540deg)", opacity: "0" },
        },
        "ring-fill": { from: { strokeDashoffset: "var(--ring-from)" }, to: { strokeDashoffset: "var(--ring-to)" } },
      },
      animation: {
        "pop-in": "pop-in .25s ease-out both",
        shimmer: "shimmer 8s linear infinite",
        "bounce-soft": "bounce-soft 2.2s ease-in-out infinite",
        wiggle: "wiggle 1.8s ease-in-out infinite",
        "confetti-fall": "confetti-fall 2.4s ease-in forwards",
      },
    },
  },
  plugins: [],
};
