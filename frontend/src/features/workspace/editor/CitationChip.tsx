import { Link2, Quote } from "lucide-react";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/overlays";
import { Badge } from "@/components/ui/primitives";
import type { FactInfo } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export function CitationChip({ id, fact }: { id: string; fact: FactInfo | undefined }) {
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
