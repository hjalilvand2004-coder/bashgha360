/** Tailwind config — design tokens of باشگاه۳۶۰ (docs/07). RTL-first. v1.2 modern look. */
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
        ink: { DEFAULT: "var(--c-text)", soft: "var(--c-text-muted)" },
        line: "var(--c-border)",
        ok: "var(--c-success)",
        warn: "var(--c-warning)",
        bad: "var(--c-danger)",
      },
      fontFamily: { sans: ["Vazirmatn", "Tahoma", "sans-serif"] },
      borderRadius: { sm: "8px", md: "14px", lg: "20px", xl: "26px" },
      boxShadow: {
        sm: "0 1px 2px rgba(15,20,32,.06)",
        md: "0 6px 18px rgba(15,20,32,.09)",
        lg: "0 16px 40px rgba(15,20,32,.16)",
        glow: "0 4px 18px rgba(46,80,190,.28)",
        glowAccent: "0 4px 18px rgba(14,159,154,.30)",
      },
      keyframes: {
        "pop-in": { "0%": { opacity: "0", transform: "scale(.96)" }, "100%": { opacity: "1", transform: "scale(1)" } },
        shimmer: { "0%": { backgroundPosition: "200% center" }, "100%": { backgroundPosition: "-200% center" } },
      },
      animation: {
        "pop-in": "pop-in .25s ease-out both",
        shimmer: "shimmer 8s linear infinite",
      },
    },
  },
  plugins: [],
};
