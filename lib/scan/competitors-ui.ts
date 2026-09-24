export const COMPETITOR_METHODOLOGY =
  "Competitor benchmarking compares websites using SiteLens's observable analysis. Each website is independently crawled and analyzed using the configured SiteLens limits and environment.";

export const COMPETITOR_LIMITATIONS =
  "Results represent measurements from the SiteLens scan and should not be interpreted as search rankings, traffic estimates, conversion rates, or business-performance predictions.";

export function competitorStatusLabel(value: string | null | undefined) {
  if (value === "scanning" || value === "running") return "Scanning";
  if (value === "queued") return "Queued";
  if (value === "completed") return "Completed";
  if (value === "failed") return "Failed";
  if (value === "cancelled") return "Cancelled";
  return "Unknown";
}

export function emptyCompetitorsCopy(kind: "none" | "incomplete" | "unavailable") {
  if (kind === "incomplete") {
    return {
      title: "Comparison will update when the competitor scan completes.",
      body: "Competitor websites are scanned independently using the same SiteLens analyzers.",
    };
  }
  if (kind === "unavailable") {
    return {
      title: "Competitors are not available yet.",
      body: "Add competitors after the primary scan completes.",
    };
  }
  return {
    title: "No competitor websites have been added to this scan.",
    body: "Add up to 5 public websites to compare measurable SiteLens findings.",
  };
}

export function displayCell(available: boolean | undefined, value: unknown, fallback = "Unavailable") {
  if (!available || value == null || value === "") {
    return fallback;
  }
  return String(value);
}

export function formatTimestamp(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function barWidth(value: number | null | undefined, max: number) {
  if (typeof value !== "number" || max <= 0) return 0;
  return Math.max(4, Math.round((Math.abs(value) / max) * 100));
}
