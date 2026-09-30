import { Check, Loader2, Scissors, Sparkles } from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";
import { BeadBracelet, Sequins } from "@/components/shared/brand";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/primitives";
import { useSystem } from "@/lib/api/queries";
import type { Project } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/** The company's first word for the ready card's bracelet, letters only. */
export function braceletWord(company: string | null | undefined): string {
  const word = (company ?? "").split(/\s+/)[0]?.replace(/[^\p{L}]/gu, "") ?? "";
  return word.length >= 2 && word.length <= 9 ? word : "new job";
}

export function ReadyCard({ project, running, disabled, onGenerate }: { project: Project; running: boolean; disabled?: boolean; onGenerate: () => void }) {
  const { data: system } = useSystem();
  const checks = useMemo(
    () => [
      { ok: !!system?.inputs.resume, label: "Base resume", detail: system?.inputs.resume ?? "Needed", to: "/resume" },
      { ok: !!system?.inputs.profile, label: "Profile", detail: system?.inputs.profile ?? "Needed", to: "/profile" },
      {
        ok: !!system?.inputs.fact_bank,
        label: "Fact bank",
        detail: system?.inputs.fact_bank ? `${system.inputs.fact_bank} facts, citations enforced` : "Optional, adds provenance checks",
        to: "/evidence",
        optional: true,
      },
      { ok: true, label: "Template", detail: <span className="capitalize">{project.template}</span>, to: "" },
    ],
    [system, project.template],
  );
  return (
    <Card className="relative overflow-hidden p-6 sm:p-8">
      <div className="absolute -right-24 -top-24 size-64 rounded-full bg-gradient-to-br from-brand-pink/25 to-brand-lilac/15 blur-3xl" />
      <Sequins count={3} />
      <div className="relative">
        <div className="flex flex-wrap items-center gap-4">
          <div className="bg-brand-gradient flex size-12 items-center justify-center rounded-2xl shadow-lift">
            <Scissors className="size-5" />
          </div>
          <BeadBracelet text={braceletWord(project.company)} size="sm" />
        </div>
        <h2 className="mt-5 text-xl font-semibold tracking-tight">
          Ready to tailor {project.role ? `for ${project.role}` : "this resume"}
        </h2>
        <p className="mt-1.5 max-w-lg text-sm leading-relaxed text-muted-foreground">
          Claude drafts a summary, bullets, and skills from your real experience, then deterministic checks verify every number,
          citation, and claim before anything is written.
        </p>
        <ul className="mt-6 grid gap-2 sm:grid-cols-2">
          {checks.map((c) => (
            <li key={c.label} className="flex items-start gap-2.5 rounded-lg border bg-background/60 px-3 py-2.5">
              <span
                className={cn(
                  "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full",
                  c.ok ? "bg-success text-success-foreground" : c.optional ? "border border-dashed border-muted-foreground/50" : "bg-warning text-warning-foreground",
                )}
              >
                {c.ok ? <Check className="size-3" strokeWidth={3} /> : !c.optional && <span className="text-[10px] font-bold">!</span>}
              </span>
              <div className="min-w-0 text-sm">
                <div className="font-medium">{c.label}</div>
                <div className="truncate text-xs text-muted-foreground">
                  {c.to && !c.ok ? (
                    <Link to={c.to} className="text-primary hover:underline">
                      {c.detail}
                    </Link>
                  ) : (
                    c.detail
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
        <Button variant="gradient" size="lg" className="mt-6" onClick={onGenerate} disabled={running || disabled}>
          {running ? <Loader2 className="animate-spin" /> : <Sparkles />}
          {running ? "Generating..." : "Generate tailored resume"}
        </Button>
      </div>
    </Card>
  );
}
