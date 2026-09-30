import { ArrowRight, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { Sequins } from "@/components/shared/brand";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/primitives";

export function SetupCard({ profile, resume }: { profile: boolean; resume: boolean }) {
  const steps = [
    { done: resume, label: "Upload your base resume", to: "/resume" },
    { done: profile, label: "Confirm your profile", to: "/profile" },
  ];
  return (
    <Card className="relative mt-6 overflow-hidden border-primary/25">
      <div className="absolute inset-0 bg-gradient-to-br from-brand-pink/[0.16] via-brand-lilac/[0.08] to-transparent" />
      <div className="bead-rule absolute inset-x-0 top-0 h-[3px]" />
      <Sequins count={3} />
      <div className="relative flex flex-col gap-5 p-6 md:flex-row md:items-center">
        <div className="bg-brand-gradient flex size-12 shrink-0 items-center justify-center rounded-2xl shadow-lift">
          <Sparkles className="size-5" />
        </div>
        <div className="flex-1">
          <h2 className="text-base font-semibold tracking-tight">Set up Resume Taylor in about two minutes</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Your base resume and profile are the only source material the tailoring can draw from.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {steps.map((s) => (
              <Badge key={s.label} variant={s.done ? "success" : "outline"}>
                {s.done ? "Done" : "To do"}: {s.label}
              </Badge>
            ))}
          </div>
        </div>
        <Button asChild>
          <Link to="/welcome">
            Start setup <ArrowRight />
          </Link>
        </Button>
      </div>
    </Card>
  );
}
