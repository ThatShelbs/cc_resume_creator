import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ArrowDownAZ, GripVertical, Link2, Plus, Quote, Trash2, X } from "lucide-react";
import { useRef, useState, type KeyboardEvent } from "react";
import { SeverityIcon } from "@/components/common";
import { Button } from "@/components/ui/button";
import { HoverCard, HoverCardContent, HoverCardTrigger, Tooltip } from "@/components/ui/overlays";
import { AutoTextarea, Badge, Card, Input } from "@/components/ui/primitives";
import type { FactInfo, LintIssue, LintResult, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";
import { newBullet, type Draft, type EditableBullet } from "./draft";

type Update = (fn: (d: Draft) => Draft) => void;

const WORST: Severity[] = ["error", "warning", "info"];
function worst(issues: LintIssue[] | undefined): Severity | null {
  if (!issues?.length) return null;
  return WORST.find((s) => issues.some((i) => i.severity === s)) ?? null;
}

function IssueBadge({ issues }: { issues: LintIssue[] | undefined }) {
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

function CitationChip({ id, fact }: { id: string; fact: FactInfo | undefined }) {
  return (
    <HoverCard openDelay={150} closeDelay={80}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex h-5 items-center gap-1 rounded border px-1.5 font-mono text-[10.5px] font-medium transition-colors",
            fact ? "border-primary/25 bg-primary/[0.06] text-primary hover:bg-primary/10" : "border-destructive/30 text-destructive",
          )}
        >
          <Link2 className="size-3" />
          {id}
        </button>
      </HoverCardTrigger>
      <HoverCardContent align="start" className="w-80">
        {fact ? (
          <>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-mono font-medium text-primary">{id}</span>
              <span>·</span>
              <span className="truncate">{fact.employer}</span>
              <Badge variant="secondary" className="ml-auto capitalize">
                {fact.kind}
              </Badge>
            </div>
            <p className="mt-2 flex gap-2 text-sm leading-relaxed">
              <Quote className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
              {fact.text}
            </p>
            <p className="mt-2 text-[11px] text-muted-foreground">This bullet is built from this fact in your fact bank.</p>
          </>
        ) : (
          <p className="text-sm text-destructive">{id} isn't in your fact bank anymore.</p>
        )}
      </HoverCardContent>
    </HoverCard>
  );
}

function BulletRow({
  bullet,
  issues,
  facts,
  onChange,
  onRemove,
  onEnter,
  onBackspaceEmpty,
  onRemoveCitation,
  autoFocus,
}: {
  bullet: EditableBullet;
  issues: LintIssue[] | undefined;
  facts: Record<string, FactInfo> | undefined;
  onChange: (text: string) => void;
  onRemove: () => void;
  onEnter: () => void;
  onBackspaceEmpty: () => void;
  onRemoveCitation: (id: string) => void;
  autoFocus: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: bullet._key });
  const [focused, setFocused] = useState(false);
  const sev = worst(issues);

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onEnter();
    } else if (e.key === "Backspace" && !bullet.text) {
      e.preventDefault();
      onBackspaceEmpty();
    }
  };

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "group relative flex gap-1.5 rounded-lg py-1 pr-1 transition-colors",
        isDragging && "z-10 bg-card shadow-lift ring-1 ring-border",
        sev === "error" && "bg-destructive/[0.04]",
      )}
    >
      <button
        type="button"
        className="mt-2 flex h-6 w-5 shrink-0 cursor-grab touch-none items-center justify-center rounded text-muted-foreground/50 opacity-0 transition-opacity hover:bg-secondary hover:text-foreground focus-visible:opacity-100 group-hover:opacity-100 active:cursor-grabbing"
        aria-label="Drag to reorder"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="size-3.5" />
      </button>
      <span className="mt-[15px] size-1.5 shrink-0 rounded-full bg-foreground/40" />
      <div className="min-w-0 flex-1">
        <AutoTextarea
          autoFocus={autoFocus}
          value={bullet.text}
          onChange={(e) => onChange(e.target.value.replace(/\n/g, " "))}
          onKeyDown={onKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Describe a real accomplishment..."
          aria-invalid={sev === "error"}
          className={cn(
            "border-transparent bg-transparent px-2 shadow-none hover:border-input focus-visible:bg-background",
            sev === "error" && "border-destructive/40",
          )}
        />
        {(bullet.ids.length > 0 || issues?.length || focused) && (
          <div className="mt-1 flex flex-wrap items-center gap-1.5 px-2">
            {bullet.ids.map((id) => (
              <span key={id} className="group/chip inline-flex items-center">
                <CitationChip id={id} fact={facts?.[id]} />
                <button
                  type="button"
                  onClick={() => onRemoveCitation(id)}
                  className="-ml-0.5 hidden rounded p-0.5 text-muted-foreground hover:text-destructive group-hover/chip:inline-flex"
                  aria-label={`Unlink ${id}`}
                >
                  <X className="size-3" />
                </button>
              </span>
            ))}
            <IssueBadge issues={issues} />
            {focused && (
              <span className={cn("ml-auto text-[11px] tabular-nums text-muted-foreground", bullet.text.length > 240 && "text-warning")}>
                {bullet.text.length} chars
              </span>
            )}
          </div>
        )}
      </div>
      <Tooltip content="Remove bullet">
        <Button
          variant="ghost"
          size="icon-sm"
          className="mt-1 size-7 shrink-0 text-muted-foreground opacity-0 hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
          onClick={onRemove}
          aria-label="Remove bullet"
        >
          <Trash2 className="size-3.5" />
        </Button>
      </Tooltip>
    </li>
  );
}

