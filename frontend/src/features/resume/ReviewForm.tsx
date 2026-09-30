/**
 * Review and correct the structure parsed from an uploaded resume before it
 * becomes the canonical base resume. Fields that weren't found verbatim in
 * the uploaded file are flagged, so nothing is accepted silently.
 */
import { ArrowDown, ArrowLeftRight, ArrowUp, Plus, ShieldAlert, Trash2 } from "lucide-react";
import { SortableItems } from "@/components/shared/SortableItems";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/overlays";
import { AutoTextarea, Badge, Card, Field, Input } from "@/components/ui/primitives";
import type { ResumeStructure } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type Job = ResumeStructure["jobs"][number];
type Edu = ResumeStructure["education"][number];

function flagMap(structure: ResumeStructure): Map<string, string> {
  return new Map(structure.flags.map((f) => [f.path, f.message]));
}

function Flagged({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="text-xs text-warning">{message}</p>;
}

export function ReviewForm({ value, onChange }: { value: ResumeStructure; onChange: (s: ResumeStructure) => void }) {
  const flags = flagMap(value);
  // Once a flagged field is edited, the flag no longer describes it.
  const clearFlag = (s: ResumeStructure, prefix: string): ResumeStructure => ({
    ...s,
    flags: s.flags.filter((f) => f.path !== prefix),
  });
  const setJob = (i: number, patch: Partial<Job>, field?: string) => {
    let next: ResumeStructure = { ...value, jobs: value.jobs.map((j, k) => (k === i ? { ...j, ...patch } : j)) };
    if (field) next = clearFlag(next, `jobs.${i}.${field}`);
    onChange(next);
  };
  const setEdu = (i: number, patch: Partial<Edu>, field?: string) => {
    let next: ResumeStructure = { ...value, education: value.education.map((e, k) => (k === i ? { ...e, ...patch } : e)) };
    if (field) next = clearFlag(next, `education.${i}.${field}`);
    onChange(next);
  };
  const moveJob = (i: number, dir: -1 | 1) => {
    const jobs = [...value.jobs];
    const j = i + dir;
    if (j < 0 || j >= jobs.length) return;
    [jobs[i], jobs[j]] = [jobs[j], jobs[i]];
    // Flag paths are positional; clear them rather than mislabel fields.
    onChange({ ...value, jobs, flags: value.flags.filter((f) => !f.path.startsWith("jobs.")) });
  };
  const jobFlags = (i: number) => value.flags.filter((f) => f.path.startsWith(`jobs.${i}.`)).length;

  return (
    <div className="grid gap-5">
      {value.flags.length > 0 && (
        <div className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/[0.07] px-4 py-3 text-sm">
          <ShieldAlert className="mt-0.5 size-4 shrink-0 text-warning" />
          <p className="leading-relaxed">
            <span className="font-medium">{value.flags.length} field{value.flags.length > 1 ? "s" : ""} to double-check.</span>{" "}
            <span className="text-muted-foreground">
              They're highlighted below because they weren't found word-for-word in your file, or were missing. Titles, employers, and
              dates are copied into every resume exactly as saved here.
            </span>
          </p>
        </div>
      )}

      <Card className="p-5">
        <h3 className="text-sm font-semibold">Summary</h3>
        <p className="mb-2 mt-0.5 text-xs text-muted-foreground">
          Used as source material (e.g. your years of experience); each resume gets a freshly tailored summary.
        </p>
        <AutoTextarea value={value.summary} onChange={(e) => onChange({ ...value, summary: e.target.value })} aria-label="Summary" />
      </Card>

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">
          Experience <span className="font-normal text-muted-foreground">({value.jobs.length})</span>
        </h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => onChange({ ...value, jobs: [...value.jobs, { company: "", location: "", dates: "", title: "", bullets: [""] }] })}
        >
          <Plus /> Add employer
        </Button>
      </div>
      {value.jobs.map((job, i) => (
        <Card key={i} className={cn("p-5", jobFlags(i) > 0 && "border-warning/40")}>
          <div className="mb-4 flex items-center gap-2">
            <Badge variant="secondary">#{i + 1}</Badge>
            <span className="truncate text-sm font-medium">{job.company || "New employer"}</span>
            {jobFlags(i) > 0 && <Badge variant="warning">{jobFlags(i)} to check</Badge>}
            <div className="ml-auto flex gap-0.5">
              <Tooltip content="Swap company and title (for resumes that list the title first)">
                <Button variant="ghost" size="icon-sm" onClick={() => setJob(i, { company: job.title, title: job.company })} aria-label="Swap company and title">
                  <ArrowLeftRight />
                </Button>
              </Tooltip>
              <Button variant="ghost" size="icon-sm" onClick={() => moveJob(i, -1)} disabled={i === 0} aria-label="Move up">
                <ArrowUp />
              </Button>
              <Button variant="ghost" size="icon-sm" onClick={() => moveJob(i, 1)} disabled={i === value.jobs.length - 1} aria-label="Move down">
                <ArrowDown />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                className="hover:text-destructive"
                onClick={() => onChange({ ...value, jobs: value.jobs.filter((_, k) => k !== i), flags: value.flags.filter((f) => !f.path.startsWith("jobs.")) })}
                aria-label="Remove employer"
              >
                <Trash2 />
              </Button>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {(["company", "title", "location", "dates"] as const).map((field) => {
              const msg = flags.get(`jobs.${i}.${field}`);
              return (
                <Field key={field} label={{ company: "Company", title: "Job title", location: "Location", dates: "Dates" }[field]}>
                  <Input
                    value={job[field]}
                    aria-invalid={!!msg}
                    className={cn(msg && "border-warning/60 bg-warning/[0.04]")}
                    onChange={(e) => setJob(i, { [field]: e.target.value }, field)}
                    placeholder={field === "dates" ? "2019 - Present" : undefined}
                  />
                  <Flagged message={msg} />
                </Field>
              );
            })}
          </div>
          <div className="mt-4">
            <div className="mb-1.5 text-[13px] font-medium">Bullets</div>
            <SortableItems
              items={job.bullets}
              addLabel="Add bullet"
              placeholder="An accomplishment from this role"
              flags={Object.fromEntries(
                job.bullets.map((_, b) => [b, flags.get(`jobs.${i}.bullets.${b}`)]).filter(([, m]) => m),
              )}
              onChange={(bullets) =>
                onChange({
                  ...value,
                  jobs: value.jobs.map((j, k) => (k === i ? { ...j, bullets } : j)),
                  flags: value.flags.filter((f) => !f.path.startsWith(`jobs.${i}.bullets.`)),
                })
              }
            />
          </div>
        </Card>
      ))}

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">
          Education <span className="font-normal text-muted-foreground">({value.education.length})</span>
        </h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => onChange({ ...value, education: [...value.education, { institution: "", location: "", dates: "", degree: "" }] })}
        >
          <Plus /> Add school
        </Button>
      </div>
      {value.education.map((edu, i) => (
        <Card key={i} className="grid gap-4 p-5 sm:grid-cols-2">
          {(["institution", "degree", "location", "dates"] as const).map((field) => {
            const msg = flags.get(`education.${i}.${field}`);
            return (
              <Field key={field} label={{ institution: "School", degree: "Degree", location: "Location", dates: "Dates" }[field]}>
                <Input
                  value={edu[field]}
                  aria-invalid={!!msg}
                  className={cn(msg && "border-warning/60 bg-warning/[0.04]")}
                  onChange={(e) => setEdu(i, { [field]: e.target.value }, field)}
                />
                <Flagged message={msg} />
              </Field>
            );
          })}
          <div className="sm:col-span-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-destructive"
              onClick={() => onChange({ ...value, education: value.education.filter((_, k) => k !== i) })}
            >
              <Trash2 /> Remove school
            </Button>
          </div>
        </Card>
      ))}

      {value.other_sections.length > 0 && (
        <>
          <h3 className="text-sm font-semibold">Other sections</h3>
          {value.other_sections.map((sec, i) => (
            <Card key={i} className="p-5">
              <Input
                value={sec.title}
                onChange={(e) => onChange({ ...value, other_sections: value.other_sections.map((s, k) => (k === i ? { ...s, title: e.target.value } : s)) })}
                className="mb-3 h-8 max-w-xs font-medium"
                aria-label="Section title"
              />
              <SortableItems
                items={sec.lines}
                onChange={(lines) => onChange({ ...value, other_sections: value.other_sections.map((s, k) => (k === i ? { ...s, lines } : s)) })}
              />
            </Card>
          ))}
        </>
      )}
    </div>
  );
}

export function cleanStructure(s: ResumeStructure): ResumeStructure {
  return {
    ...s,
    jobs: s.jobs.map((j) => ({ ...j, bullets: j.bullets.filter((b) => b.trim()) })),
    other_sections: s.other_sections.map((o) => ({ ...o, lines: o.lines.filter((l) => l.trim()) })).filter((o) => o.lines.length),
  };
}
