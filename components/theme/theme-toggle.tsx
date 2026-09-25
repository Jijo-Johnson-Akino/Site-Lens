"use client";

import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/components/theme/theme-provider";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, cycleTheme } = useTheme();
  const isDark = theme === "dark";
  const label = isDark ? "Dark theme" : "Light theme";
  const nextLabel = isDark ? "Light theme" : "Dark theme";
  const Icon = isDark ? Moon : Sun;

  return (
    <button
      type="button"
      onClick={cycleTheme}
      className={cn(
        "inline-flex size-10 shrink-0 items-center justify-center rounded-[10px] border border-border bg-card text-foreground transition-colors",
        "hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        className,
      )}
      aria-label={`${label}. Switch to ${nextLabel}.`}
      title={`${label} · click for ${nextLabel}`}
    >
      <Icon className="size-4" aria-hidden />
    </button>
  );
}
