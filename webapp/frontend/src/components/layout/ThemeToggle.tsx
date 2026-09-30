import { Laptop, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
  Tooltip,
} from "@/components/ui/overlays";
import { useTheme, type ThemePreference } from "@/lib/theme";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, resolved, setTheme } = useTheme();
  return (
    <DropdownMenu>
      <Tooltip content="Theme">
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon-sm" className={cn("relative", className)} aria-label="Change theme">
            <Sun className={cn("transition-all", resolved === "dark" ? "-rotate-90 scale-0" : "rotate-0 scale-100")} />
            <Moon
              className={cn(
                "absolute transition-all",
                resolved === "dark" ? "rotate-0 scale-100" : "rotate-90 scale-0",
              )}
            />
          </Button>
        </DropdownMenuTrigger>
      </Tooltip>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Appearance</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={theme} onValueChange={(v) => setTheme(v as ThemePreference)}>
          <DropdownMenuRadioItem value="light">
            <Sun /> Day
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="dark">
            <Moon /> Night
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="system">
            <Laptop /> Match system
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** A segmented Day / Night / System control for the Settings page. */
export function ThemeSegmented() {
  const { theme, setTheme } = useTheme();
  const options: { value: ThemePreference; label: string; icon: typeof Sun }[] = [
    { value: "light", label: "Day", icon: Sun },
    { value: "dark", label: "Night", icon: Moon },
    { value: "system", label: "System", icon: Laptop },
  ];
  return (
    <div role="radiogroup" aria-label="Theme" className="inline-grid grid-cols-3 gap-1 rounded-lg bg-secondary p-1">
      {options.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={theme === value}
          onClick={() => setTheme(value)}
          className={cn(
            "flex items-center justify-center gap-1.5 rounded-md px-3.5 py-1.5 text-[13px] font-medium text-muted-foreground transition-all hover:text-foreground",
            theme === value && "bg-background text-foreground shadow-soft",
          )}
        >
          <Icon className="size-3.5" />
          {label}
        </button>
      ))}
    </div>
  );
}
