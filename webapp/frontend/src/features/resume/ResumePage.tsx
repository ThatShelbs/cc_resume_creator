import { Building2, ChevronDown, Download, GraduationCap, PenLine, Upload } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Badge, Card, Skeleton } from "@/components/ui/primitives";
import { withToken } from "@/lib/api";
import { useResume } from "@/lib/queries";
import type { ResumeStructure, UploadResult } from "@/lib/types";
import { cn, relativeTime } from "@/lib/utils";
import { ResumeFlow } from "./ResumeFlow";
import { ResumeDropzone } from "./ResumeUpload";

type Mode = { kind: "view" } | { kind: "replace"; upload?: UploadResult } | { kind: "edit"; structure: ResumeStructure };

export default function ResumePage() {
  const { data, isLoading } = useResume();
  const [mode, setMode] = useState<Mode>({ kind: "view" });
  const [open, setOpen] = useState<number | null>(0);

  const header = (
    <PageHeader
      title="Base resume"
      description="Your official employers, titles, and dates. These are copied into every tailored resume exactly as saved here; only the summary, bullets, and skills are tailored."
      actions={
        data?.exists && mode.kind === "view" ? (
          <>
            <Button asChild variant="outline" size="sm">
              <a href={withToken("/api/resume/download")} download>
                <Download /> .docx
              </a>
            </Button>
            <Button variant="outline" size="sm" onClick={() => data.structure && setMode({ kind: "edit", structure: data.structure })}>
              <PenLine /> Edit details
            </Button>
            <Button size="sm" onClick={() => setMode({ kind: "replace" })}>
              <Upload /> Replace
            </Button>
          </>
        ) : undefined
      }
    />
  );

  if (isLoading)
    return (
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        {header}
        <Skeleton className="mt-6 h-64" />
      </div>
    );

  const s = data?.structure;
  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      {header}
      <div className="mt-6">
        {mode.kind === "replace" || (!data?.exists && mode.kind === "view") ? (
          <ResumeFlow
            initialUpload={mode.kind === "replace" ? mode.upload : undefined}
            onConfirmed={() => setMode({ kind: "view" })}
            onCancel={data?.exists ? () => setMode({ kind: "view" }) : undefined} />
        ) : mode.kind === "edit" ? (
          <ResumeFlow initial={mode.structure} confirmLabel="Save changes" onConfirmed={() => setMode({ kind: "view" })} onCancel={() => setMode({ kind: "view" })} />
        ) : s ? (
          <div className="grid gap-6">
            <p className="-mt-2 text-xs text-muted-foreground">
              <code className="rounded bg-muted px-1">resume_input/{data?.file}</code>
              {data?.updated && `, updated ${relativeTime(data.updated)}`}. Replacing it keeps the old one in resume_archive/.
            </p>

            <section>
              <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <Building2 className="size-4 text-primary" /> Experience
              </h2>
              <ol className="relative grid gap-3 border-l pl-6">
                {s.jobs.map((job, i) => (
                  <li key={i} className="relative">
                    <span className="absolute -left-[31px] top-4 flex size-3 items-center justify-center rounded-full border-2 border-background bg-primary ring-4 ring-primary/10" />
                    <Card className="overflow-hidden">
                      <button
                        type="button"
                        onClick={() => setOpen(open === i ? null : i)}
                        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/30"
                        aria-expanded={open === i}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="font-medium">{job.title}</div>
                          <div className="text-sm text-muted-foreground">
                            {job.company}
                            {job.location && ` · ${job.location}`}
                          </div>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="text-xs font-medium tabular-nums text-muted-foreground">{job.dates}</div>
                          <Badge variant="secondary" className="mt-1">
                            {job.bullets.length} bullets
                          </Badge>
                        </div>
                        <ChevronDown className={cn("mt-1 size-4 shrink-0 text-muted-foreground transition-transform", open === i && "rotate-180")} />
                      </button>
                      {open === i && (
                        <ul className="grid gap-1.5 border-t px-4 py-3 text-[13px] leading-relaxed">
                          {job.bullets.map((b, k) => (
                            <li key={k} className="flex gap-2">
                              <span className="mt-2 size-1 shrink-0 rounded-full bg-muted-foreground" />
                              {b}
                            </li>
                          ))}
                        </ul>
                      )}
                    </Card>
                  </li>
                ))}
              </ol>
            </section>

            {s.education.length > 0 && (
              <section>
                <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                  <GraduationCap className="size-4 text-primary" /> Education
                </h2>
                <div className="grid gap-3 sm:grid-cols-2">
                  {s.education.map((e, i) => (
                    <Card key={i} className="px-4 py-3">
                      <div className="font-medium">{e.degree}</div>
                      <div className="text-sm text-muted-foreground">{e.institution}</div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {[e.location, e.dates].filter(Boolean).join(" · ")}
                      </div>
                    </Card>
                  ))}
                </div>
              </section>
            )}

            <section>
              <h2 className="mb-3 text-sm font-semibold">Replace with a newer resume</h2>
              <ResumeDropzone compact onUploaded={(upload) => setMode({ kind: "replace", upload })} />
            </section>
          </div>
        ) : null}
      </div>
    </div>
  );
}
