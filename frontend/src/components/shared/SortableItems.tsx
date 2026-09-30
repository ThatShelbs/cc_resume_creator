/**
 * An editable, drag-to-reorder list of one-line text items. Enter adds an
 * item below, Backspace on an empty item removes it. Used for profile
 * section items and resume bullets.
 */
import { closestCenter, DndContext, KeyboardSensor, PointerSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Plus, X } from "lucide-react";
import { useRef, useState } from "react";
import { cn, uid } from "@/lib/utils";
import { Button } from "../ui/button";
import { AutoTextarea } from "../ui/primitives";

interface Keyed {
  key: string;
  text: string;
}

function Row({
  item,
  placeholder,
  autoFocus,
  flagged,
  onChange,
  onEnter,
  onBackspaceEmpty,
  onRemove,
}: {
  item: Keyed;
  placeholder?: string;
  autoFocus: boolean;
  flagged?: string;
  onChange: (t: string) => void;
  onEnter: () => void;
  onBackspaceEmpty: () => void;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.key });
  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn("group flex items-start gap-1 rounded-md", isDragging && "z-10 bg-card shadow-lift ring-1 ring-border")}
    >
      <button
        type="button"
        className="mt-2 flex h-5 w-5 shrink-0 cursor-grab touch-none items-center justify-center rounded text-muted-foreground/50 opacity-0 hover:text-foreground focus-visible:opacity-100 group-hover:opacity-100"
        aria-label="Drag to reorder"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="size-3.5" />
      </button>
      <div className="min-w-0 flex-1">
        <AutoTextarea
          autoFocus={autoFocus}
          value={item.text}
          placeholder={placeholder}
          aria-invalid={!!flagged}
          onChange={(e) => onChange(e.target.value.replace(/\n/g, " "))}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onEnter();
            } else if (e.key === "Backspace" && !item.text) {
              e.preventDefault();
              onBackspaceEmpty();
            }
          }}
          className={cn("min-h-[34px] py-1.5", flagged && "border-warning/60 bg-warning/[0.04]")}
        />
        {flagged && <p className="mt-1 px-1 text-xs text-warning">{flagged}</p>}
      </div>
      <button
        type="button"
        onClick={onRemove}
        className="mt-1.5 rounded p-1 text-muted-foreground opacity-0 hover:bg-secondary hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
        aria-label="Remove"
      >
        <X className="size-3.5" />
      </button>
    </li>
  );
}

export function SortableItems({
  items,
  onChange,
  placeholder,
  addLabel = "Add item",
  flags,
}: {
  items: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
  addLabel?: string;
  flags?: Record<number, string>;
}) {
  // Stable keys for the current items, kept in step with edits.
  const keysRef = useRef<string[]>([]);
  while (keysRef.current.length < items.length) keysRef.current.push(uid());
  keysRef.current.length = items.length;
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const keyed: Keyed[] = items.map((text, i) => ({ key: keysRef.current[i], text }));

  const insertAt = (pos: number) => {
    const key = uid();
    keysRef.current.splice(pos, 0, key);
    setFocusKey(key);
    onChange([...items.slice(0, pos), "", ...items.slice(pos)]);
  };
  const removeAt = (pos: number) => {
    keysRef.current.splice(pos, 1);
    onChange(items.filter((_, i) => i !== pos));
  };
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const from = keysRef.current.indexOf(String(active.id));
    const to = keysRef.current.indexOf(String(over.id));
    keysRef.current = arrayMove(keysRef.current, from, to);
    onChange(arrayMove(items, from, to));
  };

  return (
    <div>
      <DndContext sensors={sensors} collisionDetection={closestCenter} modifiers={[restrictToVerticalAxis]} onDragEnd={onDragEnd}>
        <SortableContext items={keyed.map((k) => k.key)} strategy={verticalListSortingStrategy}>
          <ul className="grid gap-1">
            {keyed.map((item, i) => (
              <Row
                key={item.key}
                item={item}
                placeholder={placeholder}
                autoFocus={focusKey === item.key}
                flagged={flags?.[i]}
                onChange={(t) => onChange(items.map((x, j) => (j === i ? t : x)))}
                onEnter={() => insertAt(i + 1)}
                onBackspaceEmpty={() => {
                  if (i > 0) setFocusKey(keysRef.current[i - 1]);
                  removeAt(i);
                }}
                onRemove={() => removeAt(i)}
              />
            ))}
          </ul>
        </SortableContext>
      </DndContext>
      <Button type="button" variant="ghost" size="sm" className="ml-5 mt-1 text-muted-foreground" onClick={() => insertAt(items.length)}>
        <Plus /> {addLabel}
      </Button>
    </div>
  );
}
