import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Briefcase, FileUp, Laptop, Moon, Plus, Settings, ShieldCheck, Sun, UserRound } from "lucide-react";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { StatusBadge } from "@/components/shared/common";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from "@/components/ui/command";
import { useProjects } from "@/lib/api/queries";
import { useTheme } from "@/lib/theme";

export function CommandMenu({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const navigate = useNavigate();
  const { setTheme } = useTheme();
  const { data: projects } = useProjects();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  const run = (fn: () => void) => {
    onOpenChange(false);
    fn();
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0 dark:bg-black/60" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed left-1/2 top-[18vh] z-50 w-[calc(100vw-2rem)] max-w-xl -translate-x-1/2 overflow-hidden rounded-xl border shadow-lift data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-[0.98]"
        >
          <DialogPrimitive.Title className="sr-only">Command menu</DialogPrimitive.Title>
          <Command loop>
            <CommandInput placeholder="Jump to a project or run an action..." />
            <CommandList>
              <CommandEmpty>No matches.</CommandEmpty>
              <CommandGroup heading="Actions">
                <CommandItem onSelect={() => run(() => navigate("/projects/new"))}>
                  <Plus /> New project from a job posting
                </CommandItem>
                <CommandItem onSelect={() => run(() => navigate("/profile"))}>
                  <UserRound /> Edit profile
                </CommandItem>
                <CommandItem onSelect={() => run(() => navigate("/resume"))}>
                  <FileUp /> Upload or replace base resume
                </CommandItem>
                <CommandItem onSelect={() => run(() => navigate("/evidence"))}>
                  <ShieldCheck /> Fact bank and never-claim list
                </CommandItem>
                <CommandItem onSelect={() => run(() => navigate("/settings"))}>
                  <Settings /> Settings
                </CommandItem>
              </CommandGroup>
              <CommandSeparator />
              <CommandGroup heading="Theme">
                <CommandItem onSelect={() => run(() => setTheme("light"))}>
                  <Sun /> Day mode
                </CommandItem>
                <CommandItem onSelect={() => run(() => setTheme("dark"))}>
                  <Moon /> Night mode
                </CommandItem>
                <CommandItem onSelect={() => run(() => setTheme("system"))}>
                  <Laptop /> Match system
                </CommandItem>
              </CommandGroup>
              {!!projects?.length && (
                <>
                  <CommandSeparator />
                  <CommandGroup heading="Projects">
                    {projects.map((p) => (
                      <CommandItem
                        key={p.id}
                        value={`${p.name} ${p.company} ${p.role} ${p.id}`}
                        onSelect={() => run(() => navigate(`/projects/${p.id}`))}
                      >
                        <Briefcase />
                        <span className="min-w-0 flex-1 truncate">{p.name}</span>
                        <StatusBadge status={p.status} />
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </>
              )}
            </CommandList>
          </Command>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
