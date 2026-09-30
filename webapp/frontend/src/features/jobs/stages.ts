import type { JobSummary } from "@/lib/types";

export interface StepDef {
  key: string;
  label: string;
  detail: string;
}

const STEP_LIBRARY: Record<string, StepDef> = {
  preparing: { key: "preparing", label: "Reading your materials", detail: "Profile, base resume, fact bank, and the posting" },
  drafting: { key: "drafting", label: "Drafting with Claude", detail: "Tailoring the summary, bullets, and skills to this role" },
  structuring: { key: "structuring", label: "Structuring the draft", detail: "Turning the draft into editable content" },
  validating: { key: "validating", label: "Truthfulness checks", detail: "Citations, numbers, never-claim list, keyword coverage" },
  cover_letter: { key: "cover_letter", label: "Writing the cover letter", detail: "Built only from the validated resume content" },
  rendering: { key: "rendering", label: "Laying out the document", detail: "Applying your template to a Word document" },
  pdf: { key: "pdf", label: "Exporting the PDF", detail: "Microsoft Word renders the final PDF" },
};

export function stepsFor(job: Pick<JobSummary, "kind" | "stages_seen">, opts: { coverLetter?: boolean } = {}): StepDef[] {
  const keysByKind: Record<string, string[]> = {
    generate: ["preparing", "drafting", "structuring", "validating", ...(opts.coverLetter ? ["cover_letter"] : []), "rendering", "pdf"],
    render: ["preparing", "validating", "rendering", "pdf"],
    fact_bank: ["preparing", "drafting", "validating"],
    ingest: ["preparing", "drafting", "validating"],
  };
  const keys = [...(keysByKind[job.kind] ?? ["preparing"])];
  // A stage the pipeline reported that we didn't predict (e.g. a cover
  // letter) still gets a row, in order.
  for (const seen of job.stages_seen ?? []) {
    if (seen !== "done" && !keys.includes(seen) && STEP_LIBRARY[seen]) {
      const pdfIdx = keys.indexOf("rendering");
      keys.splice(pdfIdx >= 0 ? pdfIdx : keys.length, 0, seen);
    }
  }
  return keys.map((k) => STEP_LIBRARY[k]);
}

export type StepState = "done" | "active" | "failed" | "pending" | "skipped";

/**
 * Where each step stands, from the job's current stage and status. Pure, so
 * the stepper's behavior is unit-tested without a server.
 */
export function stepStates(steps: StepDef[], job: Pick<JobSummary, "status" | "stage" | "stages_seen"> | null): StepState[] {
  if (!job) return steps.map(() => "pending");
  const keys = steps.map((s) => s.key);
  const seen = new Set(job.stages_seen ?? []);
  const current = keys.indexOf(job.stage);
  const furthest = Math.max(current, ...keys.map((k, i) => (seen.has(k) ? i : -1)));

  return steps.map((step, i) => {
    // Every "::stage" line is recorded, so a step never seen on a successful
    // run genuinely didn't happen (e.g. no Word, so no PDF export).
    if (job.status === "succeeded") return seen.has(step.key) || i === 0 ? "done" : "skipped";
    if (job.status === "queued") return "pending";
    if (i < furthest) return "done";
    if (i === furthest) {
      if (job.status === "failed" || job.status === "cancelled") return "failed";
      return "active";
    }
    return "pending";
  });
}

export function progressPercent(states: StepState[]): number {
  if (!states.length) return 0;
  const done = states.filter((s) => s === "done" || s === "skipped").length;
  const active = states.includes("active") ? 0.5 : 0;
  return Math.round(((done + active) / states.length) * 100);
}
