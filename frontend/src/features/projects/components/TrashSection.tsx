import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Trash2, Undo2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/primitives";
import { api } from "@/lib/api/client";
import { keys, useTrash } from "@/lib/api/queries";
import { cn, relativeTime } from "@/lib/utils";

export function TrashSection() {
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
