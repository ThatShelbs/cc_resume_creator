import { PenLine } from "lucide-react";
import { useEffect, useState } from "react";
import { Input } from "@/components/ui/primitives";

export function EditableTitle({ value, onSave }: { value: string; onSave: (v: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(value);
  useEffect(() => setText(value), [value]);
  const commit = () => {
    setEditing(false);
    const v = text.trim();
    if (v && v !== value) onSave(v);
    else setText(value);
  };
  return editing ? (
    <Input
      autoFocus
      value={text}
      onChange={(e) => setText(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
        if (e.key === "Escape") {
          setText(value);
          setEditing(false);
        }
      }}
      className="h-9 max-w-xl text-xl font-semibold tracking-tight"
      aria-label="Project name"
    />
  ) : (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className="group flex max-w-full items-center gap-2 rounded-md text-left"
      title="Rename"
    >
      <h1 className="line-clamp-2 break-words text-xl font-semibold tracking-tight sm:text-2xl">{value}</h1>
      <PenLine className="size-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
    </button>
  );
}
