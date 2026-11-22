/** Charts with textual summary + data table alternative (UX-08: meaning never color/motion only). */
import { Card } from "./ui";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { toFa, formatPoints } from "../lib/format";

export type ChartDatum = { label: string; value: number };

export function MiniChart({ title, data, unit_fa = "امتیاز", tableCaption }: {
  title: string; data: ChartDatum[]; unit_fa?: string; tableCaption: string;
}) {
  const total = data.reduce((a, b) => a + b.value, 0);
  return (
    <Card>
      <p className="mb-2 text-sm font-bold">{title}</p>
      <p className="sr-only">خلاصهٔ متنی نمودار: {data.map((d) => `${d.label}: ${formatPoints(d.value)} ${unit_fa}`).join("، ")}. مجموع: {formatPoints(total)}.</p>
      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-ink-soft">داده‌ای برای نمایش وجود ندارد.</p>
      ) : (
        <div className="h-44" role="img" aria-label={title}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--c-border)" />
              <XAxis dataKey="label" tick={{ fontSize: 11, fontFamily: "Vazirmatn" }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => toFa(String(v))} width={34} />
              <Tooltip
                contentStyle={{ fontFamily: "Vazirmatn", fontSize: 12, borderRadius: 8, background: "var(--c-surface)", border: "1px solid var(--c-border)" }}
                formatter={(v: number) => [`${formatPoints(v)} ${unit_fa}`, ""]}
              />
              <Bar dataKey="value" fill="var(--c-accent)" radius={[6, 6, 0, 0]} maxBarSize={38} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <details className="mt-2 text-xs text-ink-soft">
        <summary className="cursor-pointer">جدول جایگزین نمودار</summary>
        <table className="mt-2 w-full text-right">
          <caption className="sr-only">{tableCaption}</caption>
          <thead><tr><th className="py-1">عنوان</th><th className="py-1">{unit_fa}</th></tr></thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.label} className="border-t border-line"><td className="py-1">{d.label}</td><td className="py-1">{formatPoints(d.value)}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
    </Card>
  );
}
