import { Check, CircleAlert, Cloud, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type SaveState = "saved" | "dirty" | "saving" | "error";

export function SaveIndicator({ state }: { state: SaveState }) {
  const map = {
    saved: { icon: Check, text: "Saved", cls: "text-muted-foreground" },
    dirty: { icon: Cloud, text: "Unsaved", cls: "text-muted-foreground" },
    saving: { icon: Loader2, text: "Saving", cls: "text-muted-foreground [&_svg]:animate-spin" },
    error: { icon: CircleAlert, text: "Not saved", cls: "text-destructive" },
  }[state];
  const Icon = map.icon;
  return (
    <span className={cn("mr-1 flex items-center gap-1.5 text-xs", map.cls)} aria-live="polite">
      <Icon className="size-3.5" /> {map.text}
    </span>
  );
}
