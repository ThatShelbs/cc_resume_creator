/**
 * Upload, then (optionally Claude-assisted) structure, then review, then
 * confirm. Shared by the Base Resume page and the onboarding wizard.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, PenLine, Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Callout } from "@/components/common";
import { Button } from "@/components/ui/button";
import { useJobs } from "@/features/jobs/JobCenter";
import { api } from "@/lib/api";
import { keys } from "@/lib/queries";
import type { JobSummary, ResumeStructure, UploadResult } from "@/lib/types";
import { cleanStructure, ReviewForm } from "./ReviewForm";
import { ResumeDropzone } from "./ResumeUpload";

export type Prefill = UploadResult["prefill"];

const EMPTY: ResumeStructure = {
  summary: "",
  education: [],
  jobs: [{ company: "", location: "", dates: "", title: "", bullets: [""] }],
  other_sections: [],
  flags: [],
  source: "manual",
  source_file: "",
  raw_text: "",
  contact_lines: [],
};

export function ResumeFlow({
  initial,
  initialUpload,
  onConfirmed,
  onCancel,
  confirmLabel = "Save as my base resume",
}: {
  initial?: ResumeStructure | null;
  initialUpload?: UploadResult | null;
  onConfirmed?: (prefill: Prefill | null) => void;
  onCancel?: () => void;
  confirmLabel?: string;
}) {
  const qc = useQueryClient();
  const { track } = useJobs();
  const [upload, setUpload] = useState<UploadResult | null>(initialUpload ?? null);
  const [structure, setStructure] = useState<ResumeStructure | null>(
    initial ?? (initialUpload && !initialUpload.needs_ai ? initialUpload.structure : null),
  );
  const [prefill, setPrefill] = useState<Prefill | null>(initialUpload?.prefill ?? null);
  const [aiRunning, setAiRunning] = useState(false);

  const onUploaded = (r: UploadResult) => {
    setUpload(r);
    setPrefill(r.prefill);
    if (!r.needs_ai) {
      setStructure(r.structure);
      toast.success(`Found ${r.structure.jobs.length} employer${r.structure.jobs.length === 1 ? "" : "s"}`, {
        description: "Review the details below, then save.",
      });
    } else {
      setStructure(null);
    }
  };

  const useAi = async () => {
    if (!upload) return;
    setAiRunning(true);
    try {
      const job = await api.post<JobSummary>(`/api/resume/ai/${upload.upload_id}`);
      track(job, {
        title: "Structuring your resume",
        successMessage: "Resume structured. Review it before saving.",
        onSuccess: (j) => {
          setAiRunning(false);
          const res = j.result as { structure: ResumeStructure; prefill: Prefill } | null;
          if (res) {
            setStructure(res.structure);
            setPrefill((p) => ({ ...res.prefill, ...Object.fromEntries(Object.entries(p ?? {}).filter(([, v]) => (Array.isArray(v) ? v.length : v))) }) as Prefill);
          }
        },
        onFailure: () => setAiRunning(false),
      });
    } catch (e) {
      setAiRunning(false);
      toast.error((e as Error).message);
    }
  };

  const confirm = useMutation({
    mutationFn: (s: ResumeStructure) =>
      api.post<{ file: string; fact_bank_issues: { id: string; employer: string }[] }>("/api/resume/confirm", {
        structure: cleanStructure(s),
        upload_id: upload?.upload_id,
      }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: keys.resume });
      qc.invalidateQueries({ queryKey: keys.system });
      qc.invalidateQueries({ queryKey: keys.facts });
      qc.invalidateQueries({ queryKey: keys.projects });
      toast.success("Base resume saved", { description: `resume_input/${r.file}` });
      if (r.fact_bank_issues.length)
        toast.warning(`${r.fact_bank_issues.length} fact(s) in your fact bank name an employer that's no longer on your resume`, {
          description: "Update them under Evidence so they stay citable.",
          duration: 10_000,
        });
      onConfirmed?.(prefill);
    },
    onError: (e) => toast.error("Couldn't save", { description: (e as Error).message }),
  });

  if (!structure) {
    return (
      <div className="grid gap-4">
        {upload?.needs_ai ? (
          <Callout
            tone="warning"
            title="We couldn't map this layout automatically"
            action={
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setStructure({ ...EMPTY, source_file: upload.structure.source_file })}>
                  <PenLine /> Fill in by hand
                </Button>
                <Button size="sm" loading={aiRunning} onClick={useAi}>
                  <Sparkles /> Structure with Claude
                </Button>
              </div>
            }
          >
            Claude can extract employers, titles, dates, and bullets word-for-word (one short call). Every field is then checked against
            your file and flagged if it doesn't match.
          </Callout>
        ) : null}
        <ResumeDropzone onUploaded={onUploaded} />
        {onCancel && (
          <div>
            <Button variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="grid gap-5">
      {structure.source_file && (
        <p className="text-xs text-muted-foreground">
          From <span className="font-medium text-foreground">{structure.source_file.replace(/^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}_/, "")}</span>
          {structure.source === "ai" ? ", structured by Claude" : structure.source === "heuristic" ? ", read automatically" : ""}.
        </p>
      )}
      <ReviewForm value={structure} onChange={setStructure} />
      <div className="sticky bottom-4 z-20 flex flex-wrap items-center justify-end gap-2 rounded-xl border bg-popover/95 px-4 py-3 shadow-lift backdrop-blur">
        <span className="mr-auto text-xs text-muted-foreground">
          {structure.flags.length ? `${structure.flags.length} flagged field(s) left to check` : "Everything checks out"}
        </span>
        <Button
          variant="ghost"
          onClick={() => {
            setStructure(initial ?? null);
            setUpload(null);
            onCancel?.();
          }}
        >
          Cancel
        </Button>
        <Button loading={confirm.isPending} onClick={() => confirm.mutate(structure)}>
          <Check /> {confirmLabel}
        </Button>
      </div>
    </div>
  );
}
