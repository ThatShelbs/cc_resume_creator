import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BookOpen, CheckCircle2, FolderOpen, Power, Save, XCircle } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common";
import { ThemeSegmented } from "@/components/layout/ThemeToggle";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogContent, Select } from "@/components/ui/overlays";
import { Card, Input, Separator, Skeleton, Switch } from "@/components/ui/primitives";
import { TemplatePicker } from "@/features/projects/TemplatePicker";
import { api, withToken } from "@/lib/api";
import { keys, useSettings, useSystem } from "@/lib/queries";
import type { Settings, TemplateKey } from "@/lib/types";
import { cn } from "@/lib/utils";

function Row({ title, description, children, className }: { title: string; description?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={cn("grid gap-3 py-5 first:pt-0 last:pb-0 md:grid-cols-[260px_1fr] md:gap-8", className)}>
      <div>
        <div className="text-sm font-medium">{title}</div>
        {description && <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</p>}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const { data: settings, isLoading } = useSettings();
  const { data: system } = useSystem();
  const qc = useQueryClient();
  const [form, setForm] = useState<Settings | null>(null);
  const [quit, setQuit] = useState(false);
  const [stopped, setStopped] = useState(false);

  useEffect(() => {
    if (settings) setForm(settings);
  }, [settings]);

  const dirty = !!form && JSON.stringify(form) !== JSON.stringify(settings);
  const save = useMutation({
    mutationFn: (s: Settings) => api.put<Settings>("/api/settings", s),
    onSuccess: (s) => {
      qc.setQueryData(keys.settings, s);
      toast.success("Settings saved");
    },
    onError: (e) => toast.error((e as Error).message),
  });
  const openFolder = (target: string) => api.post("/api/system/open-folder", { target }).catch((e) => toast.error((e as Error).message));

  if (stopped)
    return (
      <div className="mx-auto max-w-lg px-6 pt-24 text-center">
        <Power className="mx-auto size-8 text-muted-foreground" />
        <h1 className="mt-4 text-xl font-semibold">Resume Studio has stopped</h1>
        <p className="mt-2 text-sm text-muted-foreground">You can close this tab. Run the launcher again whenever you need it.</p>
      </div>
    );

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <PageHeader
        title="Settings"
        actions={
          <Button disabled={!dirty} loading={save.isPending} onClick={() => form && save.mutate(form)}>
            <Save /> Save changes
          </Button>
        }
      />

      <Card className="mt-6 divide-y p-6">
        <Row title="Appearance" description="Day, night, or follow your operating system.">
          <ThemeSegmented />
        </Row>
      </Card>

      <h2 className="mt-8 text-sm font-semibold">Generation</h2>
      {isLoading || !form ? (
        <Skeleton className="mt-3 h-72" />
      ) : (
        <Card className="mt-3 divide-y p-6">
          <Row title="Claude model" description="Sonnet is fast and strong at writing. Opus is the most capable and a bit slower.">
            <div className="flex flex-wrap gap-2">
              <Select
                aria-label="Model"
                value={(system?.models ?? []).includes(form.model) ? form.model : "custom"}
                onValueChange={(v) => v !== "custom" && setForm({ ...form, model: v })}
                className="w-48"
                options={[...(system?.models ?? ["sonnet", "opus", "haiku"]).map((m) => ({ value: m, label: <span className="capitalize">{m}</span> })), { value: "custom", label: "Custom model id" }]}
              />
              {!(system?.models ?? []).includes(form.model) && (
                <Input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} className="w-56" aria-label="Custom model id" />
              )}
            </div>
          </Row>
          <Row title="Reasoning effort" description="Higher effort can improve tailoring and takes longer.">
            <div role="radiogroup" className="inline-grid grid-cols-3 gap-1 rounded-lg bg-secondary p-1">
              {(system?.efforts ?? ["low", "medium", "high"]).map((e) => (
                <button
                  key={e}
                  type="button"
                  role="radio"
                  aria-checked={form.effort === e}
                  onClick={() => setForm({ ...form, effort: e })}
                  className={cn(
                    "rounded-md px-4 py-1.5 text-[13px] font-medium capitalize text-muted-foreground transition-all",
                    form.effort === e && "bg-background text-foreground shadow-soft",
                  )}
                >
                  {e}
                </button>
              ))}
            </div>
          </Row>
          <Row title="Timeout per Claude call" description="How long to wait for one response before giving up.">
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={120}
                max={1800}
                step={60}
                value={form.timeout_seconds}
                onChange={(e) => setForm({ ...form, timeout_seconds: Number(e.target.value) })}
                className="w-56 accent-[hsl(var(--primary))]"
                aria-label="Timeout in seconds"
              />
              <span className="text-sm tabular-nums">{Math.round(form.timeout_seconds / 60)} min</span>
            </div>
          </Row>
          <Row title="Cover letter by default" description="New projects start with the cover letter switched on.">
            <Switch checked={form.cover_letter_default} onCheckedChange={(v) => setForm({ ...form, cover_letter_default: v })} aria-label="Cover letter by default" />
          </Row>
          <Row title="Default template" description="Used for new projects. Each project can switch anytime.">
            <TemplatePicker size="sm" value={form.default_template as TemplateKey} onChange={(t) => setForm({ ...form, default_template: t })} />
          </Row>
        </Card>
      )}

      <h2 className="mt-8 text-sm font-semibold">System</h2>
      <Card className="mt-3 divide-y p-6">
        <Row title="Claude Code CLI" description="Generation runs through your logged-in Claude subscription. No API key needed.">
          <Status ok={!!system?.claude.found} label={system?.claude.found ? (system.claude.version ?? "Installed") : "Not found on PATH"} />
          {system?.claude.path && <p className="mt-1 truncate text-xs text-muted-foreground">{system.claude.path}</p>}
          <p className="mt-2 text-xs text-muted-foreground">
            If generation says you're signed out, run <code className="rounded bg-muted px-1">claude /login</code> in a terminal.
          </p>
        </Row>
        <Row title="PDF export" description="Uses Microsoft Word on Windows. Without it you still get .docx files.">
          <Status ok={!!system?.word} label={system?.word ? "Microsoft Word available" : "Word not found"} />
        </Row>
        <Row title="Your data" description="Everything stays on this computer, in plain files you can open.">
          <p className="truncate font-mono text-xs text-muted-foreground">{system?.data_root}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => openFolder("projects")}>
              <FolderOpen /> Projects
            </Button>
            <Button size="sm" variant="outline" onClick={() => openFolder("inputs")}>
              <FolderOpen /> Inputs
            </Button>
            <Button size="sm" variant="outline" onClick={() => openFolder("archive")}>
              <FolderOpen /> Backups
            </Button>
          </div>
        </Row>
        <Row title="About" description={`Resume Studio ${system?.version ?? ""}`}>
          <div className="flex flex-wrap gap-2">
            <Button asChild size="sm" variant="outline">
              <a href={withToken("/api/docs")} target="_blank" rel="noreferrer">
                <BookOpen /> API reference
              </a>
            </Button>
            <Button size="sm" variant="outline" className="text-destructive hover:text-destructive" onClick={() => setQuit(true)}>
              <Power /> Quit Resume Studio
            </Button>
          </div>
        </Row>
      </Card>
      <Separator className="my-8 opacity-0" />

      <AlertDialog open={quit} onOpenChange={setQuit}>
        <AlertDialogContent
          title="Quit Resume Studio?"
          description="This stops the local server. Any running generation is stopped too. Start it again from the launcher."
          confirmLabel="Quit"
          destructive
          onConfirm={() => api.post("/api/system/shutdown").finally(() => setStopped(true))}
        />
      </AlertDialog>
    </div>
  );
}

function Status({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className={cn("flex items-center gap-1.5 text-sm font-medium", ok ? "text-success" : "text-destructive")}>
      {ok ? <CheckCircle2 className="size-4" /> : <XCircle className="size-4" />}
      {label}
    </div>
  );
}
