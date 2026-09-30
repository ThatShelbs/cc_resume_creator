import { Card, Skeleton } from "@/components/ui/primitives";
import type { Project } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export function StatsStrip({ projects, loading }: { projects: Project[] | undefined; loading: boolean }) {
  const stats = [
    { label: "Projects", value: projects?.length ?? 0, tone: "text-foreground" },
    { label: "Applied", value: projects?.filter((p) => p.status === "applied").length ?? 0, tone: "text-primary" },
    { label: "Interviewing", value: projects?.filter((p) => p.status === "interviewing").length ?? 0, tone: "text-warning" },
    { label: "Offers", value: projects?.filter((p) => p.status === "offer").length ?? 0, tone: "text-success" },
  ];
  return (
    <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      {stats.map((s) => (
        <Card key={s.label} className="px-4 py-3.5">
          <div className="text-xs font-medium text-muted-foreground">{s.label}</div>
          {loading ? (
            <Skeleton className="mt-2 h-7 w-10" />
          ) : (
            <div className={cn("mt-1 text-2xl font-semibold tabular-nums tracking-tight", s.tone)}>{s.value}</div>
          )}
        </Card>
      ))}
    </div>
  );
}
