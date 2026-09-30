import { AutoTextarea, Card } from "@/components/ui/primitives";
import type { FactInfo, LintResult } from "@/lib/api/types";
import { type Draft } from "./draft";
import { Update } from "@/features/workspace/editor/types";
import { IssueBadge } from "@/features/workspace/editor/IssueBadge";
import { ExperienceCard } from "@/features/workspace/editor/ExperienceCard";
import { SkillsEditor } from "@/features/workspace/editor/SkillsEditor";

export function ContentEditor({
  draft,
  update,
  lint,
  facts,
}: {
  draft: Draft;
  update: Update;
  lint: LintResult | undefined;
  facts: Record<string, FactInfo> | undefined;
}) {
  return (
    <div className="grid gap-4">
      <Card className="p-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">Summary</h3>
          <div className="flex items-center gap-2">
            <IssueBadge issues={lint?.summary} />
            <span className="text-[11px] tabular-nums text-muted-foreground">
              {draft.summary.trim() ? draft.summary.trim().split(/\s+/).length : 0} words
            </span>
          </div>
        </div>
        <AutoTextarea
          value={draft.summary}
          onChange={(e) => update((d) => ({ ...d, summary: e.target.value }))}
          className="mt-2"
          aria-label="Summary"
        />
      </Card>

      {draft.experience.map((_, i) => (
        <ExperienceCard key={i} index={i} draft={draft} update={update} lint={lint} facts={facts} />
      ))}

      <SkillsEditor draft={draft} update={update} lint={lint} />

      {draft.cover_letter && (
        <Card className="p-4">
          <h3 className="text-sm font-semibold">Cover letter</h3>
          <p className="text-xs text-muted-foreground">"Dear Hiring Team," and your sign-off are added automatically.</p>
          <div className="mt-3 grid gap-2">
            {draft.cover_letter.map((p, i) => (
              <div key={i} className="flex gap-2">
                <AutoTextarea
                  value={p.text}
                  onChange={(e) =>
                    update((d) => ({
                      ...d,
                      cover_letter: (d.cover_letter ?? []).map((x, j) => (j === i ? { ...x, text: e.target.value } : x)),
                    }))
                  }
                  aria-label={`Cover letter paragraph ${i + 1}`}
                />
                <div className="pt-1.5">
                  <IssueBadge issues={lint?.cover_letter[String(i)]} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
