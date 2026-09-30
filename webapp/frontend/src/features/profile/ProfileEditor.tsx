import { closestCenter, DndContext, KeyboardSensor, PointerSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Plus, Sparkles, Trash2 } from "lucide-react";
import { SortableItems } from "@/components/SortableItems";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/overlays";
import { Badge, Card, Field, Input } from "@/components/ui/primitives";
import type { Profile, ProfileSection } from "@/lib/types";
import { cn, uid } from "@/lib/utils";

const SUGGESTED = ["Leadership", "Projects", "Software/Tools", "Skills", "Recent Awards", "Certifications", "Publications", "Things that make me unique"];
const SKILL_SECTIONS = new Set(["software/tools", "software / tools", "tools", "skills"]);

function SectionCard({
  section,
  onChange,
  onRemove,
}: {
  section: ProfileSection;
  onChange: (s: ProfileSection) => void;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: section.id });
  const feedsSkills = SKILL_SECTIONS.has(section.title.trim().toLowerCase());
  return (
    <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }} className={cn(isDragging && "z-10")}>
      <Card className={cn("group p-4", isDragging && "shadow-lift ring-1 ring-border")}>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="flex size-6 cursor-grab touch-none items-center justify-center rounded text-muted-foreground/60 hover:bg-secondary hover:text-foreground"
            aria-label="Drag section"
            {...attributes}
            {...listeners}
          >
            <GripVertical className="size-4" />
          </button>
          <Input
            value={section.title}
            onChange={(e) => onChange({ ...section, title: e.target.value })}
            className="h-8 max-w-xs border-transparent px-2 text-[15px] font-semibold shadow-none hover:border-input"
            aria-label="Section title"
          />
          {feedsSkills && (
            <Tooltip content="Entries here are matched against each posting: ones the posting names are always kept in the skills list, and they drive keyword coverage.">
              <Badge variant="default" className="cursor-default">
                <Sparkles /> Skills matching
              </Badge>
            </Tooltip>
          )}
          <span className="ml-auto text-xs tabular-nums text-muted-foreground">{section.items.length}</span>
          <Tooltip content="Delete section">
            <Button variant="ghost" size="icon-sm" onClick={onRemove} className="text-muted-foreground hover:text-destructive" aria-label="Delete section">
              <Trash2 className="size-4" />
            </Button>
          </Tooltip>
        </div>
        <div className="mt-2 pl-1">
          <SortableItems
            items={section.items}
            onChange={(items) => onChange({ ...section, items })}
            placeholder={feedsSkills ? "e.g. Python" : "Something true, specific, and ideally measurable"}
          />
        </div>
      </Card>
    </div>
  );
}

export function ProfileEditor({ value, onChange }: { value: Profile; onChange: (p: Profile) => void }) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const c = value.contact;
  const setContact = (field: keyof typeof c, v: string) => onChange({ ...value, contact: { ...c, [field]: v } });
  const existing = new Set(value.sections.map((s) => s.title.trim().toLowerCase()));
  const addSection = (title = "New section") =>
    onChange({ ...value, sections: [...value.sections, { id: uid(), title, items: [""] }] });

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const from = value.sections.findIndex((s) => s.id === active.id);
    const to = value.sections.findIndex((s) => s.id === over.id);
    onChange({ ...value, sections: arrayMove(value.sections, from, to) });
  };

  return (
    <div className="grid gap-5">
      <Card className="p-5">
        <h3 className="text-sm font-semibold">Contact</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">Printed at the top of every resume and cover letter.</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="Full name" htmlFor="p-name">
            <Input id="p-name" value={c.name} onChange={(e) => setContact("name", e.target.value)} autoComplete="name" />
          </Field>
          <Field label="Email" htmlFor="p-email">
            <Input id="p-email" type="email" value={c.email} onChange={(e) => setContact("email", e.target.value)} autoComplete="email" />
          </Field>
          <Field label="Phone" htmlFor="p-phone">
            <Input id="p-phone" value={c.phone} onChange={(e) => setContact("phone", e.target.value)} autoComplete="tel" />
          </Field>
          <Field label="Location" htmlFor="p-location" hint="City, State">
            <Input id="p-location" value={c.location} onChange={(e) => setContact("location", e.target.value)} />
          </Field>
          <Field label="LinkedIn" htmlFor="p-linkedin" hint="Optional. Becomes a clickable link." className="sm:col-span-2">
            <Input id="p-linkedin" value={c.linkedin} onChange={(e) => setContact("linkedin", e.target.value)} placeholder="linkedin.com/in/you" />
          </Field>
        </div>
      </Card>

      <DndContext sensors={sensors} collisionDetection={closestCenter} modifiers={[restrictToVerticalAxis]} onDragEnd={onDragEnd}>
        <SortableContext items={value.sections.map((s) => s.id)} strategy={verticalListSortingStrategy}>
          <div className="grid gap-4">
            {value.sections.map((s) => (
              <SectionCard
                key={s.id}
                section={s}
                onChange={(next) => onChange({ ...value, sections: value.sections.map((x) => (x.id === s.id ? next : x)) })}
                onRemove={() => onChange({ ...value, sections: value.sections.filter((x) => x.id !== s.id) })}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-dashed p-4">
        <Button variant="outline" size="sm" onClick={() => addSection()}>
          <Plus /> Add section
        </Button>
        {SUGGESTED.filter((t) => !existing.has(t.toLowerCase())).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => addSection(t)}
            className="rounded-full border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
          >
            + {t}
          </button>
        ))}
      </div>
    </div>
  );
}
