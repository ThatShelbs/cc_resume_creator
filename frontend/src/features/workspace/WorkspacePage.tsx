import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CircleAlert, Copy, Eye, FileText, FolderOpen, Gauge, History, LayoutTemplate, MoreHorizontal, NotebookPen, PenLine, RefreshCcw, Sparkles, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Callout, EmptyState, Monogram } from "@/components/shared/common";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogContent, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger, Tabs, TabsContent, TabsList, TabsTrigger, Tooltip } from "@/components/ui/overlays";
import { Badge, Card, Kbd } from "@/components/ui/primitives";
import { useJobs, useJobState } from "@/features/jobs/JobCenter";
import { TemplatePicker } from "@/features/projects/TemplatePicker";
import { api, projectFileUrl } from "@/lib/api/client";
import { keys, usePatchProject, useProject, useProjectFacts, useSystem } from "@/lib/api/queries";
import { isDone } from "@/lib/api/sse";
import type { JobSummary, LintResult, Project, ProjectDetail, TemplateKey } from "@/lib/api/types";
import { cn, formatDate, isMac, relativeTime } from "@/lib/utils";
import { ContentEditor } from "./ContentEditor";
import { fingerprint, fromDraft, toDraft, type Draft } from "./draft";
import { HistoryPanel } from "./HistoryPanel";
import { InsightsPanel } from "./InsightsPanel";
import { PdfPreview } from "./PdfPreview";
import { ResumePaper } from "./ResumePaper";
import { PostingPanel, TrackingPanel } from "./SidePanels";
import { EditableTitle } from "@/features/workspace/components/EditableTitle";
import { StatusMenu } from "@/features/workspace/components/StatusMenu";
import { SaveState, SaveIndicator } from "@/features/workspace/components/SaveIndicator";
import { DownloadMenu } from "@/features/workspace/components/DownloadMenu";
import { RunningBanner } from "@/features/workspace/components/RunningBanner";
import { ReadyCard } from "@/features/workspace/components/ReadyCard";
import { WorkspaceSkeleton } from "@/features/workspace/components/WorkspaceSkeleton";

export default function WorkspacePage() {
  const { id = "" } = useParams();
  const { data, isLoading, error } = useProject(id);

  if (isLoading) return <WorkspaceSkeleton />;
  if (error || !data)
    return (
      <div className="mx-auto max-w-2xl p-6 pt-16">
        <EmptyState
          icon={CircleAlert}
          title="Project not found"
          description={(error as Error)?.message ?? "It may have been moved to the trash."}
          action={
            <Button asChild>
              <Link to="/">Back to projects</Link>
            </Button>
          }
        />
      </div>
    );
  return <Workspace key={id} detail={data} />;
}

