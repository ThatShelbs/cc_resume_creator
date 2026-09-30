import { ChevronDown } from "lucide-react";
import { STATUS_META, StatusBadge } from "@/components/shared/common";
import { DropdownMenu, DropdownMenuContent, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger } from "@/components/ui/overlays";
import type { Project, ProjectStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export function StatusMenu({ project, onChange }: { project: Project; onChange: (s: ProjectStatus) => void }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="rounded-full focus-visible:ring-2 focus-visible:ring-ring" aria-label="Change status">
        <span className="inline-flex items-center gap-0.5">
          <StatusBadge status={project.status} />
          <ChevronDown className="size-3 text-muted-foreground" />
        </span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuLabel>Status</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={project.status} onValueChange={(v) => onChange(v as ProjectStatus)}>
          {(Object.keys(STATUS_META) as ProjectStatus[]).map((s) => (
            <DropdownMenuRadioItem key={s} value={s}>
              <span className={cn("size-2 rounded-full", STATUS_META[s].dot)} />
              {STATUS_META[s].label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
