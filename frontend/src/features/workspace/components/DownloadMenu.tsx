import { ChevronDown, Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/overlays";
import { projectFileUrl } from "@/lib/api/client";
import type { FileInfo } from "@/lib/api/types";
import { formatBytes } from "@/lib/utils";

export function DownloadMenu({ pid, outputs }: { pid: string; outputs: FileInfo[] }) {
  const label = (name: string) => {
    const kind = name.startsWith("out_cover_letter_") ? "Cover letter" : name.endsWith("_report.md") ? "Tailoring report" : "Resume";
    const ext = name.endsWith("_report.md") ? ".md" : name.slice(name.lastIndexOf("."));
    return { kind, ext };
  };
  const files = [...outputs].sort((a, b) => a.name.localeCompare(b.name));
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" disabled={!files.length}>
          <Download /> Download <ChevronDown className="!size-3.5 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        {files.map((f) => {
          const { kind, ext } = label(f.name);
          return (
            <DropdownMenuItem key={f.name} asChild>
              <a href={projectFileUrl(pid, f.name, { download: true })} download>
                <FileText />
                <span className="flex-1">
                  {kind} <span className="text-muted-foreground">{ext}</span>
                </span>
                <span className="text-[11px] text-muted-foreground">{formatBytes(f.size)}</span>
              </a>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
