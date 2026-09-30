import { CheckCircle2, ChevronDown, FileText, Gauge, ShieldCheck } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { SeverityIcon } from "@/components/common";
import { Tooltip } from "@/components/ui/overlays";
import { Badge, Card, Skeleton } from "@/components/ui/primitives";
import { useReport } from "@/lib/queries";
import type { LintResult, ResumeResult } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

function CoverageRing({ covered, total }: { covered: number; total: number }) {
  const pct = total ? covered / total : 1;
  const r = 34;
  const c = 2 * Math.PI * r;
  const tone = pct >= 0.75 ? "text-success" : pct >= 0.5 ? "text-warning" : "text-destructive";
  return (
    <div className="relative size-24 shrink-0">
      <svg viewBox="0 0 80 80" className="size-24 -rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" strokeWidth="7" className="stroke-secondary" />
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          strokeWidth="7"
          strokeLinecap="round"
          stroke="currentColor"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          className={cn("transition-[stroke-dashoffset] duration-700 ease-out", tone)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-semibold tabular-nums tracking-tight">{Math.round(pct * 100)}%</span>
        <span className="text-[10px] text-muted-foreground">
          {covered}/{total} terms
        </span>
      </div>
    </div>
  );
}

export function InsightsPanel({ pid, result, lint }: { pid: string; result: ResumeResult; lint: LintResult | undefined }) {
  const covered = result.coverage?.covered ?? [];
  const missing = result.coverage?.missing ?? [];
  const warnings = result.warnings ?? [];
  const genWarnings = (result.generation_warnings ?? []).filter((w) => !warnings.includes(w));
  const [showReport, setShowReport] = useState(false);
  const report = useReport(pid, showReport);
  const counts = lint?.counts ?? { error: 0, warning: 0, info: 0 };

  return (
    <div className="grid gap-4">
      <Card className="p-5">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Gauge className="size-4 text-primary" /> Keyword coverage
        </div>
        <div className="mt-4 flex flex-col gap-5 sm:flex-row sm:items-center">
          <CoverageRing covered={covered.length} total={covered.length + missing.length} />
          <div className="min-w-0 flex-1 text-sm">
            <p className="leading-relaxed text-muted-foreground">
              Terms from the posting that you <em>genuinely have</em> (from your profile's skills and your fact bank's tags). Missing
              ones are honest gaps to consider, never an invitation to claim something new.
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {covered.map((t) => (
                <Badge key={t} variant="success">
                  <CheckCircle2 /> {t}
                </Badge>
              ))}
              {missing.map((t) => (
                <Tooltip key={t} content="In your materials and the posting, but not in this resume. Work it into a bullet only if it's true for that role.">
                  <Badge variant="outline" className="border-dashed">
                    {t}
                  </Badge>
                </Tooltip>
              ))}
              {!covered.length && !missing.length && <span className="text-xs text-muted-foreground">No overlapping terms found.</span>}
            </div>
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <ShieldCheck className="size-4 text-primary" /> Truthfulness checks
          <span className="ml-auto flex gap-1.5">
            {counts.error > 0 && <Badge variant="destructive">{counts.error} blocking</Badge>}
            <Badge variant={counts.warning ? "warning" : "success"}>{counts.warning} to review</Badge>
          </span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Re-checked live as you edit: numbers against your materials, citations against your fact bank, and every line against
          your never-claim list.
        </p>
        {warnings.length > 0 ? (
          <ul className="mt-4 grid gap-2">
            {warnings.map((w, i) => (
              <li key={i} className="flex gap-2 rounded-md bg-muted/50 px-3 py-2 text-[13px] leading-snug">
                <SeverityIcon severity="warning" className="mt-0.5" />
                <span>{w}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="mt-4 flex items-center gap-2 rounded-md bg-success/[0.07] px-3 py-2 text-[13px] text-success">
            <CheckCircle2 className="size-4" /> The last render passed every check.
          </div>
        )}
        {genWarnings.length > 0 && (
          <details className="group mt-3">
            <summary className="cursor-pointer list-none text-xs font-medium text-muted-foreground hover:text-foreground">
              <ChevronDown className="mr-1 inline size-3.5 transition-transform group-open:rotate-180" />
              {genWarnings.length} note{genWarnings.length > 1 ? "s" : ""} from generation (e.g. dropped bullets)
            </summary>
            <ul className="mt-2 grid gap-1.5">
              {genWarnings.map((w, i) => (
                <li key={i} className="rounded-md border px-3 py-1.5 text-xs text-muted-foreground">
                  {w}
                </li>
              ))}
            </ul>
          </details>
        )}
      </Card>

      <Card className="grid grid-cols-2 gap-4 p-5 text-sm sm:grid-cols-4">
        <Stat label="Pages" value={result.page_count ?? "n/a"} />
        <Stat label="Template" value={<span className="capitalize">{result.template ?? "classic"}</span>} />
        <Stat label="Model" value={`${result.model ?? "?"} · ${result.effort ?? "?"}`} />
        <Stat label="Generated" value={formatDate(result.generated_at, true) || "n/a"} />
      </Card>

      <Card className="overflow-hidden">
        <button
          type="button"
          onClick={() => setShowReport((v) => !v)}
          className="flex w-full items-center gap-2 px-5 py-4 text-left text-sm font-semibold transition-colors hover:bg-muted/40"
        >
          <FileText className="size-4 text-primary" /> Full tailoring report
          <span className="ml-2 text-xs font-normal text-muted-foreground">inputs, provenance for every bullet, and the raw draft</span>
          <ChevronDown className={cn("ml-auto size-4 transition-transform", showReport && "rotate-180")} />
        </button>
        {showReport && (
          <div className="border-t px-5 py-4">
            {report.isLoading ? (
              <div className="grid gap-2">
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-5/6" />
              </div>
            ) : report.error ? (
              <p className="text-sm text-muted-foreground">No report yet. It's written with every render.</p>
            ) : (
              <article className="prose prose-sm max-w-none dark:prose-invert prose-headings:tracking-tight prose-pre:max-h-80 prose-pre:overflow-auto prose-pre:text-xs">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.data ?? ""}</ReactMarkdown>
              </article>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-0.5 truncate font-medium">{value}</div>
    </div>
  );
}
