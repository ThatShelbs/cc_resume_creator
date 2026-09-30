import { describe, expect, it } from "vitest";
import { progressPercent, stepStates, stepsFor } from "@/features/jobs/stages";
import type { JobSummary } from "@/lib/api/types";

const job = (patch: Partial<JobSummary>): JobSummary => ({
  id: "j1",
  kind: "generate",
  label: "Tailoring",
  project_id: "p1",
  status: "running",
  stage: "preparing",
  stages_seen: [],
  error: null,
  hint: null,
  deny: [],
  created: "",
  elapsed: 0,
  line_count: 0,
  result: null,
  ...patch,
});

describe("generation stepper", () => {
  it("lists the steps for each job kind", () => {
    expect(stepsFor(job({})).map((s) => s.key)).toEqual(["preparing", "drafting", "structuring", "validating", "rendering", "pdf"]);
    expect(stepsFor(job({}), { coverLetter: true }).map((s) => s.key)).toContain("cover_letter");
    expect(stepsFor(job({ kind: "render" })).map((s) => s.key)).toEqual(["preparing", "validating", "rendering", "pdf"]);
  });

  it("adds a reported stage it didn't predict, before rendering", () => {
    const keys = stepsFor(job({ stages_seen: ["preparing", "cover_letter"] })).map((s) => s.key);
    expect(keys.indexOf("cover_letter")).toBe(keys.indexOf("rendering") - 1);
  });

  it("marks earlier steps done and the current one active", () => {
    const j = job({ stage: "structuring", stages_seen: ["preparing", "drafting", "structuring"] });
    const states = stepStates(stepsFor(j), j);
    expect(states).toEqual(["done", "done", "active", "pending", "pending", "pending"]);
    expect(progressPercent(states)).toBe(42);
  });

  it("marks the step that was running as failed", () => {
    const j = job({ status: "failed", stage: "validating", stages_seen: ["preparing", "drafting", "structuring", "validating"] });
    expect(stepStates(stepsFor(j), j)[3]).toBe("failed");
  });

  it("shows steps that never ran on a successful job as skipped", () => {
    const j = job({ kind: "render", status: "succeeded", stage: "done", stages_seen: ["preparing", "validating", "rendering", "done"] });
    expect(stepStates(stepsFor(j), j)).toEqual(["done", "done", "done", "skipped"]);
  });

  it("keeps everything pending while queued", () => {
    const j = job({ status: "queued", stage: "queued" });
    expect(new Set(stepStates(stepsFor(j), j))).toEqual(new Set(["pending"]));
  });
});
