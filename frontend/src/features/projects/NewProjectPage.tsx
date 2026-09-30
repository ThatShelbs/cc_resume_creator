import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ClipboardPaste, FileUp, Sparkles, Wand2 } from "lucide-react";
import { useEffect, useRef, useState, type DragEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Callout, PageHeader } from "@/components/shared/common";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, Field, Input, Switch, Textarea } from "@/components/ui/primitives";
import { useJobs } from "@/features/jobs/JobCenter";
import { api } from "@/lib/api/client";
import { keys, useSettings, useSystem } from "@/lib/api/queries";
import type { JobSummary, Project, TemplateKey } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { TemplatePicker } from "./TemplatePicker";

const MIN_POSTING = 40;

export default function NewProjectPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { track } = useJobs();
  const { data: system } = useSystem();
  const { data: settings } = useSettings();

  const [jobText, setJobText] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [url, setUrl] = useState("");
  const [template, setTemplate] = useState<TemplateKey | null>(null);
  const [coverLetter, setCoverLetter] = useState<boolean | null>(null);
  const [dragging, setDragging] = useState(false);
  const touched = useRef({ company: false, role: false });
  const fileInput = useRef<HTMLInputElement>(null);

  const effectiveTemplate = template ?? ((settings?.default_template as TemplateKey) || "classic");
  const effectiveCover = coverLetter ?? settings?.cover_letter_default ?? false;
  const ready = !system?.onboarding_needed;
  const tooShort = jobText.trim().length < MIN_POSTING;

  // Suggest company and role from the posting, without overwriting edits.
  useEffect(() => {
    if (tooShort || (touched.current.company && touched.current.role)) return;
    const t = window.setTimeout(async () => {
      try {
        const g = await api.post<{ company: string; role: string }>("/api/projects/guess", { text: jobText });
        if (!touched.current.company && g.company) setCompany(g.company);
        if (!touched.current.role && g.role) setRole(g.role);
      } catch {
        /* suggestions are optional */
      }
    }, 450);
    return () => window.clearTimeout(t);
  }, [jobText, tooShort]);

  const create = useMutation({
    mutationFn: (generate: boolean) =>
      api.post<{ project: Project; job: JobSummary | null }>("/api/projects", {
        job_text: jobText,
        company,
        role,
        url,
        template: effectiveTemplate,
        cover_letter: effectiveCover,
        generate,
      }),
    onSuccess: ({ project, job }) => {
      qc.invalidateQueries({ queryKey: keys.projects });
      if (job) {
        track(job, { title: `Tailoring for ${project.company || project.name}`, coverLetter: effectiveCover, successMessage: "Your tailored resume is ready" });
      } else {
        toast.success("Project saved");
      }
      navigate(`/projects/${project.id}`);
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const loadFile = async (file: File) => {
    try {
      const r = await api.upload<{ text: string; company: string; role: string }>("/api/projects/extract-posting", file);
      setJobText(r.text);
      if (!touched.current.company && r.company) setCompany(r.company);
      if (!touched.current.role && r.role) setRole(r.role);
      toast.success(`Loaded ${file.name}`);
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) loadFile(file);
  };

  const pasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text.trim()) setJobText(text);
      else toast("Your clipboard is empty");
    } catch {
      toast("Press Ctrl+V in the box to paste");
    }
  };

  const words = jobText.trim() ? jobText.trim().split(/\s+/).length : 0;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2 mb-3 text-muted-foreground">
        <Link to="/">
          <ArrowLeft /> Projects
        </Link>
      </Button>
      <PageHeader
        title="New project"
        description="Paste the job posting you're applying to. Resume Taylor tailors your real experience to it, and every claim stays traceable to your own materials."
      />

      {!ready && (
        <Callout
          tone="warning"
          className="mt-6"
          title="Finish setup to generate"
          action={
            <Button asChild size="sm" variant="outline">
              <Link to="/welcome">Start setup</Link>
            </Button>
          }
        >
          You can save this posting now. Generating needs your base resume and profile.
        </Callout>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_340px]">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
            <div>
              <CardTitle>Job posting</CardTitle>
              <CardDescription>Paste the full text, including requirements and responsibilities.</CardDescription>
            </div>
            <div className="flex shrink-0 gap-1.5">
              <Button variant="outline" size="sm" onClick={pasteFromClipboard}>
                <ClipboardPaste /> Paste
              </Button>
              <Button variant="outline" size="sm" onClick={() => fileInput.current?.click()}>
                <FileUp /> File
              </Button>
              <input
                ref={fileInput}
                type="file"
                accept=".txt,.md,.pdf,.docx"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && loadFile(e.target.files[0])}
              />
            </div>
          </CardHeader>
          <CardContent>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={cn("relative rounded-lg transition-shadow", dragging && "ring-2 ring-primary ring-offset-2 ring-offset-background")}
            >
              <Textarea
                autoFocus
                value={jobText}
                onChange={(e) => setJobText(e.target.value)}
                placeholder={"Director, Customer Analytics\n\nAbout the role\nYou will lead a team of analysts...\n\nTip: you can also drop a .docx, .pdf, or .txt file here."}
                className="min-h-[420px] resize-y font-[450] leading-relaxed"
                aria-label="Job posting text"
              />
              {dragging && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-lg bg-primary/5 text-sm font-medium text-primary">
                  Drop to load the posting
                </div>
              )}
            </div>
            <div className="mt-2 flex justify-between text-xs text-muted-foreground">
              <span>{tooShort && jobText ? "Keep going: that looks shorter than a full posting." : " "}</span>
              <span className="tabular-nums">{words.toLocaleString()} words</span>
            </div>
          </CardContent>
        </Card>

        <div className="grid content-start gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Details
                {(company || role) && !tooShort && (
                  <span className="flex items-center gap-1 text-xs font-normal text-muted-foreground">
                    <Wand2 className="size-3" /> suggested from the posting
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <Field label="Company" htmlFor="company">
                <Input
                  id="company"
                  value={company}
                  onChange={(e) => {
                    touched.current.company = true;
                    setCompany(e.target.value);
                  }}
                  placeholder="Example Co."
                />
              </Field>
              <Field label="Role" htmlFor="role">
                <Input
                  id="role"
                  value={role}
                  onChange={(e) => {
                    touched.current.role = true;
                    setRole(e.target.value);
                  }}
                  placeholder="Director, Customer Analytics"
                />
              </Field>
              <Field label="Posting link" hint="Optional, for your records." htmlFor="url">
                <Input id="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" />
              </Field>
              <label className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2.5">
                <span>
                  <span className="block text-sm font-medium">Cover letter</span>
                  <span className="block text-xs text-muted-foreground">Built only from the validated resume</span>
                </span>
                <Switch checked={effectiveCover} onCheckedChange={setCoverLetter} aria-label="Also write a cover letter" />
              </label>
            </CardContent>
          </Card>

          <div className="grid gap-2">
            <Button
              variant="gradient"
              size="lg"
              disabled={tooShort || !ready}
              loading={create.isPending && create.variables === true}
              onClick={() => create.mutate(true)}
            >
              <Sparkles /> Save and generate
            </Button>
            <Button variant="outline" disabled={tooShort} loading={create.isPending && create.variables === false} onClick={() => create.mutate(false)}>
              Save as draft
            </Button>
            <p className="px-1 text-center text-xs leading-relaxed text-muted-foreground">
              Generation takes a minute or two and uses your Claude subscription through the Claude Code CLI.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-sm font-semibold tracking-tight">Template</h2>
        <p className="mb-3 mt-0.5 text-sm text-muted-foreground">
          All three are single-column and ATS-friendly. You can switch any time without regenerating.
        </p>
        <TemplatePicker value={effectiveTemplate} onChange={setTemplate} />
      </div>
    </div>
  );
}
