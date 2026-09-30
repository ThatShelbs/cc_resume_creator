import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  Briefcase,
  ChevronDown,
  Copy,
  FileDown,
  Inbox,
  Loader2,
  MoreHorizontal,
  Plus,
  RefreshCcw,
  Search,
  Sparkles,
  Trash2,
  Undo2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sequins } from "@/components/brand";
import { Callout, EmptyState, Monogram, PageHeader, STATUS_META, StatusBadge } from "@/components/common";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogContent,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Select,
  Tooltip,
} from "@/components/ui/overlays";
import { Badge, Card, Input, Skeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { keys, useImportCandidates, useProjects, useSystem, useTrash } from "@/lib/queries";
import type { Project, ProjectStatus } from "@/lib/types";
import { cn, plural, relativeTime } from "@/lib/utils";

type Filter = "all" | "active" | ProjectStatus;
type Sort = "updated" | "created" | "company";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "active", label: "In progress" },
  { key: "draft", label: "Drafts" },
  { key: "applied", label: "Applied" },
  { key: "interviewing", label: "Interviewing" },
  { key: "offer", label: "Offers" },
  { key: "rejected", label: "Closed" },
  { key: "archived", label: "Archived" },
];

export function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const { data: system } = useSystem();
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<Sort>("updated");

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const p of projects ?? []) c[p.status] = (c[p.status] ?? 0) + 1;
    return c;
  }, [projects]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = (projects ?? []).filter((p) => {
      if (filter === "active" && !["draft", "applied", "interviewing"].includes(p.status)) return false;
      if (filter !== "all" && filter !== "active" && p.status !== filter) return false;
      if (filter === "all" && p.status === "archived") return false;
      return !q || `${p.name} ${p.company} ${p.role} ${p.notes}`.toLowerCase().includes(q);
    });
    return [...list].sort((a, b) =>
      sort === "company"
        ? (a.company || a.name).localeCompare(b.company || b.name)
        : sort === "created"
          ? b.created_at.localeCompare(a.created_at)
          : b.updated_at.localeCompare(a.updated_at),
    );
  }, [projects, filter, query, sort]);

  const needsSetup = system?.onboarding_needed;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <PageHeader
        title="Projects"
        description="One project per job posting. Each keeps its tailored resume, every earlier version, and where you are in the process."
        actions={
          <Button asChild variant="gradient">
            <Link to="/projects/new">
              <Plus /> New project
            </Link>
          </Button>
        }
      />

      {needsSetup && <SetupCard profile={!!system?.inputs.profile} resume={!!system?.inputs.resume} />}

      <StatsStrip projects={projects} loading={isLoading} />

      <ImportCallout />

      <div className="mt-6 flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 lg:pb-0">
          {FILTERS.map((f) => {
            const n = f.key === "all" ? (projects?.length ?? 0) - (counts.archived ?? 0) : f.key === "active" ? (counts.draft ?? 0) + (counts.applied ?? 0) + (counts.interviewing ?? 0) : (counts[f.key] ?? 0);
            if (f.key !== "all" && f.key !== "active" && !n) return null;
            return (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                className={cn(
                  "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-[13px] font-medium transition-colors",
                  filter === f.key
                    ? "border-foreground/15 bg-foreground text-background"
                    : "bg-background text-muted-foreground hover:bg-secondary hover:text-foreground",
                )}
              >
                {f.label}
                <span className={cn("tabular-nums", filter === f.key ? "text-background/70" : "text-muted-foreground/70")}>{n}</span>
              </button>
            );
          })}
        </div>
        <div className="flex gap-2 lg:ml-auto">
          <div className="relative flex-1 lg:w-64 lg:flex-none">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter projects" className="pl-8" aria-label="Filter projects" />
          </div>
          <Select
            aria-label="Sort"
            value={sort}
            onValueChange={(v) => setSort(v as Sort)}
            className="w-40"
            options={[
              { value: "updated", label: "Recently updated" },
              { value: "created", label: "Newest first" },
              { value: "company", label: "Company A to Z" },
            ]}
          />
        </div>
      </div>

      <div className="mt-5">
        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-[168px] rounded-xl" />
            ))}
          </div>
        ) : !projects?.length ? (
          <EmptyState
            icon={Briefcase}
            title="Start your first project"
            description="Paste a job posting and Resume Taylor tailors your real experience to it. Nothing is invented: every bullet traces back to your own materials."
            action={
              <Button asChild variant="gradient">
                <Link to="/projects/new">
                  <Plus /> New project
                </Link>
              </Button>
            }
          />
        ) : !visible.length ? (
          <EmptyState icon={Inbox} title="No matching projects" description="Try a different filter or search." />
        ) : (
          <motion.div layout className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <AnimatePresence initial={false}>
              {visible.map((p) => (
                <ProjectCard key={p.id} project={p} />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>

      <TrashSection />
    </div>
  );
}

function SetupCard({ profile, resume }: { profile: boolean; resume: boolean }) {
  const steps = [
    { done: resume, label: "Upload your base resume", to: "/resume" },
    { done: profile, label: "Confirm your profile", to: "/profile" },
  ];
  return (
    <Card className="relative mt-6 overflow-hidden border-primary/25">
      <div className="absolute inset-0 bg-gradient-to-br from-brand-pink/[0.16] via-brand-lilac/[0.08] to-transparent" />
      <div className="bead-rule absolute inset-x-0 top-0 h-[3px]" />
      <Sequins count={3} />
      <div className="relative flex flex-col gap-5 p-6 md:flex-row md:items-center">
        <div className="bg-brand-gradient flex size-12 shrink-0 items-center justify-center rounded-2xl shadow-lift">
          <Sparkles className="size-5" />
        </div>
        <div className="flex-1">
          <h2 className="text-base font-semibold tracking-tight">Set up Resume Taylor in about two minutes</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Your base resume and profile are the only source material the tailoring can draw from.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {steps.map((s) => (
              <Badge key={s.label} variant={s.done ? "success" : "outline"}>
                {s.done ? "Done" : "To do"}: {s.label}
              </Badge>
            ))}
          </div>
        </div>
        <Button asChild>
          <Link to="/welcome">
            Start setup <ArrowRight />
          </Link>
        </Button>
      </div>
    </Card>
  );
}

function StatsStrip({ projects, loading }: { projects: Project[] | undefined; loading: boolean }) {
  const stats = [
    { label: "Projects", value: projects?.length ?? 0, tone: "text-foreground" },
    { label: "Applied", value: projects?.filter((p) => p.status === "applied").length ?? 0, tone: "text-primary" },
    { label: "Interviewing", value: projects?.filter((p) => p.status === "interviewing").length ?? 0, tone: "text-warning" },
    { label: "Offers", value: projects?.filter((p) => p.status === "offer").length ?? 0, tone: "text-success" },
  ];
  return (
    <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      {stats.map((s) => (
        <Card key={s.label} className="px-4 py-3.5">
          <div className="text-xs font-medium text-muted-foreground">{s.label}</div>
          {loading ? (
            <Skeleton className="mt-2 h-7 w-10" />
          ) : (
            <div className={cn("mt-1 text-2xl font-semibold tabular-nums tracking-tight", s.tone)}>{s.value}</div>
          )}
        </Card>
      ))}
    </div>
  );
}

function ImportCallout() {
  const { data } = useImportCandidates();
  const qc = useQueryClient();
  const importAll = useMutation({
    mutationFn: () => api.post<{ created: string[] }>("/api/import", { files: data?.map((c) => c.file) ?? [] }),
    onSuccess: (r) => {
      toast.success(`Imported ${plural(r.created.length, "posting")}`);
      qc.invalidateQueries({ queryKey: keys.projects });
      qc.invalidateQueries({ queryKey: keys.importCandidates });
    },
    onError: (e) => toast.error((e as Error).message),
  });
  if (!data?.length) return null;
  return (
    <Callout
      className="mt-6"
      title={`Found ${plural(data.length, "job posting")} in resume_input/`}
      action={
        <Button size="sm" variant="outline" loading={importAll.isPending} onClick={() => importAll.mutate()}>
          <FileDown /> Import as {data.length > 1 ? "projects" : "a project"}
        </Button>
      }
    >
      {data.map((c) => c.role || c.file).join(", ")}. These came from the command-line workflow.
    </Callout>
  );
}

function ProjectCard({ project: p }: { project: Project }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const refresh = () => qc.invalidateQueries({ queryKey: keys.projects });

  const setStatus = useMutation({
    mutationFn: (status: ProjectStatus) => api.patch(`/api/projects/${p.id}`, { status }),
    onSuccess: refresh,
    onError: (e) => toast.error((e as Error).message),
  });
  const duplicate = useMutation({
    mutationFn: () => api.post<Project>(`/api/projects/${p.id}/duplicate`),
    onSuccess: (copy) => {
      refresh();
      toast.success("Project duplicated", { action: { label: "Open", onClick: () => navigate(`/projects/${copy.id}`) } });
    },
    onError: (e) => toast.error((e as Error).message),
  });
  const remove = useMutation({
    mutationFn: () => api.del<{ trash_id: string }>(`/api/projects/${p.id}`),
    onSuccess: ({ trash_id }) => {
      refresh();
      qc.invalidateQueries({ queryKey: keys.trash });
      toast("Moved to trash", {
        description: p.name,
        action: {
          label: "Undo",
          onClick: () =>
            api.post(`/api/trash/${trash_id}/restore`).then(() => {
              refresh();
              qc.invalidateQueries({ queryKey: keys.trash });
            }),
        },
      });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const generated = p.last_generate?.ok ? p.last_generate.when : null;
  return (
    <motion.div layout initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}>
      <Card
        role="link"
        tabIndex={0}
        onClick={() => navigate(`/projects/${p.id}`)}
        onKeyDown={(e) => e.key === "Enter" && navigate(`/projects/${p.id}`)}
        className="group flex h-full cursor-pointer flex-col p-4 transition-all hover:-translate-y-0.5 hover:border-foreground/15 hover:shadow-lift focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="flex items-start gap-3">
          <Monogram text={p.company || p.name} />
          <div className="min-w-0 flex-1">
            <div className="truncate text-[15px] font-semibold leading-tight tracking-tight">{p.role || p.name}</div>
            <div className="mt-0.5 truncate text-sm text-muted-foreground">{p.company || "Company not set"}</div>
          </div>
          <div onClick={(e) => e.stopPropagation()}>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon-sm" className="-mr-1.5 -mt-1 opacity-60 group-hover:opacity-100" aria-label="Project actions">
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Status</DropdownMenuLabel>
                <DropdownMenuRadioGroup value={p.status} onValueChange={(v) => setStatus.mutate(v as ProjectStatus)}>
                  {(Object.keys(STATUS_META) as ProjectStatus[]).map((s) => (
                    <DropdownMenuRadioItem key={s} value={s}>
                      <span className={cn("size-2 rounded-full", STATUS_META[s].dot)} />
                      {STATUS_META[s].label}
                    </DropdownMenuRadioItem>
                  ))}
                </DropdownMenuRadioGroup>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => duplicate.mutate()}>
                  <Copy /> Duplicate
                </DropdownMenuItem>
                <DropdownMenuItem destructive onSelect={() => setConfirmDelete(true)}>
                  <Trash2 /> Move to trash
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-1.5">
          <StatusBadge status={p.status} />
          <Badge variant="outline" className="capitalize">
            {p.template}
          </Badge>
          {p.cover_letter && <Badge variant="outline">+ cover letter</Badge>}
          {p.inputs_changed.length > 0 && (
            <Tooltip content={`Your ${p.inputs_changed.join(", ").replace("_", " ")} changed after this was generated.`}>
              <Badge variant="warning">
                <RefreshCcw /> Inputs changed
              </Badge>
            </Tooltip>
          )}
        </div>

        <div className="mt-auto flex items-center gap-2 border-t pt-3 text-xs text-muted-foreground" style={{ marginTop: "1rem" }}>
          {p.active_job ? (
            <span className="flex items-center gap-1.5 font-medium text-primary">
              <Loader2 className="size-3.5 animate-spin" /> {p.active_job.kind === "render" ? "Rendering" : "Generating"}...
            </span>
          ) : generated ? (
            <span>Generated {relativeTime(generated)}</span>
          ) : p.last_generate && !p.last_generate.ok ? (
            <span className="text-destructive">Last run failed</span>
          ) : (
            <span>Not generated yet</span>
          )}
          <span className="ml-auto flex items-center gap-1 font-medium text-foreground/80 opacity-0 transition-opacity group-hover:opacity-100">
            Open <ArrowRight className="size-3.5" />
          </span>
        </div>
      </Card>
      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent
          title="Move this project to the trash?"
          description={`"${p.name}" and its resume versions move to projects/_trash. You can restore it from the bottom of this page.`}
          confirmLabel="Move to trash"
          destructive
          onConfirm={() => remove.mutate()}
        />
      </AlertDialog>
    </motion.div>
  );
}

function TrashSection() {
  const { data } = useTrash();
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();
  const restore = useMutation({
    mutationFn: (id: string) => api.post(`/api/trash/${id}/restore`),
    onSuccess: () => {
      toast.success("Project restored");
      qc.invalidateQueries({ queryKey: keys.projects });
      qc.invalidateQueries({ queryKey: keys.trash });
    },
    onError: (e) => toast.error((e as Error).message),
  });
  if (!data?.length) return null;
  return (
    <div className="mt-10">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <Trash2 className="size-4" /> Trash ({data.length})
        <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <Card className="mt-3 divide-y">
          {data.map((t) => (
            <div key={t.id} className="flex items-center gap-3 px-4 py-3 text-sm">
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">{t.name}</div>
                <div className="text-xs text-muted-foreground">Deleted {relativeTime(t.deleted)}</div>
              </div>
              <Button size="sm" variant="outline" loading={restore.isPending && restore.variables === t.id} onClick={() => restore.mutate(t.id)}>
                <Undo2 /> Restore
              </Button>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
