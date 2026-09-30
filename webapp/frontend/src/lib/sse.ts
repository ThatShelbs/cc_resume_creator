import { useEffect, useRef, useState } from "react";
import { api, withToken } from "./api";
import type { JobSummary } from "./types";

export interface JobStream {
  job: JobSummary | null;
  lines: string[];
  done: boolean;
}

const DONE = new Set(["succeeded", "failed", "cancelled"]);

/**
 * Follow a background job over Server-Sent Events: its log lines, stage, and
 * final status. Falls back to polling if the stream drops (e.g. the laptop
 * slept), so a job can never look stuck in the UI.
 */
export function useJobStream(jobId: string | null | undefined): JobStream {
  const [state, setState] = useState<JobStream>({ job: null, lines: [], done: false });
  const doneRef = useRef(false);

  useEffect(() => {
    if (!jobId) return;
    doneRef.current = false;
    setState({ job: null, lines: [], done: false });
    let poll: number | undefined;
    const source = new EventSource(withToken(`/api/jobs/${jobId}/events`));

    const finish = (job: JobSummary) => {
      doneRef.current = true;
      setState((s) => ({ ...s, job, done: true }));
      source.close();
      if (poll) window.clearInterval(poll);
    };

    source.addEventListener("lines", (e) => {
      const batch = JSON.parse((e as MessageEvent).data) as string[];
      setState((s) => ({ ...s, lines: [...s.lines, ...batch] }));
    });
    source.addEventListener("status", (e) => {
      const job = JSON.parse((e as MessageEvent).data) as JobSummary;
      setState((s) => ({ ...s, job }));
    });
    source.addEventListener("end", (e) => finish(JSON.parse((e as MessageEvent).data) as JobSummary));
    source.onerror = () => {
      if (doneRef.current) return;
      source.close();
      // Stream dropped: catch up by polling the job (with its full log).
      poll = window.setInterval(async () => {
        try {
          const job = await api.get<JobSummary & { lines: string[] }>(`/api/jobs/${jobId}?lines=true`);
          setState((s) => ({ ...s, job, lines: job.lines }));
          if (DONE.has(job.status)) finish(job);
        } catch {
          /* server restarting; keep trying */
        }
      }, 1500);
    };

    return () => {
      source.close();
      if (poll) window.clearInterval(poll);
    };
  }, [jobId]);

  return state;
}

export function isDone(job: JobSummary | null | undefined): boolean {
  return !!job && DONE.has(job.status);
}
