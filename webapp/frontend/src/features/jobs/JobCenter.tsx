/**
 * Tracks every background job the UI started (or found running on load):
 * streams its progress, shows the progress sheet or a floating indicator,
 * and on completion refreshes the affected data and toasts the outcome.
 */
import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown, CircleSlash, Loader2, TerminalSquare, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Callout } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/overlays";
import { Progress } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { keys } from "@/lib/queries";
import { useJobStream, type JobStream } from "@/lib/sse";
import type { JobSummary } from "@/lib/types";
import { cn } from "@/lib/utils";
import { progressPercent, stepStates, stepsFor, type StepState } from "./stages";

export interface TrackOptions {
  title?: string;
  open?: boolean;
  coverLetter?: boolean;
  successMessage?: string;
  onSuccess?: (job: JobSummary) => void;
  onFailure?: (job: JobSummary) => void;
}

interface Tracked {
  job: JobSummary;
  opts: TrackOptions;
}

interface JobActions {
  track: (job: JobSummary, opts?: TrackOptions) => void;
  open: (jobId: string) => void;
}

const ActionsContext = createContext<JobActions | null>(null);
const StreamsContext = createContext<Record<string, JobStream>>({});

export function useJobs(): JobActions {
  const ctx = useContext(ActionsContext);
  if (!ctx) throw new Error("useJobs must be used inside <JobCenter>");
  return ctx;
}

export function useJobState(jobId: string | null | undefined): JobStream | null {
  const streams = useContext(StreamsContext);
  return jobId ? (streams[jobId] ?? null) : null;
}

function JobWatcher({ id, onUpdate }: { id: string; onUpdate: (id: string, s: JobStream) => void }) {
  const stream = useJobStream(id);
  useEffect(() => onUpdate(id, stream), [id, stream, onUpdate]);
  return null;
}

export function JobCenter({ children }: { children: ReactNode }) {
  const [tracked, setTracked] = useState<Record<string, Tracked>>({});
  const [streams, setStreams] = useState<Record<string, JobStream>>({});
  const [openId, setOpenId] = useState<string | null>(null);
  const finished = useRef(new Set<string>());
  const qc = useQueryClient();
  const navigate = useNavigate();

  const track = useCallback((job: JobSummary, opts: TrackOptions = {}) => {
    setTracked((t) => ({ ...t, [job.id]: { job, opts } }));
    if (opts.open !== false) setOpenId(job.id);
  }, []);

  // Pick up jobs that were already running when the page (re)loaded.
  useEffect(() => {
    api
      .get<JobSummary[]>("/api/jobs")
      .then((jobs) => jobs.forEach((j) => track(j, { open: false })))
      .catch(() => undefined);
  }, [track]);

  const onUpdate = useCallback(
    (id: string, s: JobStream) => {
      setStreams((prev) => (prev[id] === s ? prev : { ...prev, [id]: s }));
      if (!s.done || !s.job || finished.current.has(id)) return;
      finished.current.add(id);
      const entry = tracked[id];
      const job = s.job;
      const pid = job.project_id;
      qc.invalidateQueries({ queryKey: keys.projects });
      qc.invalidateQueries({ queryKey: keys.system });
      if (pid) qc.invalidateQueries({ queryKey: ["project", pid] });
      if (job.kind === "fact_bank") qc.invalidateQueries({ queryKey: keys.facts });

      const view = pid && !location.pathname.includes(pid) ? { label: "Open", onClick: () => navigate(`/projects/${pid}`) } : undefined;
      if (job.status === "succeeded") {
        entry?.opts.onSuccess?.(job);
        toast.success(entry?.opts.successMessage ?? `${job.label}: done`, { action: view });
      } else if (job.status === "failed") {
        entry?.opts.onFailure?.(job);
        toast.error(job.deny?.length ? "Blocked by your never-claim list" : "Something went wrong", {
          description: job.hint ?? job.error ?? undefined,
          action: { label: "Details", onClick: () => setOpenId(id) },
          duration: 10_000,
        });
      }
    },
    [tracked, qc, navigate],
  );

  const actions = useMemo<JobActions>(() => ({ track, open: setOpenId }), [track]);
  const openEntry = openId ? tracked[openId] : null;
  const running = Object.values(tracked).filter((t) => !streams[t.job.id]?.done);
  const indicator = running.find((t) => t.job.id !== openId);

  return (
    <ActionsContext.Provider value={actions}>
      <StreamsContext.Provider value={streams}>
        {children}
        {Object.keys(tracked).map((id) => (
          <JobWatcher key={id} id={id} onUpdate={onUpdate} />
        ))}
        <JobSheet
          entry={openEntry}
          stream={openId ? streams[openId] : undefined}
          onOpenChange={(o) => !o && setOpenId(null)}
        />
        <AnimatePresence>
          {indicator && (
            <FloatingIndicator
              key={indicator.job.id}
              entry={indicator}
              stream={streams[indicator.job.id]}
              onOpen={() => setOpenId(indicator.job.id)}
            />
          )}
        </AnimatePresence>
      </StreamsContext.Provider>
    </ActionsContext.Provider>
  );
}

