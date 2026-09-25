export const THEME_STORAGE_KEY = "sitebench-theme";
export const THEME_CHANGE_EVENT = "sitebench-theme-change";

export type ThemePreference = "system" | "dark";
export type ResolvedTheme = "light" | "dark";

export const THEME_OPTIONS: ThemePreference[] = ["system", "dark"];

export function isThemePreference(value: string | null | undefined): value is ThemePreference {
  return value === "dark" || value === "system";
}

/** Light in storage/UI means follow the OS. Dark is always dark. */
export function normalizeTheme(value: string | null | undefined): ThemePreference {
  if (value === "dark") return "dark";
  return "system";
}

export function readStoredTheme(): ThemePreference {
  if (typeof window === "undefined") return "system";
  try {
    return normalizeTheme(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return "system";
  }
}

export function systemPrefersDark() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolveTheme(preference: ThemePreference): ResolvedTheme {
  if (preference === "dark") return "dark";
  return systemPrefersDark() ? "dark" : "light";
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
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  window.addEventListener(THEME_CHANGE_EVENT, onChange);
  window.addEventListener("storage", onChange);
  media.addEventListener("change", onChange);
  return () => {
    window.removeEventListener(THEME_CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onChange);
    media.removeEventListener("change", onChange);
  };
}

export function nextTheme(current: ThemePreference): ThemePreference {
  return current === "dark" ? "system" : "dark";
}
