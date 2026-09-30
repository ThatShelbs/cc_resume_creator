import { Check } from "lucide-react";
import { useSystem } from "@/lib/api/queries";
import type { TemplateKey } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const FALLBACK = [
  { key: "classic", label: "Classic", description: "Centered navy header and ruled section headings." },
  { key: "modern", label: "Modern", description: "Left-aligned header with a teal accent." },
  { key: "compact", label: "Compact", description: "Serif, tighter spacing for long careers." },
] as const;

export function TemplatePicker({
  value,
  onChange,
  disabled,
  size = "md",
}: {
  value: TemplateKey;
  onChange: (key: TemplateKey) => void;
  disabled?: boolean;
  size?: "sm" | "md";
}) {
  const { data } = useSystem();
  const templates = data?.templates ?? FALLBACK;
  return (
    <div role="radiogroup" aria-label="Resume template" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {templates.map((t) => {
        const selected = t.key === value;
        return (
          <button
            key={t.key}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            onClick={() => onChange(t.key as TemplateKey)}
            className={cn(
              "group relative flex flex-col overflow-hidden rounded-xl border bg-card text-left shadow-soft transition-all hover:-translate-y-0.5 hover:shadow-lift disabled:pointer-events-none disabled:opacity-60",
              selected ? "border-primary ring-2 ring-primary/25" : "hover:border-foreground/20",
            )}
          >
            <div className={cn("paper-canvas flex items-start justify-center overflow-hidden px-5 pt-4", size === "sm" ? "h-28" : "h-40")}>
              <img
                src={`/templates/${t.key}.png`}
                alt={`${t.label} template preview`}
                loading="lazy"
                className="w-full rounded-t-sm bg-white shadow-paper transition-transform duration-300 group-hover:scale-[1.02]"
              />
            </div>
            <div className="flex items-start gap-2 border-t p-3">
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium">{t.label}</div>
                {size === "md" && <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{t.description}</div>}
              </div>
              <span
                className={cn(
                  "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full border transition-colors",
                  selected ? "border-primary bg-primary text-primary-foreground" : "border-input",
                )}
              >
                {selected && <Check className="size-3" strokeWidth={3} />}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
