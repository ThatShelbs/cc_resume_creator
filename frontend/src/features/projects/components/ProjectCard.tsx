import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Copy, Loader2, MoreHorizontal, RefreshCcw, Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Monogram, STATUS_META, StatusBadge } from "@/components/shared/common";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogContent, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuTrigger, Tooltip } from "@/components/ui/overlays";
import { Badge, Card } from "@/components/ui/primitives";
import { api } from "@/lib/api/client";
import { keys } from "@/lib/api/queries";
import type { Project, ProjectStatus } from "@/lib/api/types";
import { cn, relativeTime } from "@/lib/utils";

export function ProjectCard({ project: p }: { project: Project }) {
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