function useElapsed(job: JobSummary | null | undefined, done: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  const base = useRef<{ at: number; elapsed: number } | null>(null);
  useEffect(() => {
    if (job?.elapsed != null) base.current = { at: Date.now(), elapsed: job.elapsed };
  }, [job?.elapsed, job?.status, job?.stage]);
  useEffect(() => {
    if (done) return;
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, [done]);
  if (!base.current) return 0;
  return done ? base.current.elapsed : base.current.elapsed + (now - base.current.at) / 1000;
}

function fmtElapsed(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return m ? `${m}m ${sec.toString().padStart(2, "0")}s` : `${sec}s`;
}

function StepIcon({ state, index }: { state: StepState; index: number }) {
  if (state === "done")
    return (
      <span className="flex size-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
        <Check className="size-3.5" strokeWidth={3} />
      </span>
    );
  if (state === "active")
    return (
      <span className="relative flex size-6 items-center justify-center">
        <span className="absolute inset-0 animate-pulse-ring rounded-full bg-primary/40" />
        <span className="relative flex size-6 items-center justify-center rounded-full border-2 border-primary bg-background">
          <Loader2 className="size-3.5 animate-spin text-primary" />
        </span>
      </span>
    );
  if (state === "failed")
    return (
      <span className="flex size-6 items-center justify-center rounded-full bg-destructive text-destructive-foreground">
        <X className="size-3.5" strokeWidth={3} />
      </span>
    );
  if (state === "skipped")
    return (
      <span className="flex size-6 items-center justify-center rounded-full border border-dashed text-muted-foreground">
        <CircleSlash className="size-3" />
      </span>
    );
  return (
    <span className="flex size-6 items-center justify-center rounded-full border bg-background text-[11px] font-medium text-muted-foreground">
      {index + 1}
    </span>
  );
}

export function JobSheet({
  entry,
  stream,
  onOpenChange,
}: {
  entry: Tracked | null;
  stream: JobStream | undefined;
  onOpenChange: (open: boolean) => void;
}) {
  const job = stream?.job ?? entry?.job ?? null;
  const done = !!stream?.done;
  const elapsed = useElapsed(job, done);
  const [showLog, setShowLog] = useState(false);
  const logRef = useRef<HTMLPreElement>(null);
  const lines = stream?.lines ?? [];

  useEffect(() => {
    if (showLog && logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [lines.length, showLog]);

  if (!entry || !job) return <Sheet open={false} onOpenChange={onOpenChange} />;

  const steps = stepsFor(job, { coverLetter: entry.opts.coverLetter });
  const states = stepStates(steps, job);
  const pct = progressPercent(states);
  const cancel = async () => {
    try {
      await api.post(`/api/jobs/${job.id}/cancel`);
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <Sheet open onOpenChange={onOpenChange}>
      <SheetContent aria-describedby={undefined} className="sm:max-w-md">
        <div className="border-b px-6 pb-5 pt-6">
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {job.status === "succeeded" ? "Finished" : job.status === "failed" ? "Stopped" : job.status === "cancelled" ? "Cancelled" : "Working"}
          </div>
          <h2 className="mt-1 pr-8 text-lg font-semibold tracking-tight">{entry.opts.title ?? job.label}</h2>
          <div className="mt-4 flex items-center gap-3">
            <Progress
              value={job.status === "succeeded" ? 100 : pct}
              className="h-1.5"
              indicatorClassName={cn(job.status === "failed" && "bg-destructive", job.status === "succeeded" && "bg-success")}
            />
            <span className="w-14 shrink-0 text-right text-xs tabular-nums text-muted-foreground">{fmtElapsed(elapsed)}</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <ol className="relative grid gap-5">
            {steps.map((step, i) => (
              <li key={step.key} className="relative flex gap-3.5">
                {i < steps.length - 1 && (
                  <span
                    className={cn(
                      "absolute left-3 top-7 h-[calc(100%-0.25rem)] w-px -translate-x-1/2",
                      states[i] === "done" ? "bg-primary/60" : "bg-border",
                    )}
                  />
                )}
                <StepIcon state={states[i]} index={i} />
                <div className="min-w-0 pt-0.5">
                  <div
                    className={cn(
                      "text-sm font-medium leading-tight",
                      states[i] === "pending" && "text-muted-foreground",
                      states[i] === "skipped" && "text-muted-foreground line-through decoration-muted-foreground/40",
                    )}
                  >
                    {step.label}
                  </div>
                  <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{step.detail}</div>
                </div>
              </li>
            ))}
          </ol>

          {job.status === "failed" && (
            <Callout tone="error" title={job.deny?.length ? "Blocked by your never-claim list" : "The run stopped"} className="mt-6">
              <span className="whitespace-pre-wrap">{job.hint ?? job.error}</span>
              {job.deny?.length > 0 && (
                <ul className="mt-2 grid gap-1.5">
                  {job.deny.map((d, i) => (
                    <li key={i} className="rounded-md bg-background/70 px-2 py-1 text-xs">
                      <span className="font-medium text-foreground">{d.where}</span>: matched <code>{d.pattern}</code>
                    </li>
                  ))}
                </ul>
              )}
            </Callout>
          )}

          <button
            type="button"
            onClick={() => setShowLog((v) => !v)}
            className="mt-6 flex w-full items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <TerminalSquare className="size-3.5" />
            Live log ({lines.length} lines)
            <ChevronDown className={cn("ml-auto size-3.5 transition-transform", showLog && "rotate-180")} />
          </button>
          {showLog && (
            <pre
              ref={logRef}
              className="mt-2 max-h-72 overflow-auto rounded-lg border bg-muted/50 p-3 font-mono text-[11px] leading-relaxed text-muted-foreground"
            >
              {lines.length ? lines.join("\n") : "Waiting for output..."}
            </pre>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t px-6 py-4">
          {!done && (
            <Button variant="ghost" onClick={cancel}>
              Cancel run
            </Button>
          )}
          <Button variant={done ? "default" : "outline"} onClick={() => onOpenChange(false)}>
            {done ? "Close" : "Run in background"}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function FloatingIndicator({ entry, stream, onOpen }: { entry: Tracked; stream: JobStream | undefined; onOpen: () => void }) {
  const job = stream?.job ?? entry.job;
  const steps = stepsFor(job, { coverLetter: entry.opts.coverLetter });
  const states = stepStates(steps, job);
  const active = steps[states.indexOf("active")];
  return (
    <motion.button
      type="button"
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 16, scale: 0.96 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      onClick={onOpen}
      className="fixed bottom-5 right-5 z-40 flex max-w-[calc(100vw-2.5rem)] items-center gap-3 rounded-full border bg-popover py-2 pl-2 pr-4 text-left shadow-lift transition-colors hover:bg-secondary"
    >
      <span className="flex size-8 items-center justify-center rounded-full bg-primary/10">
        <Loader2 className="size-4 animate-spin text-primary" />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium">{entry.opts.title ?? job.label}</span>
        <span className="block truncate text-xs text-muted-foreground">{active?.label ?? "Queued"}</span>
      </span>
    </motion.button>
  );
}
