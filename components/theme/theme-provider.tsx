"use client";

import { createContext, useContext, useMemo, useSyncExternalStore, type ReactNode } from "react";

import {
  nextTheme,
  persistTheme,
  readStoredTheme,
  resolveTheme,
  subscribeTheme,
  type ResolvedTheme,
  type ThemePreference,
} from "@/lib/theme";

type ThemeContextValue = {
  theme: ThemePreference;
  resolved: ResolvedTheme;
  setTheme: (theme: ThemePreference) => void;
  cycleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getThemeSnapshot() {
  return readStoredTheme();
}

function getResolvedSnapshot() {
  return resolveTheme(readStoredTheme());
}

function getServerThemeSnapshot(): ThemePreference {
  return "system";
}

function getServerResolvedSnapshot(): ResolvedTheme {
  return "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useSyncExternalStore(subscribeTheme, getThemeSnapshot, getServerThemeSnapshot);
  const resolved = useSyncExternalStore(subscribeTheme, getResolvedSnapshot, getServerResolvedSnapshot);

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      resolved,
      setTheme: persistTheme,
      cycleTheme: () => persistTheme(nextTheme(theme)),
    }),
    [theme, resolved],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
