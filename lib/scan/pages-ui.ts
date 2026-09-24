export function pageTitle(title: string | null | undefined): string {
  const text = (title || "").trim();
  return text || "Untitled page";
}

export function crawlStatusLabel(status: string | null | undefined): string {
  if (status === "crawled") return "Crawled";
  if (status === "failed") return "Failed";
  if (status === "skipped") return "Skipped";
  if (status === "crawling") return "Crawling";
  if (status === "queued") return "Queued";
  if (status === "discovered") return "Discovered";
  return "Unknown";
}

export function indexableLabel(value: boolean | null | undefined): string {
  if (value === true) return "Indexable";
  if (value === false) return "Noindex";
  return "Unknown";
}

export function httpLabel(code: number | null | undefined): string {
  return typeof code === "number" ? String(code) : "—";
}

export function scoreLabel(value: number | null | undefined): string {
  return typeof value === "number" ? String(value) : "Not analyzed";
}

export function formatBytes(value: number | null | undefined): string {
  if (typeof value !== "number") {
    return "—";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${Math.round((value / 1024) * 10) / 10} KB`;
  }
  return `${Math.round((value / (1024 * 1024)) * 10) / 10} MB`;
}
