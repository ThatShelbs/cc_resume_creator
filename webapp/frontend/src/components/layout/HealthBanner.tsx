import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, KeyRound, Sparkles, Terminal, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useSystem } from "@/lib/queries";

const DISMISS_KEY = "studio-dismissed-word-banner";

/** System problems that would make generation fail, surfaced up front. */
export function HealthBanner() {
  const { data } = useSystem();
  const [wordDismissed, setWordDismissed] = useState(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === "1";
    } catch {
      return false;
    }
  });
  const qc = useQueryClient();
  const clearSample = useMutation({
    mutationFn: () => api.post<{ backup: string | null }>("/api/demo/clear"),
    onSuccess: async (r) => {
      await qc.invalidateQueries();
      toast.success(r.backup ? `Sample data cleared. Your edits were saved to ${r.backup}` : "Sample data cleared.");
    },
    onError: (e: Error) => toast.error(e.message),
  });
  if (!data) return null;

  if (!data.claude.found) {
    return (
      <div className="flex items-start gap-3 border-b border-destructive/25 bg-destructive/[0.07] px-4 py-2.5 text-sm sm:px-6">
        <Terminal className="mt-0.5 size-4 shrink-0 text-destructive" />
        <p className="leading-relaxed">
          <span className="font-medium">The Claude Code CLI wasn't found.</span>{" "}
          <span className="text-muted-foreground">
            Close this window and double-click <code className="rounded bg-background/70 px-1">Launch Resume Studio.bat</code>{" "}
            again; it installs and signs in for you. You can still edit everything in the meantime.
          </span>
        </p>
      </div>
    );
  }

  if (data.claude.logged_in === false && !data.api_key.set) {
    return (
      <div className="flex items-start gap-3 border-b border-warning/25 bg-warning/[0.07] px-4 py-2.5 text-sm sm:px-6">
        <KeyRound className="mt-0.5 size-4 shrink-0 text-warning" />
        <p className="leading-relaxed">
          <span className="font-medium">Not signed in to Claude yet.</span>{" "}
          <span className="text-muted-foreground">
            Run <code className="rounded bg-background/70 px-1">claude /login</code> in a terminal, or{" "}
            <Link to="/settings" className="underline">
              paste an API key in Settings
            </Link>
            . You can still edit everything in the meantime.
          </span>
        </p>
      </div>
    );
  }

  if (data.sample_loaded) {
    return (
      <div className="flex flex-wrap items-center gap-3 border-b border-primary/25 bg-primary/[0.06] px-4 py-2 text-sm sm:px-6">
        <Sparkles className="size-4 shrink-0 text-primary" />
        <p className="min-w-0 flex-1 text-muted-foreground">
          <span className="font-medium text-foreground">Sample data.</span> This is a made-up applicant for exploring. Clear it
          before adding your own resume.
        </p>
        <Button size="sm" variant="outline" disabled={clearSample.isPending} onClick={() => clearSample.mutate()}>
          Clear sample data
        </Button>
      </div>
    );
  }

  if (!data.word && !wordDismissed) {
    return (
      <div className="flex items-center gap-3 border-b border-warning/25 bg-warning/[0.07] px-4 py-2 text-sm sm:px-6">
        <AlertTriangle className="size-4 shrink-0 text-warning" />
        <p className="flex-1 text-muted-foreground">
          <span className="font-medium text-foreground">PDF export needs Microsoft Word on Windows.</span> You'll still get a
          .docx for every resume.
        </p>
        <button
          type="button"
          className="rounded p-1 text-muted-foreground hover:bg-background/60 hover:text-foreground"
          aria-label="Dismiss"
          onClick={() => {
            setWordDismissed(true);
            try {
              localStorage.setItem(DISMISS_KEY, "1");
            } catch {
              /* ignore */
            }
          }}
        >
          <X className="size-4" />
        </button>
      </div>
    );
  }
  return null;
}
