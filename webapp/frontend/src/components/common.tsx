/** Shared page-level building blocks. */
import { AlertCircle, AlertTriangle, Info, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import type { ProjectStatus, Severity } from "@/lib/types";
import { cn, hueFor, initials } from "@/lib/utils";
import { Badge } from "./ui/primitives";

export function Logo({ className, withText = true }: { className?: string; withText?: boolean }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <img src="/favicon.svg" alt="" className="size-7 rounded-lg shadow-soft" />
      {withText && (
        <div className="leading-none">
          <div className="text-[15px] font-semibold tracking-tight">Resume Studio</div>
          <div className="mt-0.5 text-[10.5px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            Truthful tailoring
          </div>
        </div>
      )}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  eyebrow?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="min-w-0">
        {eyebrow && <div className="mb-1.5 text-xs font-medium text-muted-foreground">{eyebrow}</div>}
        <h1 className="text-balance text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon: LucideIcon;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed bg-card/50 px-6 py-14 text-center",
        className,
      )}
    >
      <div className="relative mb-4">
        <div className="absolute inset-0 rounded-2xl bg-primary/20 blur-xl" />
        <div className="relative flex size-12 items-center justify-center rounded-2xl border bg-background shadow-soft">
          <Icon className="size-5 text-primary" />
        </div>
      </div>
      <h3 className="text-base font-semibold tracking-tight">{title}</h3>
      {description && <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Monogram({ text, className }: { text: string; className?: string }) {
  const hue = hueFor(text || "?");
  return (
    <div
      aria-hidden
      className={cn(
        "flex size-10 shrink-0 items-center justify-center rounded-lg text-sm font-semibold tracking-tight",
        className,
      )}
      style={{
        background: `linear-gradient(135deg, hsl(${hue} 70% 55% / 0.16), hsl(${(hue + 40) % 360} 70% 55% / 0.22))`,
        color: `hsl(${hue} 55% 42%)`,
      }}
    >
      <span className="dark:brightness-[1.6]">{initials(text)}</span>
    </div>
  );
}

export const STATUS_META: Record<ProjectStatus, { label: string; variant: "default" | "secondary" | "success" | "warning" | "destructive" | "outline"; dot: string }> = {
  draft: { label: "Draft", variant: "secondary", dot: "bg-muted-foreground/60" },
  applied: { label: "Applied", variant: "default", dot: "bg-primary" },
  interviewing: { label: "Interviewing", variant: "warning", dot: "bg-warning" },
  offer: { label: "Offer", variant: "success", dot: "bg-success" },
  rejected: { label: "Closed", variant: "outline", dot: "bg-destructive/70" },
  archived: { label: "Archived", variant: "outline", dot: "bg-muted-foreground/40" },
};

export function StatusBadge({ status, className }: { status: ProjectStatus; className?: string }) {
  const meta = STATUS_META[status] ?? STATUS_META.draft;
  return (
    <Badge variant={meta.variant} className={className}>
      <span className={cn("size-1.5 rounded-full", meta.dot)} />
      {meta.label}
    </Badge>
  );
}

const SEVERITY_ICON: Record<Severity, LucideIcon> = { error: AlertCircle, warning: AlertTriangle, info: Info };
const SEVERITY_TONE: Record<Severity, string> = {
  error: "text-destructive",
  warning: "text-warning",
  info: "text-muted-foreground",
};

export function SeverityIcon({ severity, className }: { severity: Severity; className?: string }) {
  const Icon = SEVERITY_ICON[severity];
  return <Icon className={cn("size-3.5 shrink-0", SEVERITY_TONE[severity], className)} />;
}

export function Callout({
  tone = "info",
  title,
  children,
  action,
  className,
}: {
  tone?: "info" | "warning" | "error" | "success";
  title?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  const tones = {
    info: "border-primary/20 bg-primary/[0.05] [&_.callout-icon]:text-primary",
    warning: "border-warning/30 bg-warning/[0.07] [&_.callout-icon]:text-warning",
    error: "border-destructive/30 bg-destructive/[0.06] [&_.callout-icon]:text-destructive",
    success: "border-success/30 bg-success/[0.07] [&_.callout-icon]:text-success",
  } as const;
  const Icon = tone === "error" ? AlertCircle : tone === "warning" ? AlertTriangle : Info;
  return (
    <div className={cn("flex gap-3 rounded-lg border px-4 py-3 text-sm", tones[tone], className)}>
      <Icon className="callout-icon mt-0.5 size-4 shrink-0" />
      <div className="min-w-0 flex-1 leading-relaxed">
        {title && <div className="font-medium">{title}</div>}
        {children && <div className={cn("text-muted-foreground", title && "mt-0.5")}>{children}</div>}
      </div>
      {action && <div className="shrink-0 self-center">{action}</div>}
    </div>
  );
}
