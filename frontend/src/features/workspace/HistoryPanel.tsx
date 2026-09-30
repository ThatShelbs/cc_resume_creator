import { useQuery } from "@tanstack/react-query";
import { diffWords } from "diff";
import { Download, GitCompare, History, RotateCcw } from "lucide-react";
import { useState } from "react";
import { EmptyState } from "@/components/shared/common";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogContent, Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/overlays";
import { Badge, Card, Skeleton } from "@/components/ui/primitives";
import { api, versionFileUrl } from "@/lib/api/client";
import { useVersions } from "@/lib/api/queries";
import type { ResumeResult, Version } from "@/lib/api/types";
import { formatBytes, formatDate, relativeTime } from "@/lib/utils";

function Diff({ before, after }: { before: string; after: string }) {
  const parts = diffWords(before, after);
  return (
    <p className="whitespace-pre-wrap text-[13px] leading-relaxed">
      {parts.map((p, i) =>
        p.added ? (
          <ins key={i} className="rounded-sm bg-success/15 px-0.5 text-success no-underline decoration-success/40">
            {p.value}
          </ins>
        ) : p.removed ? (
          <del key={i} className="rounded-sm bg-destructive/10 px-0.5 text-destructive/80 decoration-destructive/40">
            {p.value}
          </del>
        ) : (
          <span key={i}>{p.value}</span>
        ),
      )}
    </p>
  );
}

function CompareDialog({ pid, version, current, onClose }: { pid: string; version: Version; current: ResumeResult; onClose: () => void }) {
  const { data: old, error: queryError } = useQuery({
    queryKey: ["project", pid, "version", version.id],
    queryFn: () => api.get<ResumeResult>(`/api/projects/${pid}/versions/${version.id}`),
    staleTime: Infinity,
  });
  const error = queryError ? (queryError as Error).message : null;

  const companies = Array.from(new Set([...(old?.experience ?? []), ...current.experience].map((e) => e.company)));
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Compare with the version from {formatDate(version.generated_at ?? version.id, true)}</DialogTitle>
          <DialogDescription>
            <ins className="rounded-sm bg-success/15 px-1 text-success no-underline">Added</ins> in the current version,{" "}
            <del className="rounded-sm bg-destructive/10 px-1 text-destructive/80">removed</del> since that one.
          </DialogDescription>
        </DialogHeader>
        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : !old ? (
          <div className="grid gap-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-16" />
            <Skeleton className="h-24" />
          </div>
        ) : (
          <div className="grid gap-5">
            <section>
              <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Summary</h4>
              <Diff before={old.summary} after={current.summary} />
            </section>
            {companies.map((company) => {
              const a = old.experience.find((e) => e.company === company)?.bullets.map((b) => b.text) ?? [];
              const b = current.experience.find((e) => e.company === company)?.bullets.map((x) => x.text) ?? [];
              return (
                <section key={company}>
                  <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{company}</h4>
                  <Diff before={a.map((t) => `• ${t}`).join("\n")} after={b.map((t) => `• ${t}`).join("\n")} />
                </section>
              );
            })}
            <section>
              <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Skills</h4>
              <Diff before={old.skills.join(", ")} after={current.skills.join(", ")} />
            </section>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function HistoryPanel({
  pid,
  current,
  onRestore,
}: {
  pid: string;
  current: ResumeResult;
  onRestore: (versionId: string) => void;
}) {
  const { data, isLoading } = useVersions(pid);
  const [compare, setCompare] = useState<Version | null>(null);
  const [restore, setRestore] = useState<Version | null>(null);

  if (isLoading)
    return (
      <div className="grid gap-3">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
    );
  if (!data?.length)
    return (
      <EmptyState
        icon={History}
        title="No earlier versions yet"
        description="Each time you regenerate, the version it replaces is kept here, with its Word file and report, so you can compare or roll back."
      />
    );

  return (
    <>
      <ol className="relative grid gap-3 border-l pl-5">
        {data.map((v) => (
          <li key={v.id} className="relative">
            <span className="absolute -left-[26px] top-4 size-2.5 rounded-full border-2 border-background bg-muted-foreground/60 ring-1 ring-border" />
            <Card className="p-4">
              <div className="flex flex-wrap items-center gap-2">
                <div className="text-sm font-medium">{formatDate(v.generated_at ?? null, true) || v.id}</div>
                <span className="text-xs text-muted-foreground">{v.generated_at && relativeTime(v.generated_at)}</span>
                <div className="ml-auto flex gap-1.5">
                  {v.template && (
                    <Badge variant="outline" className="capitalize">
                      {v.template}
                    </Badge>
                  )}
                  {v.page_count && <Badge variant="outline">{v.page_count} pg</Badge>}
                  {v.warnings > 0 && <Badge variant="warning">{v.warnings} warnings</Badge>}
                </div>
              </div>
              {v.summary && <p className="mt-2 line-clamp-2 text-[13px] leading-relaxed text-muted-foreground">{v.summary}</p>}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => setCompare(v)}>
                  <GitCompare /> Compare with current
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setRestore(v)}>
                  <RotateCcw /> Restore
                </Button>
                <div className="ml-auto flex flex-wrap gap-1">
                  {v.files
                    .filter((f) => f.name.endsWith(".docx"))
                    .map((f) => (
                      <Button key={f.name} asChild size="sm" variant="ghost" className="text-muted-foreground">
                        <a href={versionFileUrl(pid, v.id, f.name)} download>
                          <Download /> {f.name.includes("cover_letter") ? "Cover letter" : "Resume"} .docx
                          <span className="text-[11px] opacity-70">{formatBytes(f.size)}</span>
                        </a>
                      </Button>
                    ))}
                </div>
              </div>
            </Card>
          </li>
        ))}
      </ol>
      {compare && <CompareDialog pid={pid} version={compare} current={current} onClose={() => setCompare(null)} />}
      <AlertDialog open={!!restore} onOpenChange={(o) => !o && setRestore(null)}>
        <AlertDialogContent
          title="Restore this version?"
          description="Its content becomes the current resume and is re-rendered. What you have now is saved to History first, so nothing is lost."
          confirmLabel="Restore"
          onConfirm={() => restore && onRestore(restore.id)}
        />
      </AlertDialog>
    </>
  );
}
