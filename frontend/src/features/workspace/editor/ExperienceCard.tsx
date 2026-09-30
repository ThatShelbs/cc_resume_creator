import { closestCenter, DndContext, KeyboardSensor, PointerSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/primitives";
import type { FactInfo, LintResult } from "@/lib/api/types";
import { newBullet, type Draft, type EditableBullet } from "@/features/workspace/draft";
import { Update } from "@/features/workspace/editor/types";
import { BulletRow } from "@/features/workspace/editor/BulletRow";

export function ExperienceCard({
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
