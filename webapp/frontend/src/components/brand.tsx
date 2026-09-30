/**
 * Resume Taylor's decorative flourishes: palette beads strung like a
 * friendship bracelet, and sequin sparkles. Purely visual, so every piece is
 * aria-hidden. See docs/brand/BRAND.md for the palette and usage rules.
 */
import type { CSSProperties } from "react";
import { cn } from "@/lib/utils";

/** The bead colors, in stringing order. Literal class names so Tailwind keeps them. */
const BEADS = ["bg-brand-sage", "bg-brand-gold", "bg-brand-lilac", "bg-brand-sky", "bg-brand-pink", "bg-brand-tan"] as const;

/** A palette swatch picked by a stable hash, for company monograms. */
export const SWATCHES = ["sage", "gold", "lilac", "sky", "pink", "tan"] as const;

const SIZES = {
  sm: { bead: "size-2", cube: "h-4 min-w-4 text-[9px]", gap: "gap-[2px]" },
  md: { bead: "size-3", cube: "h-6 min-w-6 text-[11px]", gap: "gap-[3px]" },
} as const;

/**
 * A strand of round beads with optional letter cubes in the middle, the way
 * friendship bracelets spell a word. Spaces become an extra round bead.
 */
export function BeadBracelet({
  text,
  beads = 3,
  size = "md",
  className,
}: {
  text?: string;
  beads?: number;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const s = SIZES[size];
  const letters = text ? [...text.toUpperCase().slice(0, 12)] : [];
  let n = 0;
  const round = (key: string) => <span key={key} className={cn("shrink-0 rounded-full shadow-sm ring-1 ring-black/10", s.bead, BEADS[n++ % BEADS.length])} />;
  return (
    <div aria-hidden className={cn("relative inline-flex items-center px-1", className)}>
      <span className="absolute inset-x-0 top-1/2 h-[1.5px] -translate-y-1/2 rounded-full bg-foreground/25" />
      <span className={cn("relative flex items-center", s.gap)}>
        {Array.from({ length: beads }, (_, i) => round(`a${i}`))}
        {letters.map((ch, i) =>
          ch.trim() ? (
            <span
              key={`l${i}`}
              className={cn(
                "flex shrink-0 items-center justify-center rounded-[5px] bg-[#FBF8F4] px-1 font-bold leading-none text-brand-navy shadow-sm ring-1 ring-black/10",
                s.cube,
              )}
            >
              {ch}
            </span>
          ) : (
            round(`s${i}`)
          ),
        )}
        {Array.from({ length: beads }, (_, i) => round(`b${i}`))}
      </span>
    </div>
  );
}

export function SparkleStar({ className, style }: { className?: string; style?: CSSProperties }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className={className} style={style}>
      <path d="M12 0l2.7 9.3L24 12l-9.3 2.7L12 24l-2.7-9.3L0 12l9.3-2.7z" fill="currentColor" />
    </svg>
  );
}

/** Where the sequins sit, as percentages of the parent, with a size and color each. */
const SEQUINS = [
  { top: "12%", left: "8%", size: 14, color: "text-brand-gold", delay: "0s" },
  { top: "22%", left: "88%", size: 10, color: "text-brand-sky", delay: "0.9s" },
  { top: "70%", left: "93%", size: 16, color: "text-brand-pink", delay: "1.6s" },
  { top: "80%", left: "4%", size: 9, color: "text-brand-lilac", delay: "0.4s" },
  { top: "6%", left: "62%", size: 8, color: "text-brand-sage", delay: "2.1s" },
] as const;

/**
 * A few twinkling sequins scattered over a positioned parent. The twinkle is
 * switched off by the reduced-motion rule in index.css.
 */
export function Sequins({ className, count = SEQUINS.length }: { className?: string; count?: number }) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      {SEQUINS.slice(0, count).map((q, i) => (
        <SparkleStar
          key={i}
          className={cn("absolute animate-twinkle", q.color)}
          style={{ top: q.top, left: q.left, width: q.size, height: q.size, animationDelay: q.delay }}
        />
      ))}
    </div>
  );
}
