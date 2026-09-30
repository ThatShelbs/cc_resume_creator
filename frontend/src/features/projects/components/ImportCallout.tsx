import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileDown } from "lucide-react";
import { toast } from "sonner";
import { Callout } from "@/components/shared/common";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { keys, useImportCandidates } from "@/lib/api/queries";
import { plural } from "@/lib/utils";

export function ImportCallout() {
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
