import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookCheck, Ban, CheckCircle2, Plus, Save, Search, ShieldCheck, Sparkles, Trash2, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Callout, EmptyState, PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogContent, Select, Tabs, TabsContent, TabsList, TabsTrigger, Tooltip } from "@/components/ui/overlays";
import { AutoTextarea, Badge, Card, Input, Skeleton, Textarea } from "@/components/ui/primitives";
import { useJobs } from "@/features/jobs/JobCenter";
import { api } from "@/lib/api";
import { useDebounced } from "@/lib/hooks";
import { keys, useFacts, useGuardrails, useSystem } from "@/lib/queries";
import type { Fact, FactsPayload, GuardrailsPayload, JobSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function EvidencePage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <PageHeader
        title="Evidence"
        description="The guardrails that keep every resume truthful: a fact bank that every bullet must cite, and phrases that must never appear."
      />
      <Tabs defaultValue="facts" className="mt-6">
        <TabsList>
          <TabsTrigger value="facts">
            <BookCheck /> Fact bank
          </TabsTrigger>
          <TabsTrigger value="deny">
            <Ban /> Never-claim list
          </TabsTrigger>
        </TabsList>
        <TabsContent value="facts" className="mt-5">
          <FactBank />
        </TabsContent>
        <TabsContent value="deny" className="mt-5">
          <Guardrails />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function FactBank() {
  const { data, isLoading } = useFacts();
  const { data: system } = useSystem();
  const { track } = useJobs();
  const qc = useQueryClient();
  const [facts, setFacts] = useState<Fact[]>([]);
  const [baseline, setBaseline] = useState("");
  const [query, setQuery] = useState("");
  const [employer, setEmployer] = useState("all");
  const [confirmDraft, setConfirmDraft] = useState(false);

  useEffect(() => {
    if (!data) return;
    setFacts(data.facts);
    setBaseline(JSON.stringify(data.facts));
  }, [data]);

  const dirty = JSON.stringify(facts) !== baseline;
  const employers = useMemo(() => ["general", ...(data?.companies ?? []), "unassigned"], [data]);
  const issues = new Set(data?.employer_issues.map((i) => i.id));

  const save = useMutation({
    mutationFn: () => api.put<FactsPayload>("/api/facts", { facts: facts.filter((f) => f.text.trim()) }),
    onSuccess: (r) => {
      qc.setQueryData(keys.facts, r);
      qc.invalidateQueries({ queryKey: keys.system });
      toast.success("Fact bank saved", { description: "A backup of the previous version is in resume_archive/." });
    },
    onError: (e) => toast.error("Couldn't save", { description: (e as Error).message }),
  });

  const draft = useMutation({
    mutationFn: () => api.post<JobSummary>("/api/facts/draft", { force: !!data?.exists }),
    onSuccess: (job) => track(job, { title: "Drafting your fact bank", successMessage: "Fact bank drafted. Review the unassigned facts." }),
    onError: (e) => toast.error((e as Error).message),
  });

  const visible = facts
    .map((f, i) => ({ f, i }))
    .filter(({ f }) => (employer === "all" || f.employer === employer) && (!query || `${f.id} ${f.text} ${f.tags.join(" ")}`.toLowerCase().includes(query.toLowerCase())));

  const set = (i: number, patch: Partial<Fact>) => setFacts((list) => list.map((f, k) => (k === i ? { ...f, ...patch } : f)));
  const unassigned = facts.filter((f) => f.employer === "unassigned").length;

  if (isLoading) return <Skeleton className="h-80" />;

  if (!data?.exists && !facts.length)
    return (
      <>
        <EmptyState
          icon={BookCheck}
          title="No fact bank yet"
          description="A fact bank is a list of atomic, true facts from your profile and resume, each tagged with its employer. When you have one, every generated bullet must cite the facts it's built from, and any bullet citing another employer's fact is dropped."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Button variant="gradient" disabled={system?.onboarding_needed} loading={draft.isPending} onClick={() => draft.mutate()}>
                <Sparkles /> Draft it from my profile and resume
              </Button>
              <Button variant="outline" onClick={() => setFacts([{ id: "", employer: "general", kind: "accomplishment", text: " ", metrics: [], tags: [] }])}>
                <Plus /> Start by hand
              </Button>
            </div>
          }
        />
      </>
    );

  return (
    <div className="grid gap-4">
      {unassigned > 0 && (
        <Callout tone="warning" title={`${unassigned} fact${unassigned > 1 ? "s are" : " is"} unassigned`}>
          Unassigned facts can inform the summary but can never back a bullet. Set the employer they belong to, or "general".
        </Callout>
      )}
      {data?.employer_issues.length ? (
        <Callout tone="warning" title="Some employers don't match your base resume">
          {data.employer_issues.map((i) => `${i.id} (${i.employer})`).join(", ")}. The pipeline treats these as unassigned until fixed.
        </Callout>
      ) : null}

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search facts, ids, tags" className="pl-8" />
        </div>
        <Select
          aria-label="Filter by employer"
          value={employer}
          onValueChange={setEmployer}
          className="sm:w-56"
          options={[{ value: "all", label: "All employers" }, ...employers.map((e) => ({ value: e, label: e }))]}
        />
        <Button variant="outline" onClick={() => setConfirmDraft(true)} disabled={system?.onboarding_needed}>
          <Sparkles /> Redraft
        </Button>
        <Button
          variant="outline"
          onClick={() => setFacts((list) => [...list, { id: "", employer: employer === "all" ? "general" : employer, kind: "accomplishment", text: " ", metrics: [], tags: [] }])}
        >
          <Plus /> Add fact
        </Button>
        <Button disabled={!dirty} loading={save.isPending} onClick={() => save.mutate()}>
          <Save /> Save
        </Button>
      </div>

      <Card className="overflow-hidden">
        <div className="hidden grid-cols-[72px_190px_130px_1fr_36px] gap-3 border-b bg-muted/40 px-4 py-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground md:grid">
          <span>Id</span>
          <span>Employer</span>
          <span>Kind</span>
          <span>Fact, metrics, tags</span>
          <span />
        </div>
        <ul className="divide-y">
          {visible.map(({ f, i }) => (
            <li
              key={`${f.id}-${i}`}
              className={cn(
                "grid gap-2 px-4 py-3 md:grid-cols-[72px_190px_130px_1fr_36px] md:gap-3",
                (f.employer === "unassigned" || issues.has(f.id)) && "bg-warning/[0.04]",
              )}
            >
              <span className="pt-2 font-mono text-xs font-medium text-primary">{f.id || "new"}</span>
              <Select
                aria-label="Employer"
                value={employers.includes(f.employer) ? f.employer : "unassigned"}
                onValueChange={(v) => set(i, { employer: v })}
                className="h-8 text-[13px]"
                options={employers.map((e) => ({ value: e, label: e }))}
              />
              <Select
                aria-label="Kind"
                value={f.kind}
                onValueChange={(v) => set(i, { kind: v })}
                className="h-8 text-[13px] capitalize"
                options={(data?.kinds ?? []).map((k) => ({ value: k, label: <span className="capitalize">{k}</span> }))}
              />
              <div className="grid gap-1.5">
                <AutoTextarea value={f.text} onChange={(e) => set(i, { text: e.target.value })} className="min-h-[34px] py-1.5 text-[13px]" aria-label="Fact text" />
                <div className="grid gap-1.5 sm:grid-cols-2">
                  <Input
                    value={f.metrics.join(", ")}
                    onChange={(e) => set(i, { metrics: e.target.value.split(",").map((m) => m.trim()).filter(Boolean) })}
                    placeholder="Metrics, e.g. $300k, 200+ hours"
                    className="h-7 text-xs"
                    aria-label="Metrics"
                  />
                  <Input
                    value={f.tags.join(", ")}
                    onChange={(e) => set(i, { tags: e.target.value.split(",").map((m) => m.trim()).filter(Boolean) })}
                    placeholder="Tags, e.g. causal inference"
                    className="h-7 text-xs"
                    aria-label="Tags"
                  />
                </div>
              </div>
              <Tooltip content="Delete fact">
                <Button variant="ghost" size="icon-sm" className="text-muted-foreground hover:text-destructive" onClick={() => setFacts((l) => l.filter((_, k) => k !== i))} aria-label="Delete fact">
                  <Trash2 className="size-4" />
                </Button>
              </Tooltip>
            </li>
          ))}
          {!visible.length && <li className="px-4 py-8 text-center text-sm text-muted-foreground">No facts match.</li>}
        </ul>
      </Card>
      <p className="text-xs text-muted-foreground">
        {facts.length} facts. Keep ids stable once you've generated resumes, since each bullet's citations point to them.
      </p>

      <AlertDialog open={confirmDraft} onOpenChange={setConfirmDraft}>
        <AlertDialogContent
          title="Redraft the whole fact bank?"
          description="Claude re-extracts every fact from your profile and base resume. Your current bank, including hand edits, is backed up to resume_archive/ first."
          confirmLabel="Redraft"
          onConfirm={() => draft.mutate()}
        />
      </AlertDialog>
    </div>
  );
}