function ExperienceCard({
  index,
  draft,
  update,
  lint,
  facts,
}: {
  index: number;
  draft: Draft;
  update: Update;
  lint: LintResult | undefined;
  facts: Record<string, FactInfo> | undefined;
}) {
  const job = draft.experience[index];
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const setBullets = (fn: (b: EditableBullet[]) => EditableBullet[]) =>
    update((d) => ({
      ...d,
      experience: d.experience.map((e, i) => (i === index ? { ...e, bullets: fn(e.bullets) } : e)),
    }));

  const insertAfter = (pos: number) => {
    const b = newBullet();
    setFocusKey(b._key);
    setBullets((list) => [...list.slice(0, pos + 1), b, ...list.slice(pos + 1)]);
  };

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    setBullets((list) => {
      const from = list.findIndex((b) => b._key === active.id);
      const to = list.findIndex((b) => b._key === over.id);
      return arrayMove(list, from, to);
    });
  };

  const issuesCount = job.bullets.reduce((n, _b, b) => n + (lint?.bullets[`${index}.${b}`]?.filter((i) => i.severity !== "info").length ?? 0), 0);

  return (
    <Card className="overflow-hidden">
      <div className="flex items-start gap-3 border-b bg-muted/30 px-4 py-3">
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold">{job.company}</div>
          <div className="truncate text-xs text-muted-foreground">
            {job.title} · {job.dates}
            {job.location && ` · ${job.location}`}
          </div>
        </div>
        {issuesCount > 0 && <Badge variant="warning">{issuesCount} to review</Badge>}
        <Badge variant="secondary">{job.bullets.length} bullets</Badge>
      </div>
      <div className="px-2 py-2">
        <DndContext sensors={sensors} collisionDetection={closestCenter} modifiers={[restrictToVerticalAxis]} onDragEnd={onDragEnd}>
          <SortableContext items={job.bullets.map((b) => b._key)} strategy={verticalListSortingStrategy}>
            <ul className="grid gap-0.5">
              {job.bullets.map((b, bi) => (
                <BulletRow
                  key={b._key}
                  bullet={b}
                  autoFocus={focusKey === b._key}
                  issues={lint?.bullets[`${index}.${bi}`]}
                  facts={facts}
                  onChange={(text) => setBullets((list) => list.map((x) => (x._key === b._key ? { ...x, text } : x)))}
                  onRemove={() => setBullets((list) => list.filter((x) => x._key !== b._key))}
                  onEnter={() => insertAfter(bi)}
                  onBackspaceEmpty={() => {
                    const prev = job.bullets[bi - 1];
                    setBullets((list) => list.filter((x) => x._key !== b._key));
                    if (prev) setFocusKey(prev._key);
                  }}
                  onRemoveCitation={(id) =>
                    setBullets((list) => list.map((x) => (x._key === b._key ? { ...x, ids: x.ids.filter((i) => i !== id) } : x)))
                  }
                />
              ))}
            </ul>
          </SortableContext>
        </DndContext>
        <Button variant="ghost" size="sm" className="ml-7 mt-1 text-muted-foreground" onClick={() => insertAfter(job.bullets.length - 1)}>
          <Plus /> Add bullet
        </Button>
      </div>
    </Card>
  );
}

function SkillsEditor({ draft, update, lint }: { draft: Draft; update: Update; lint: LintResult | undefined }) {
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
