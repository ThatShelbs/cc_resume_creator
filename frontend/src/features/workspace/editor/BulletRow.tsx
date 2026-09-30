import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Trash2, X } from "lucide-react";
import { useState, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/overlays";
import { AutoTextarea } from "@/components/ui/primitives";
import type { FactInfo, LintIssue } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { type EditableBullet } from "@/features/workspace/draft";
import { worst, IssueBadge } from "@/features/workspace/editor/IssueBadge";
import { CitationChip } from "@/features/workspace/editor/CitationChip";

export function BulletRow({
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
