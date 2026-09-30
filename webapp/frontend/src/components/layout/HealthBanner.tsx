import { AlertTriangle, Terminal, X } from "lucide-react";
import { useState } from "react";
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
  if (!data) return null;

  if (!data.claude.found) {
    return (
      <div className="flex items-start gap-3 border-b border-destructive/25 bg-destructive/[0.07] px-4 py-2.5 text-sm sm:px-6">
        <Terminal className="mt-0.5 size-4 shrink-0 text-destructive" />
        <p className="leading-relaxed">
          <span className="font-medium">The Claude Code CLI wasn't found.</span>{" "}
          <span className="text-muted-foreground">
            Install it with <code className="rounded bg-background/70 px-1">npm install -g @anthropic-ai/claude-code</code>, run{" "}
            <code className="rounded bg-background/70 px-1">claude /login</code>, then restart Resume Studio. You can still edit
            everything in the meantime.
          </span>
        </p>
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