function Workspace({ detail }: { detail: ProjectDetail }) {
  const { project, result, outputs } = detail;
  const pid = project.id;
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { track, open: openJob } = useJobs();
  const { data: system } = useSystem();
  const { data: facts } = useProjectFacts(pid);
  const patch = usePatchProject(pid);

  const [draft, setDraft] = useState<Draft | null>(() => (result ? toDraft(result) : null));
  const savedFp = useRef(fingerprint(draft));
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [lint, setLint] = useState<LintResult>();
  const [tab, setTab] = useState(result ? "content" : "content");
  const [previewMode, setPreviewMode] = useState<"pdf" | "live">("pdf");
  const [confirmRegen, setConfirmRegen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Latest job for this project (live if it's running).
  const jobState = useJobState(detail.job?.id);
  const job: JobSummary | null = jobState?.job ?? detail.job ?? null;
  const running = !!job && !isDone(job);

  // Adopt a new result from the server (after a generation or render) unless
  // there are local edits in flight.
  useEffect(() => {
    if (!result) {
      setDraft(null);
      savedFp.current = "";
      return;
    }
    const incoming = toDraft(result);
    const fp = fingerprint(incoming);
    if (fp === savedFp.current) return;
    if (saveState === "dirty" || saveState === "saving") return;
    savedFp.current = fp;
    setDraft(incoming);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result]);

  const update = useCallback((fn: (d: Draft) => Draft) => {
    setDraft((d) => (d ? fn(d) : d));
  }, []);

  // Autosave (debounced) whenever the draft really changes.
  const save = useCallback(async (d: Draft) => {
    const fp = fingerprint(d);
    if (fp === savedFp.current) {
      setSaveState("saved");
      return true;
    }
    setSaveState("saving");
    try {
      const summary = await api.put<Project>(`/api/projects/${pid}/result`, fromDraft(d));
      savedFp.current = fp;
      qc.setQueryData<ProjectDetail>(keys.project(pid), (old) => (old ? { ...old, project: summary, result: fromDraft(d) } : old));
      setSaveState("saved");
      return true;
    } catch (e) {
      setSaveState("error");
      toast.error("Couldn't save your edits", { description: (e as Error).message });
      return false;
    }
  }, [pid, qc]);

  useEffect(() => {
    if (!draft) return;
    if (fingerprint(draft) === savedFp.current) return;
    setSaveState("dirty");
    const t = window.setTimeout(() => save(draft), 900);
    return () => window.clearTimeout(t);
  }, [draft, save]);

  // Live truthfulness checks (debounced).
  useEffect(() => {
    if (!draft) return;
    const t = window.setTimeout(() => {
      api
        .post<LintResult>(`/api/projects/${pid}/lint`, fromDraft(draft))
        .then(setLint)
        .catch(() => undefined);
    }, 350);
    return () => window.clearTimeout(t);
  }, [draft, pid]);

  const startJob = useMutation({
    mutationFn: ({ kind, template }: { kind: "generate" | "render"; template?: TemplateKey }) =>
      api.post<JobSummary>(`/api/projects/${pid}/${kind}`, kind === "render" && template ? { template } : undefined),
    onSuccess: (j, { kind }) => {
      qc.invalidateQueries({ queryKey: keys.project(pid) });
      if (kind === "generate") {
        track(j, {
          title: `Tailoring for ${project.company || project.name}`,
          coverLetter: project.cover_letter,
          successMessage: "Your tailored resume is ready",
        });
      } else {
        track(j, { open: false, successMessage: "Preview updated" });
      }
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const render = useCallback(
    async (template?: TemplateKey) => {
      if (!draft) return;
      if (lint?.counts.error) {
        toast.error("Remove the blocked content first", { description: "A line matches your never-claim list." });
        return;
      }
      if (!(await save(draft))) return;
      startJob.mutate({ kind: "render", template });
    },
    [draft, lint, save, startJob],
  );

  // Ctrl/Cmd+S: save now and re-render.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "s" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        if (!running && draft) render();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [render, running, draft]);

  // Don't lose edits that haven't reached the server yet.
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (saveState === "dirty" || saveState === "saving") e.preventDefault();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [saveState]);

  const duplicate = useMutation({
    mutationFn: () => api.post<Project>(`/api/projects/${pid}/duplicate`),
    onSuccess: (copy) => {
      qc.invalidateQueries({ queryKey: keys.projects });
      navigate(`/projects/${copy.id}`);
      toast.success("Duplicated. You're now editing the copy.");
    },
    onError: (e) => toast.error((e as Error).message),
  });
  const remove = useMutation({
    mutationFn: () => api.del<{ trash_id: string }>(`/api/projects/${pid}`),
    onSuccess: ({ trash_id }) => {
      qc.invalidateQueries({ queryKey: keys.projects });
      qc.invalidateQueries({ queryKey: keys.trash });
      navigate("/");
      toast("Moved to trash", {
        description: project.name,
        action: { label: "Undo", onClick: () => api.post(`/api/trash/${trash_id}/restore`).then(() => qc.invalidateQueries({ queryKey: keys.projects })) },
      });
    },
    onError: (e) => toast.error((e as Error).message),
  });
  const restoreVersion = useMutation({
    mutationFn: (vid: string) => api.post<JobSummary>(`/api/projects/${pid}/versions/${vid}/restore`),
    onSuccess: (j) => {
      qc.invalidateQueries({ queryKey: ["project", pid] });
      track(j, { open: false, successMessage: "Version restored" });
      setSaveState("saved");
      savedFp.current = "";
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const pdf = outputs.find((f) => f.name.startsWith("out_resume_") && f.name.endsWith(".pdf"));
  const pdfUrl = pdf ? projectFileUrl(pid, pdf.name, { bust: project.rendered_at ?? pdf.modified }) : null;
  const stale = saveState !== "saved" || project.outputs_stale;
  const generateLabel = draft ? "Regenerate" : "Generate";
  const blockedInputs = system?.onboarding_needed;

  // grid-cols-1 (minmax(0,1fr)) lets the column shrink; otherwise the PDF's
  // own width would size the track and the viewer could never fit it.
  const preview = (
    <div className="grid min-w-0 grid-cols-1 gap-3">
      <div className="flex items-center gap-2">
        <div role="tablist" aria-label="Preview mode" className="inline-flex rounded-lg bg-secondary p-0.5">
          {(["pdf", "live"] as const).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={previewMode === m}
              onClick={() => setPreviewMode(m)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium text-muted-foreground transition-all",
                previewMode === m && "bg-background text-foreground shadow-soft",
              )}
            >
              {m === "pdf" ? "Exact PDF" : "Live draft"}
            </button>
          ))}
        </div>
        {previewMode === "pdf" && stale && pdfUrl && (
          <Tooltip content="The PDF shows the last render. Re-render to include your latest edits.">
            <Badge variant="warning" className="cursor-default">
              Edits not rendered
            </Badge>
          </Tooltip>
        )}
        {previewMode === "live" && <span className="text-xs text-muted-foreground">Updates as you type</span>}
        {result?.page_count ? <Badge variant="outline" className="ml-auto">{result.page_count} {result.page_count === 1 ? "page" : "pages"}</Badge> : null}
      </div>
      <div className="paper-canvas rounded-xl border p-4 sm:p-6">
        {previewMode === "live" && draft ? (
          <ResumePaper draft={draft} template={project.template} />
        ) : pdfUrl ? (
          <PdfPreview url={pdfUrl} />
        ) : draft ? (
          <div className="grid gap-3">
            <Callout tone="warning" title="No PDF for this version">
              {system?.word ? "Re-render to create one." : "PDF export needs Microsoft Word. Showing the live draft instead."}
            </Callout>
            <ResumePaper draft={draft} template={project.template} />
          </div>
        ) : (
          <div className="flex aspect-[8.5/11] items-center justify-center rounded-sm border border-dashed bg-background/60 text-sm text-muted-foreground">
            Your resume will appear here
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2 mb-2 text-muted-foreground">
        <Link to="/">
          <ArrowLeft /> Projects
        </Link>
      </Button>

      {/* Header */}
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center">
        <div className="flex min-w-0 flex-1 items-center gap-3.5">
          <Monogram text={project.company || project.name} className="size-12 text-base" />
          <div className="min-w-0">
            <EditableTitle value={project.name} onSave={(name) => patch.mutate({ name }, { onError: (e) => toast.error((e as Error).message) })} />
            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
              <StatusMenu project={project} onChange={(status) => patch.mutate({ status })} />
              {project.company && <span>{project.company}</span>}
              <span className="hidden sm:inline">·</span>
              <span>Created {formatDate(project.created_at)}</span>
              {project.last_generate?.ok && (
                <>
                  <span className="hidden sm:inline">·</span>
                  <span>Generated {relativeTime(project.last_generate.when)}</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {draft && <SaveIndicator state={saveState} />}
          {draft && <DownloadMenu pid={pid} outputs={outputs} />}
          {draft && (
            <Tooltip content={<span>Apply your edits to the Word and PDF files <Kbd className="ml-1 border-background/30 bg-background/15 text-background">{isMac ? "⌘" : "Ctrl"} S</Kbd></span>}>
              <Button variant={stale ? "default" : "outline"} onClick={() => render()} disabled={running} loading={startJob.isPending && startJob.variables?.kind === "render"}>
                <RefreshCcw /> Re-render
              </Button>
            </Tooltip>
          )}
          <Button
            variant={draft ? "outline" : "gradient"}
            onClick={() => (draft ? setConfirmRegen(true) : startJob.mutate({ kind: "generate" }))}
            disabled={running || blockedInputs}
            loading={startJob.isPending && startJob.variables?.kind === "generate"}
          >
            <Sparkles /> {generateLabel}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="More actions">
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => duplicate.mutate()}>
                <Copy /> Duplicate for a similar role
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => api.post(`/api/projects/${pid}/open-folder`).catch((e) => toast.error((e as Error).message))}>
                <FolderOpen /> Open project folder
              </DropdownMenuItem>
              {job && (
                <DropdownMenuItem onSelect={() => openJob(job.id)}>
                  <FileText /> Last run details
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem destructive onSelect={() => setConfirmDelete(true)}>
                <Trash2 /> Move to trash
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Status banners */}
      <div className="mt-5 grid gap-3">
        {running && job && <RunningBanner job={job} onOpen={() => openJob(job.id)} />}
        {!running && job?.status === "failed" && (
          <Callout
            tone="error"
            title={job.deny?.length ? "The last run was blocked by your never-claim list" : `The last ${job.kind === "render" ? "render" : "generation"} didn't finish`}
            action={
              <Button size="sm" variant="outline" onClick={() => openJob(job.id)}>
                Details
              </Button>
            }
          >
            <span className="whitespace-pre-wrap">{job.hint ?? job.error}</span>
          </Callout>
        )}
        {!running && project.inputs_changed.length > 0 && draft && (
          <Callout
            tone="warning"
            title="Your source materials changed since this was generated"
            action={
              <Button size="sm" variant="outline" onClick={() => setConfirmRegen(true)} disabled={blockedInputs}>
                <Sparkles /> Regenerate
              </Button>
            }
          >
            Updated: {project.inputs_changed.map((k) => k.replace("_", " ")).join(", ")}. Regenerate to tailor from the latest versions,
            or keep this one.
          </Callout>
        )}
        {blockedInputs && (
          <Callout
            tone="warning"
            title="Add your base resume and profile to generate"
            action={
              <Button asChild size="sm" variant="outline">
                <Link to="/welcome">Start setup</Link>
              </Button>
            }
          />
        )}
      </div>

      {/* Body */}
      <Tabs value={tab} onValueChange={setTab} className="mt-6">
        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <TabsList>
            <TabsTrigger value="content">
              <PenLine /> Content
              {!!lint?.counts.error && <span className="ml-0.5 size-1.5 rounded-full bg-destructive" />}
            </TabsTrigger>
            <TabsTrigger value="preview" className="lg:hidden">
              <Eye /> Preview
            </TabsTrigger>
            <TabsTrigger value="template">
              <LayoutTemplate /> Template
            </TabsTrigger>
            <TabsTrigger value="insights" disabled={!draft}>
              <Gauge /> Insights
            </TabsTrigger>
            <TabsTrigger value="posting">
              <FileText /> Posting
            </TabsTrigger>
            <TabsTrigger value="history">
              <History /> History
            </TabsTrigger>
            <TabsTrigger value="tracking">
              <NotebookPen /> Tracking
            </TabsTrigger>
          </TabsList>
        </div>

        <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(380px,44%)] 2xl:grid-cols-[minmax(0,1fr)_600px]">
          <div className="min-w-0">
            <TabsContent value="content" className="mt-0">
              {draft ? (
                <ContentEditor draft={draft} update={update} lint={lint} facts={facts} />
              ) : (
                <ReadyCard project={project} running={running} disabled={blockedInputs} onGenerate={() => startJob.mutate({ kind: "generate" })} />
              )}
            </TabsContent>
            <TabsContent value="preview" className="mt-0 lg:hidden">
              {preview}
            </TabsContent>
            <TabsContent value="template" className="mt-0">
              <Card className="p-5">
                <h3 className="text-sm font-semibold">Template</h3>
                <p className="mb-4 mt-0.5 text-sm text-muted-foreground">
                  Switching re-renders instantly from your current content. No new draft, no Claude call.
                </p>
                <TemplatePicker
                  value={project.template}
                  disabled={running}
                  onChange={(t) => {
                    if (t === project.template) return;
                    patch.mutate({ template: t });
                    if (draft) render(t);
                  }}
                />
                <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
                  Every template is single-column with standard fonts and nothing in headers or footers, which is what applicant
                  tracking systems parse reliably.
                </p>
              </Card>
            </TabsContent>
            <TabsContent value="insights" className="mt-0">
              {result && <InsightsPanel pid={pid} result={result} lint={lint} />}
            </TabsContent>
            <TabsContent value="posting" className="mt-0">
              <PostingPanel project={project} jobText={detail.job_text} result={result} />
            </TabsContent>
            <TabsContent value="history" className="mt-0">
              {result ? (
                <HistoryPanel pid={pid} current={result} onRestore={(vid) => restoreVersion.mutate(vid)} />
              ) : (
                <EmptyState icon={History} title="No versions yet" description="Generate a resume to start its history." />
              )}
            </TabsContent>
            <TabsContent value="tracking" className="mt-0">
              <TrackingPanel project={project} />
            </TabsContent>
          </div>
          <aside className="hidden lg:block">
            <div className="sticky top-20">{preview}</div>
          </aside>
        </div>
      </Tabs>

      <AlertDialog open={confirmRegen} onOpenChange={setConfirmRegen}>
        <AlertDialogContent
          title="Generate a fresh draft?"
          description="Claude re-tailors your materials to this posting. The current version, including any hand edits, is kept in History, and you can restore it anytime."
          confirmLabel="Regenerate"
          onConfirm={async () => {
            if (draft && !(await save(draft))) return;
            startJob.mutate({ kind: "generate" });
          }}
        />
      </AlertDialog>
      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent
          title="Move this project to the trash?"
          description="You can restore it from the Projects page."
          confirmLabel="Move to trash"
          destructive
          onConfirm={() => remove.mutate()}
        />
      </AlertDialog>
    </div>
  );
}
