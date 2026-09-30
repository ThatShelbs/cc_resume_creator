import { FileUp, Loader2 } from "lucide-react";
import { useRef, useState, type DragEvent } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api/client";
import type { UploadResult } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/** Drag-and-drop (or click) upload for a resume PDF or Word file. */
export function ResumeDropzone({ onUploaded, compact }: { onUploaded: (r: UploadResult) => void; compact?: boolean }) {
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const upload = async (file: File) => {
    if (!/\.(pdf|docx)$/i.test(file.name)) {
      toast.error("Upload a .pdf or .docx file");
      return;
    }
    setBusy(true);
    try {
      onUploaded(await api.upload<UploadResult>("/api/resume/upload", file));
    } catch (e) {
      toast.error("Couldn't read that resume", { description: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) upload(f);
  };

  return (
    <button
      type="button"
      onClick={() => input.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      disabled={busy}
      className={cn(
        "group flex w-full flex-col items-center justify-center rounded-xl border-2 border-dashed bg-card/50 px-6 text-center transition-all hover:border-primary/50 hover:bg-primary/[0.03] disabled:cursor-wait",
        compact ? "py-8" : "py-14",
        dragging && "border-primary bg-primary/[0.06]",
      )}
    >
      <div className="flex size-12 items-center justify-center rounded-2xl border bg-background shadow-soft transition-transform group-hover:-translate-y-0.5">
        {busy ? <Loader2 className="size-5 animate-spin text-primary" /> : <FileUp className="size-5 text-primary" />}
      </div>
      <div className="mt-4 text-sm font-medium">{busy ? "Reading your resume..." : "Drop your resume here, or click to browse"}</div>
      <div className="mt-1 text-xs text-muted-foreground">PDF or Word (.docx), up to 20 MB. It stays on this computer.</div>
      <input
        ref={input}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          e.target.value = "";
          if (f) upload(f);
        }}
      />
    </button>
  );
}
