import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, BookCheck, Check, FileText, PartyPopper, Plus, ShieldCheck, Sparkles, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Logo } from "@/components/common";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Card, Skeleton } from "@/components/ui/primitives";
import { useJobs } from "@/features/jobs/JobCenter";
import { cleanProfile } from "@/features/profile/ProfilePage";
import { ProfileEditor } from "@/features/profile/ProfileEditor";
import { ResumeFlow, type Prefill } from "@/features/resume/ResumeFlow";
import { api } from "@/lib/api";
import { keys, useProfile, useSystem } from "@/lib/queries";
import type { JobSummary, Profile, ProfilePayload } from "@/lib/types";
import { cn, uid } from "@/lib/utils";

const STEPS = [
  { key: "welcome", label: "Welcome", icon: Sparkles },
  { key: "resume", label: "Base resume", icon: FileText },
  { key: "profile", label: "Profile", icon: UserRound },
  { key: "facts", label: "Fact bank", icon: BookCheck },
  { key: "done", label: "First project", icon: Plus },
] as const;

function profileFromPrefill(p: Prefill | null): Profile {
  return {
    contact: { name: p?.name ?? "", email: p?.email ?? "", phone: p?.phone ?? "", location: p?.location ?? "", linkedin: p?.linkedin ?? "" },
    sections: [
      { id: uid(), title: "Skills", items: p?.skills?.length ? p.skills : [""] },
      { id: uid(), title: "Software/Tools", items: [""] },
      { id: uid(), title: "Projects", items: [""] },
      { id: uid(), title: "Recent Awards", items: [""] },
    ],
  };
}

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [prefill, setPrefill] = useState<Prefill | null>(null);
  const { data: system } = useSystem();
  const go = (i: number) => setStep(Math.max(0, Math.min(STEPS.length - 1, i)));

  return (
    <div className="min-h-screen bg-canvas">
      <header className="flex h-16 items-center justify-between px-5 sm:px-8">
        <Logo />
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild variant="ghost" size="sm">
            <Link to="/">Exit setup</Link>
          </Button>
        </div>
      </header>
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-5 pb-16 pt-4 sm:px-8 md:grid-cols-[220px_minmax(0,1fr)]">
        <nav aria-label="Setup steps" className="min-w-0 md:sticky md:top-8 md:self-start">
          <ol className="flex gap-2 overflow-x-auto md:grid md:gap-1">
            {STEPS.map((s, i) => {
              const done =
                (s.key === "resume" && system?.inputs.resume) ||
                (s.key === "profile" && system?.inputs.profile) ||
                (s.key === "facts" && system?.inputs.fact_bank) ||
                (s.key === "welcome" && step > 0);
              return (
                <li key={s.key}>
                  <button
                    type="button"
                    onClick={() => go(i)}
                    className={cn(
                      "flex w-full shrink-0 items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-secondary",
                      step === i && "bg-card font-medium shadow-soft ring-1 ring-border",
                    )}
                  >
                    <span
                      className={cn(
                        "flex size-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-medium",
                        done ? "border-success bg-success text-success-foreground" : step === i ? "border-primary text-primary" : "text-muted-foreground",
                      )}
                    >
                      {done ? <Check className="size-3.5" strokeWidth={3} /> : i + 1}
                    </span>
                    <span className="whitespace-nowrap">{s.label}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -12 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="min-w-0"
          >
            {step === 0 && <Welcome onNext={() => go(1)} />}
            {step === 1 && <ResumeStep onNext={(p) => (p && setPrefill(p), go(2))} onBack={() => go(0)} />}
            {step === 2 && <ProfileStep prefill={prefill} onNext={() => go(3)} onBack={() => go(1)} />}
            {step === 3 && <FactsStep onNext={() => go(4)} onBack={() => go(2)} />}
            {step === 4 && <DoneStep />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

function StepHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="mb-6">
      <div className="text-xs font-medium uppercase tracking-wide text-primary">{eyebrow}</div>
      <h1 className="mt-1.5 text-balance text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
      {children && <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">{children}</p>}
    </div>
  );
}

function Welcome({ onNext }: { onNext: () => void }) {
  const points = [
    { icon: FileText, title: "Your real history, nothing else", text: "Every bullet is selected and rephrased from your own resume and profile. Titles, employers, and dates are copied exactly." },
    { icon: ShieldCheck, title: "Checked before it's written", text: "Numbers are verified against your materials, bullets cite their facts, and a never-claim list blocks overreach." },
    { icon: Sparkles, title: "Tailored to each posting", text: "Emphasis, ordering, and wording follow the job you paste, using your Claude subscription. Nothing leaves this computer otherwise." },
  ];
  return (
    <div>
      <StepHeader eyebrow="Welcome to Resume Studio" title="Truthful resumes, tailored to every job">
        Setup takes about two minutes: upload the resume you already have, confirm your profile, and you're ready to paste your first
        job posting.
      </StepHeader>
      <div className="grid gap-3 sm:grid-cols-3">
        {points.map(({ icon: Icon, title, text }) => (
          <Card key={title} className="p-5">
            <div className="flex size-9 items-center justify-center rounded-xl bg-primary/10">
              <Icon className="size-4 text-primary" />
            </div>
            <div className="mt-4 text-sm font-semibold">{title}</div>
            <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{text}</p>
          </Card>
        ))}
      </div>
      <Button variant="gradient" size="lg" className="mt-8" onClick={onNext}>
        Get started <ArrowRight />
      </Button>
    </div>
  );
}

function ResumeStep({ onNext, onBack }: { onNext: (p: Prefill | null) => void; onBack: () => void }) {
  const { data: system } = useSystem();
  const [replace, setReplace] = useState(false);
  return (
    <div>
      <StepHeader eyebrow="Step 1" title="Upload the resume you already have">
        This defines your official employers, titles, and dates. PDF or Word both work; you'll review what was read before it's saved.
      </StepHeader>
      {system?.inputs.resume && !replace ? (
        <Card className="flex flex-wrap items-center gap-4 p-5">
          <div className="flex size-10 items-center justify-center rounded-xl bg-success/10">
            <Check className="size-5 text-success" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-medium">You already have a base resume</div>
            <div className="truncate text-sm text-muted-foreground">{system.inputs.resume}</div>
          </div>
          <Button variant="outline" onClick={() => setReplace(true)}>
            Replace it
          </Button>
          <Button onClick={() => onNext(null)}>
            Continue <ArrowRight />
          </Button>
        </Card>
      ) : (
        <ResumeFlow confirmLabel="Save and continue" onConfirmed={(p) => onNext(p)} onCancel={system?.inputs.resume ? () => setReplace(false) : undefined} />
      )}
      <Button variant="ghost" className="mt-6" onClick={onBack}>
        <ArrowLeft /> Back
      </Button>
    </div>
  );
}

function ProfileStep({ prefill, onNext, onBack }: { prefill: Prefill | null; onNext: () => void; onBack: () => void }) {
  const { data, isLoading } = useProfile();
  const qc = useQueryClient();
  const [draft, setDraft] = useState<Profile | null>(null);

  useEffect(() => {
    if (!data || draft) return;
    setDraft(data.exists ? data.profile : profileFromPrefill(prefill));
  }, [data, prefill, draft]);

  const save = useMutation({
    mutationFn: (p: Profile) => api.put<ProfilePayload>("/api/profile", cleanProfile(p)),
    onSuccess: (r) => {
      qc.setQueryData(keys.profile, r);
      qc.invalidateQueries({ queryKey: keys.system });
      toast.success("Profile saved");
      onNext();
    },
    onError: (e) => toast.error("Couldn't save", { description: (e as Error).message }),
  });

  return (
    <div>
      <StepHeader eyebrow="Step 2" title="Confirm your profile">
        {data?.exists
          ? "Here's your current profile. Add anything true that isn't on your resume."
          : "We pre-filled what we could from your resume. Add accomplishments, projects, and tools that aren't on it: the tailoring can only use what's here or in your resume."}
      </StepHeader>
      {isLoading || !draft ? <Skeleton className="h-96" /> : <ProfileEditor value={draft} onChange={setDraft} />}
      <div className="mt-6 flex items-center gap-2">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft /> Back
        </Button>
        <Button className="ml-auto" loading={save.isPending} onClick={() => draft && save.mutate(draft)}>
          Save and continue <ArrowRight />
        </Button>
      </div>
    </div>
  );
}

function FactsStep({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const { data: system } = useSystem();
  const { track } = useJobs();
  const draft = useMutation({
    mutationFn: () => api.post<JobSummary>("/api/facts/draft", { force: !!system?.inputs.fact_bank }),
    onSuccess: (job) => {
      track(job, { title: "Drafting your fact bank", open: false, successMessage: "Fact bank ready. Review it under Evidence." });
      toast("Drafting your fact bank in the background", { description: "You can keep going." });
      onNext();
    },
    onError: (e) => toast.error((e as Error).message),
  });
  return (
    <div>
      <StepHeader eyebrow="Step 3 · Optional" title="Add a fact bank for provenance checks">
        Claude splits your profile and resume into atomic facts, each tagged with its employer. From then on, every bullet must cite the
        facts it's built from, and a bullet that borrows another employer's fact is dropped automatically.
      </StepHeader>
      <Card className="p-5">
        <div className="grid gap-3 text-sm sm:grid-cols-3">
          {[
            ["F012", "Northwind Traders", "Built a churn model that cut churn 12% in one year."],
            ["F013", "Northwind Traders", "Led a team of 4 analysts."],
            ["F021", "general", "Python, SQL, and Tableau."],
          ].map(([id, emp, text]) => (
            <div key={id} className="rounded-lg border bg-muted/30 p-3">
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                <span className="font-mono font-medium text-primary">{id}</span>
                {emp}
              </div>
              <p className="mt-1.5 text-[13px] leading-snug">{text}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-muted-foreground">Example facts. You can edit, add, or remove any of them later.</p>
      </Card>
      <div className="mt-6 flex flex-wrap items-center gap-2">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft /> Back
        </Button>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" onClick={onNext}>
            {system?.inputs.fact_bank ? "Keep my current bank" : "Skip for now"}
          </Button>
          <Button variant="gradient" loading={draft.isPending} disabled={system?.onboarding_needed} onClick={() => draft.mutate()}>
            <Sparkles /> {system?.inputs.fact_bank ? "Redraft it" : "Draft it for me"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function DoneStep() {
  const navigate = useNavigate();
  const { data: system } = useSystem();
  const ready = !system?.onboarding_needed;
  return (
    <div className="grid place-items-center py-10 text-center">
      <div className="relative">
        <div className="absolute inset-0 rounded-full bg-primary/25 blur-2xl" />
        <div className="relative flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-lift">
          <PartyPopper className="size-7" />
        </div>
      </div>
      <h1 className="mt-6 text-2xl font-semibold tracking-tight">{ready ? "You're all set" : "Almost there"}</h1>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
        {ready
          ? "Paste a job posting and Resume Studio will tailor your resume to it in a minute or two."
          : "Add your base resume and profile to start generating. You can still create projects in the meantime."}
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-2">
        <Button variant="outline" onClick={() => navigate("/")}>
          Go to projects
        </Button>
        <Button variant="gradient" onClick={() => navigate("/projects/new")}>
          <Plus /> Create your first project
        </Button>
      </div>
    </div>
  );
}
