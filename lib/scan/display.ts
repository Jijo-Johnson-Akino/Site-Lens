export function hostnameOf(url: string | null | undefined): string | null {
  if (!url) {
    return null;
  }
  try {
    return new URL(url).hostname.replace(/^www\./i, "");
  } catch {
    return url;
  }
}

export function formatScanDate(iso: string | null | undefined): string {
  if (!iso) {
    return "Unavailable";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "Unavailable";
  }
  return new Intl.DateTimeFormat("en-US", { dateStyle: "long", timeStyle: "short" }).format(date);
}

export function scanStatusLabel(status: string | undefined): string {
  if (status === "queued") return "Queued";
  if (status === "running") return "Running";
  if (status === "completed") return "Scan completed";
  if (status === "failed") return "Scan failed";
  if (status === "cancelled") return "Cancelled";
  return "Scan status unavailable";
}
