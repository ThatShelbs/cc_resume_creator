import { SeverityIcon } from "@/components/shared/common";
import { Tooltip } from "@/components/ui/overlays";
import type { LintIssue, Severity } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export const WORST: Severity[] = ["error", "warning", "info"];

export function worst(issues: LintIssue[] | undefined): Severity | null {
  if (!issues?.length) return null;
  return WORST.find((s) => issues.some((i) => i.severity === s)) ?? null;
}

export function IssueBadge({ issues }: { issues: LintIssue[] | undefined }) {
  const sev = worst(issues);
  if (!sev || !issues) return null;
  return (
    <Tooltip
      content={
        <ul className="grid gap-1">
          {issues.map((i, n) => (
            <li key={n} className="flex gap-1.5">
              <span>•</span>
              <span>{i.message}</span>
            </li>
          ))}
        </ul>
      }
    >
      <span
        tabIndex={0}
        className={cn(
          "inline-flex h-6 items-center gap-1 rounded-md px-1.5 text-[11px] font-medium",
          sev === "error" && "bg-destructive/10 text-destructive",
          sev === "warning" && "bg-warning/10 text-warning",
          sev === "info" && "bg-muted text-muted-foreground",
        )}
      >
        <SeverityIcon severity={sev} className="text-current" />
        {issues.length > 1 ? issues.length : sev === "error" ? "Blocked" : sev === "warning" ? "Check" : "Note"}
      </span>
    </Tooltip>
  );
}
