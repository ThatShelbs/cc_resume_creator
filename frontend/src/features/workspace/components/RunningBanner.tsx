import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { JobSummary } from "@/lib/api/types";

export function RunningBanner({ job, onOpen }: { job: JobSummary; onOpen: () => void }) {
  const stageLabel: Record<string, string> = {
    queued: "Waiting to start",
    preparing: "Reading your materials",
    drafting: "Drafting with Claude",
    structuring: "Structuring the draft",
    validating: "Running truthfulness checks",
    cover_letter: "Writing the cover letter",
    rendering: "Laying out the document",
    pdf: "Exporting the PDF",
    finalizing: "Saving the results",
  };
  return (
    <div className="relative overflow-hidden rounded-lg border border-primary/25 bg-primary/[0.05] px-4 py-3">
      <div className="absolute inset-x-0 bottom-0 h-0.5 overflow-hidden bg-primary/10">
        <div className="h-full w-1/3 animate-[shimmer_1.4s_ease-in-out_infinite] bg-primary/60" style={{ transform: "translateX(-100%)" }} />
      </div>
      <div className="flex items-center gap-3 text-sm">
        <Loader2 className="size-4 animate-spin text-primary" />
        <div className="min-w-0 flex-1">
          <span className="font-medium">{job.kind === "render" ? "Re-rendering" : "Tailoring your resume"}</span>
          <span className="text-muted-foreground"> · {stageLabel[job.stage] ?? job.stage}</span>
        </div>
        <Button size="sm" variant="ghost" onClick={onOpen}>
          View progress
        </Button>
      </div>
    </div>
  );
}
