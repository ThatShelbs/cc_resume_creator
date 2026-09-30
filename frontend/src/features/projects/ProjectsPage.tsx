import { AnimatePresence, motion } from "framer-motion";
import { Briefcase, Inbox, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState, PageHeader } from "@/components/shared/common";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/overlays";
import { Input, Skeleton } from "@/components/ui/primitives";
import { useProjects, useSystem } from "@/lib/api/queries";
import type { ProjectStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { SetupCard } from "@/features/projects/components/SetupCard";
import { StatsStrip } from "@/features/projects/components/StatsStrip";
import { ImportCallout } from "@/features/projects/components/ImportCallout";
import { ProjectCard } from "@/features/projects/components/ProjectCard";
import { TrashSection } from "@/features/projects/components/TrashSection";

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
