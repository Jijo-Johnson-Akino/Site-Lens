export const THEME_STORAGE_KEY = "sitebench-theme";
export const THEME_CHANGE_EVENT = "sitebench-theme-change";

export type ThemePreference = "light" | "dark";
export type ResolvedTheme = "light" | "dark";

export const THEME_OPTIONS: ThemePreference[] = ["light", "dark"];

export function isThemePreference(value: string | null | undefined): value is ThemePreference {
  return value === "light" || value === "dark";
}

/** Older builds stored "system"; that now means explicit light. */
export function normalizeTheme(value: string | null | undefined): ThemePreference {
  return value === "dark" ? "dark" : "light";
}

export function readStoredTheme(): ThemePreference {
  if (typeof window === "undefined") return "light";
  try {
    return normalizeTheme(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return "light";
  }
}

export function resolveTheme(preference: ThemePreference): ResolvedTheme {
  return preference;
}

export function applyTheme(preference: ThemePreference) {
  if (typeof document === "undefined") return;
  const resolved = resolveTheme(preference);
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
  root.dataset.theme = preference;
}

export function persistTheme(preference: ThemePreference) {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    /* ignore quota / private mode */
  }
  applyTheme(preference);
  window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
}

export function subscribeTheme(onStoreChange: () => void) {
  const onChange = () => {
    applyTheme(readStoredTheme());
    onStoreChange();
  };
  window.addEventListener(THEME_CHANGE_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(THEME_CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

export function nextTheme(current: ThemePreference): ThemePreference {
  return current === "dark" ? "light" : "dark";
}
