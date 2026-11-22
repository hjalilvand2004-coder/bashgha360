import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, post } from "../lib/api";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button, Card, Chip, Input, PageHeader, Select } from "../components/ui";
import { GOAL_LABELS } from "../lib/format";

type Goal = { id: string; goal_type: string; title_fa: string; status: string };

const schema = z.object({
  goal_type: z.enum(["weakness", "exam_prep", "skill", "collaboration", "other"]),
  title_fa: z.string().min(3, "عنوان هدف را بنویسید"),
});

export default function Goals() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["goals"], queryFn: () => get<{ items: Goal[] }>("/goals") });
  const { register, handleSubmit, reset, formState } = useForm<{ goal_type: Goal["goal_type"]; title_fa: string }>({
    resolver: zodResolver(schema), defaultValues: { goal_type: "skill" },
  });
  const add = useMutation({
    mutationFn: (body: { goal_type: string; title_fa: string }) => post("/goals", body),
    onSuccess: () => { reset({ goal_type: "skill", title_fa: "" }); qc.invalidateQueries({ queryKey: ["goals"] }); },
  });

  return (
    <div className="space-y-4">
      <PageHeader title="اهداف و ترجیحات" subtitle="اهداف مجاز: رفع ضعف، آمادگی امتحان، مهارت، همکاری یا هدف دیگر. اهداف، پیشنهادها را بهتر می‌کنند." />
      <Card>
        <form onSubmit={handleSubmit((d) => add.mutate(d))} className="grid items-end gap-3 md:grid-cols-[1fr_2fr_auto]">
          <Select label="نوع هدف" {...register("goal_type")}>
            {Object.entries(GOAL_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
          <Input label="عنوان هدف" placeholder="مثلاً آمادگی آزمون ریاضی ۲" {...register("title_fa")} error={formState.errors.title_fa?.message} />
          <Button type="submit" loading={add.isPending} className="md:mb-0.5">افزودن هدف</Button>
        </form>
      </Card>
      <div className="grid gap-3 md:grid-cols-2">
        {data?.items.map((g) => (
          <Card key={g.id} className="flex items-center justify-between">
            <div>
              <p className="font-bold">{g.title_fa}</p>
              <p className="text-xs text-ink-soft">{GOAL_LABELS[g.goal_type] ?? g.goal_type}</p>
            </div>
            <div className="flex items-center gap-2">
              <Chip tone={g.status === "active" ? "ok" : "neutral"}>{g.status === "active" ? "فعال" : "بایگانی"}</Chip>
              {g.status === "active" && (
                <Button size="sm" variant="ghost" onClick={() => post(`/goals/${g.id}/archive`).then(() => qc.invalidateQueries({ queryKey: ["goals"] }))}>بایگانی</Button>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
