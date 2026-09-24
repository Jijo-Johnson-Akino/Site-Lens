"use client";

import { Monitor, Moon, Sun } from "lucide-react";

import { useTheme } from "@/components/theme/theme-provider";
import { cn } from "@/lib/utils";

const ICONS = {
  system: Monitor,
  light: Sun,
  dark: Moon,
} as const;

const LABELS = {
  system: "System theme",
  light: "Light theme",
  dark: "Dark theme",
} as const;

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, cycleTheme } = useTheme();
  const Icon = ICONS[theme];
  const next = theme === "system" ? "light" : theme === "light" ? "dark" : "system";

  return (
    <button
      type="button"
      onClick={cycleTheme}
      className={cn(
        "inline-flex size-10 shrink-0 items-center justify-center rounded-[10px] border border-border bg-card text-foreground transition-colors",
        "hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        className,
      )}
      aria-label={`${LABELS[theme]}. Switch to ${LABELS[next]}.`}
      title={`${LABELS[theme]} · click for ${LABELS[next]}`}
    >
      <Icon className="size-4" aria-hidden />
    </button>
  );
}
