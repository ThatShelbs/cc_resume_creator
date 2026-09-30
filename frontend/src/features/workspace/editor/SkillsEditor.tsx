import { ArrowDownAZ, X } from "lucide-react";
import { useRef, useState } from "react";
import { SeverityIcon } from "@/components/shared/common";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/overlays";
import { Card, Input } from "@/components/ui/primitives";
import type { LintResult } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { type Draft } from "@/features/workspace/draft";
import { Update } from "@/features/workspace/editor/types";
import { worst } from "@/features/workspace/editor/IssueBadge";

export function SkillsEditor({ draft, update, lint }: { draft: Draft; update: Update; lint: LintResult | undefined }) {
  const [value, setValue] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const add = () => {
    const items = value.split(",").map((s) => s.trim()).filter(Boolean);
    if (!items.length) return;
    update((d) => {
      const existing = new Set(d.skills.map((s) => s.toLowerCase()));
      return { ...d, skills: [...d.skills, ...items.filter((s) => !existing.has(s.toLowerCase()))] };
    });
    setValue("");
  };
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">Skills</h3>
          <p className="text-xs text-muted-foreground">Short, standard labels. Hover a flagged one to see why.</p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground"
          onClick={() => update((d) => ({ ...d, skills: [...d.skills].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" })) }))}
        >
          <ArrowDownAZ /> Sort
        </Button>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5" onClick={() => input.current?.focus()}>
        {draft.skills.map((s, i) => {
          const issues = lint?.skills[String(i)];
          const sev = worst(issues);
          const chip = (
            <span
              className={cn(
                "group inline-flex h-7 items-center gap-1 rounded-md border bg-background pl-2.5 pr-1 text-[13px]",
                sev === "error" && "border-destructive/50 bg-destructive/[0.06] text-destructive",
                sev === "warning" && "border-warning/40 bg-warning/[0.06]",
              )}
            >
              {sev && <SeverityIcon severity={sev} />}
              {s}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  update((d) => ({ ...d, skills: d.skills.filter((_, j) => j !== i) }));
                }}
                className="rounded p-0.5 text-muted-foreground opacity-60 hover:bg-secondary hover:text-foreground group-hover:opacity-100"
                aria-label={`Remove ${s}`}
              >
                <X className="size-3" />
              </button>
            </span>
          );
          return issues ? (
            <Tooltip key={`${s}-${i}`} content={issues.map((x) => x.message).join(" ")}>
              {chip}
            </Tooltip>
          ) : (
            <span key={`${s}-${i}`}>{chip}</span>
          );
        })}
        <Input
          ref={input}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              add();
            } else if (e.key === "Backspace" && !value && draft.skills.length) {
              update((d) => ({ ...d, skills: d.skills.slice(0, -1) }));
            }
          }}
          onBlur={add}
          placeholder="Add a skill"
          className="h-7 w-36 flex-1 border-dashed text-[13px] shadow-none"
          aria-label="Add a skill"
        />
      </div>
    </Card>
  );
}
