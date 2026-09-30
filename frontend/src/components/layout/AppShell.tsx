import { AnimatePresence, motion } from "framer-motion";
import {
  Briefcase,
  FileText,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  UserRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Logo } from "@/components/shared/common";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/overlays";
import { Kbd } from "@/components/ui/primitives";
import { useProjects, useSystem } from "@/lib/api/queries";
import { cn, isMac } from "@/lib/utils";
import { CommandMenu } from "./CommandMenu";
import { HealthBanner } from "./HealthBanner";
import { ThemeToggle } from "./ThemeToggle";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  badge?: ReactNode;
}

const COLLAPSE_KEY = "taylor-sidebar-collapsed";

function useCollapsed(): [boolean, (v: boolean) => void] {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === "1";
    } catch {
      return false;
    }
  });
  const set = (v: boolean) => {
    setCollapsed(v);
    try {
      localStorage.setItem(COLLAPSE_KEY, v ? "1" : "0");
    } catch {
      /* ignore */
    }
  };
  return [collapsed, set];
}

function SidebarNav({ items, collapsed, onNavigate }: { items: NavItem[]; collapsed: boolean; onNavigate?: () => void }) {
  return (
    <nav className="grid gap-0.5" aria-label="Main">
      {items.map(({ to, label, icon: Icon, end, badge }) => (
        <Tooltip key={to} content={collapsed ? label : null} side="right">
          <NavLink
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "group relative flex h-9 items-center gap-3 rounded-md px-2.5 text-[13.5px] font-medium text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent hover:text-foreground",
                isActive && "bg-sidebar-accent text-foreground",
                collapsed && "justify-center px-0",
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.span
                    layoutId="nav-active"
                    className="absolute inset-y-1.5 left-0 w-[3px] rounded-full bg-primary"
                    transition={{ type: "spring", stiffness: 500, damping: 38 }}
                  />
                )}
                <Icon className={cn("size-[17px] shrink-0", isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
                {!collapsed && <span className="flex-1 truncate">{label}</span>}
                {!collapsed && badge}
              </>
            )}
          </NavLink>
        </Tooltip>
      ))}
    </nav>
  );
}

function SystemFooter({ collapsed }: { collapsed: boolean }) {
  const { data } = useSystem();
  const ok = data?.claude.found;
  const status = !data ? "Checking..." : ok ? "Claude CLI ready" : "Claude CLI missing";
  return (
    <Tooltip content={collapsed ? status : data?.claude.version ?? null} side="right">
      <div className={cn("flex items-center gap-2 px-2.5 py-1.5 text-xs text-muted-foreground", collapsed && "justify-center px-0")}>
        <span className="relative flex size-2">
          {ok && <span className="absolute inset-0 animate-ping rounded-full bg-success/50" />}
          <span className={cn("relative size-2 rounded-full", !data ? "bg-muted-foreground/40" : ok ? "bg-success" : "bg-destructive")} />
        </span>
        {!collapsed && <span className="truncate">{status}</span>}
      </div>
    </Tooltip>
  );
}

export function AppShell() {
  const [collapsed, setCollapsed] = useCollapsed();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const location = useLocation();
  const { data: projects } = useProjects();
  const { data: system } = useSystem();
  const running = projects?.filter((p) => p.active_job).length ?? 0;

  useEffect(() => setMobileOpen(false), [location.pathname]);

  const items: NavItem[] = [
    {
      to: "/",
      label: "Projects",
      icon: Briefcase,
      end: true,
      badge: projects?.length ? (
        <span className="rounded-full bg-secondary px-1.5 text-[11px] tabular-nums text-muted-foreground">{projects.length}</span>
      ) : undefined,
    },
    { to: "/profile", label: "Profile", icon: UserRound, badge: system && !system.inputs.profile ? <Dot /> : undefined },
    { to: "/resume", label: "Base resume", icon: FileText, badge: system && !system.inputs.resume ? <Dot /> : undefined },
    { to: "/evidence", label: "Evidence", icon: ShieldCheck },
    { to: "/settings", label: "Settings", icon: Settings },
  ];

  const sidebar = (mobile: boolean) => (
    <div className="relative flex h-full flex-col gap-4 p-3">
      <div className="bead-rule absolute inset-x-0 top-0 h-[3px] opacity-90" aria-hidden />
      <div className={cn("flex h-10 items-center justify-between px-1", collapsed && !mobile && "justify-center px-0")}>
        <Link to="/" aria-label="Resume Taylor home">
          <Logo withText={mobile || !collapsed} />
        </Link>
        {mobile && (
          <Button variant="ghost" size="icon-sm" onClick={() => setMobileOpen(false)} aria-label="Close menu">
            <X />
          </Button>
        )}
      </div>
      <Button
        asChild
        variant="gradient"
        className={cn("w-full", collapsed && !mobile && "size-9 self-center p-0")}
        aria-label="New project"
      >
        <Link to="/projects/new">
          <Plus />
          {(mobile || !collapsed) && "New project"}
        </Link>
      </Button>
      <SidebarNav items={items} collapsed={collapsed && !mobile} onNavigate={() => setMobileOpen(false)} />
      <div className="mt-auto grid gap-1">
        {running > 0 && (!collapsed || mobile) && (
          <div className="rounded-lg border bg-background/60 px-3 py-2 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">{running}</span> generation{running > 1 ? "s" : ""} running
          </div>
        )}
        <SystemFooter collapsed={collapsed && !mobile} />
        {!mobile && (
          <Button
            variant="ghost"
            size="sm"
            className={cn("justify-start gap-2 text-muted-foreground", collapsed && "justify-center")}
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
            {!collapsed && "Collapse"}
          </Button>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen">
      <aside
        className={cn(
          "sticky top-0 hidden h-screen shrink-0 border-r border-sidebar-border bg-sidebar transition-[width] duration-200 lg:block",
          collapsed ? "w-[68px]" : "w-60",
        )}
      >
        {sidebar(false)}
      </aside>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-black/40 lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              className="fixed inset-y-0 left-0 z-50 w-72 border-r bg-sidebar shadow-lift lg:hidden"
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              transition={{ type: "spring", stiffness: 420, damping: 40 }}
            >
              {sidebar(true)}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b bg-background/80 px-4 backdrop-blur-md supports-[backdrop-filter]:bg-background/65 sm:px-6">
          <Button variant="ghost" size="icon-sm" className="lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <Menu />
          </Button>
          <Link to="/" className="lg:hidden">
            <Logo withText={false} />
          </Link>
          <button
            type="button"
            onClick={() => setCmdOpen(true)}
            className="ml-auto flex h-8 w-full max-w-xs items-center gap-2 rounded-md border bg-secondary/50 px-3 text-sm text-muted-foreground transition-colors hover:bg-secondary sm:ml-0 lg:max-w-sm"
          >
            <Search className="size-3.5" />
            <span className="flex-1 truncate text-left">Search projects and actions</span>
            <Kbd className="hidden sm:inline-flex">{isMac ? "⌘" : "Ctrl"} K</Kbd>
          </button>
          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
          </div>
        </header>
        <HealthBanner />
        <main className="flex-1">
          <div key={location.pathname.split("/").slice(0, 3).join("/")} className="page-enter">
            <Outlet />
          </div>
        </main>
      </div>
      <CommandMenu open={cmdOpen} onOpenChange={setCmdOpen} />
    </div>
  );
}

function Dot() {
  return <span className="size-2 rounded-full bg-warning" aria-label="Needs attention" />;
}