function Guardrails() {
  const { data, isLoading } = useGuardrails();
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [phrase, setPhrase] = useState("");
  useEffect(() => {
    if (data) setText(data.text);
  }, [data]);

  const debouncedText = useDebounced(text, 300);
  const debouncedPhrase = useDebounced(phrase, 250);
  const check = useQuery({
    queryKey: ["guardrails-test", debouncedText, debouncedPhrase],
    queryFn: () =>
      api.post<{ matches: string[]; patterns: GuardrailsPayload["patterns"] }>("/api/guardrails/test", {
        text: debouncedText,
        phrase: debouncedPhrase,
      }),
    enabled: !!data,
    placeholderData: (prev) => prev,
  });
  const patterns = check.data?.patterns ?? data?.patterns ?? [];
  const invalid = patterns.filter((p) => p.error);

  const save = useMutation({
    mutationFn: () => api.put<GuardrailsPayload>("/api/guardrails", { text }),
    onSuccess: (r) => {
      qc.setQueryData(keys.guardrails, r);
      qc.invalidateQueries({ queryKey: keys.system });
      toast.success("Never-claim list saved");
    },
    onError: (e) => toast.error((e as Error).message),
  });

  if (isLoading) return <Skeleton className="h-80" />;
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
      <Card className="p-5">
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-primary" />
          <h3 className="text-sm font-semibold">Phrases that must never appear</h3>
          <Badge variant="secondary" className="ml-auto">
            {patterns.length - invalid.length} active
          </Badge>
        </div>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          One case-insensitive regular expression per line; lines starting with # are comments. Claude is told about them, and any
          match in a generated or edited resume blocks it from being written.
        </p>
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          spellCheck={false}
          className="mt-4 min-h-[420px] font-mono text-[12.5px] leading-6"
          aria-label="Never-claim patterns"
        />
        {invalid.length > 0 && (
          <div className="mt-3 grid gap-1">
            {invalid.map((p) => (
              <p key={p.line} className="flex items-center gap-1.5 text-xs text-destructive">
                <XCircle className="size-3.5" /> Line {p.line}: {p.error}
              </p>
            ))}
          </div>
        )}
        <div className="mt-4 flex justify-end">
          <Button disabled={text === data?.text || invalid.length > 0} loading={save.isPending} onClick={() => save.mutate()}>
            <Save /> Save list
          </Button>
        </div>
      </Card>

      <div className="grid content-start gap-4">
        <Card className="p-5">
          <h3 className="text-sm font-semibold">Test a phrase</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">Try a sentence to see whether it would be blocked.</p>
          <Textarea
            value={phrase}
            onChange={(e) => setPhrase(e.target.value)}
            placeholder="e.g. AWS certified machine learning engineer"
            className="mt-3 min-h-[90px]"
            aria-label="Phrase to test"
          />
          {phrase.trim() &&
            (check.data?.matches.length ? (
              <div className="mt-3 rounded-lg border border-destructive/30 bg-destructive/[0.06] p-3 text-sm">
                <div className="flex items-center gap-1.5 font-medium text-destructive">
                  <Ban className="size-4" /> Blocked
                </div>
                <ul className="mt-1.5 grid gap-1">
                  {check.data.matches.map((m) => (
                    <li key={m} className="font-mono text-xs text-muted-foreground">
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="mt-3 flex items-center gap-1.5 rounded-lg border border-success/30 bg-success/[0.07] p-3 text-sm font-medium text-success">
                <CheckCircle2 className="size-4" /> Allowed
              </div>
            ))}
        </Card>
        <Callout title="Tip: use phrases, not bare words">
          Block "as a software engineer", not "engineer", so "partnered with engineers" still reads fine.
        </Callout>
      </div>
    </div>
  );
}
