import type { ScanReportResponse } from "./api";

export const REPORT_VERSION_LABEL = "1.0";

export const REPORT_SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "score-breakdown", label: "Score Breakdown" },
  { id: "issues", label: "Issues" },
  { id: "recommendations", label: "Recommendations" },
  { id: "pages", label: "Pages" },
  { id: "architecture", label: "Architecture" },
  { id: "seo", label: "SEO" },
  { id: "aeo", label: "AEO" },
  { id: "uiux", label: "UI/UX" },
  { id: "accessibility", label: "Accessibility" },
  { id: "performance", label: "Performance" },
  { id: "content", label: "Content" },
  { id: "structured-data", label: "Structured Data" },
  { id: "mobile", label: "Mobile" },
  { id: "cro", label: "CRO" },
  { id: "trust", label: "Trust" },
  { id: "competitors", label: "Competitors" },
  { id: "methodology", label: "Methodology" },
] as const;

const FORBIDDEN_REPORT_CLAIMS =
  /google ranking|chatgpt ranking|gemini will recommend|eligible for google rich results|wcag compliant|ada compliant|fully accessible|this company is trustworthy|the business is legitimate|the website is safe|predicted traffic|revenue increase|conversion probability|increase conversions by/i;

export function emptyReportCopy(kind: "loading" | "unavailable" | "incomplete" | "error") {
  if (kind === "incomplete") {
    return {
      title: "Report not ready",
      body: "The website analysis report appears after the scan completes.",
    };
  }
  if (kind === "unavailable" || kind === "error") {
    return {
      title: "Unable to load report",
      body: "SiteLens could not assemble the report from the available scan results.",
    };
  }
  return {
    title: "Loading report",
    body: "Assembling the website analysis report from stored scan results.",
  };
}

export function reportStatusLabel(status: string | undefined) {
  if (status === "ready") return "Ready";
  if (status === "partial") return "Partial";
  return "Unavailable";
}

export function formatReportDate(iso: string | null | undefined) {
  if (!iso) return "Unavailable";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Unavailable";
  return new Intl.DateTimeFormat("en-US", { dateStyle: "long", timeStyle: "short" }).format(date);
}

export function displayScore(score: number | null | undefined) {
  return typeof score === "number" ? String(score) : "Unavailable";
}

export function displayScoreOutOf100(score: number | null | undefined) {
  return typeof score === "number" ? `${score} / 100` : "Unavailable";
}

export function displayCount(value: number | null | undefined) {
  return typeof value === "number" ? String(value) : "Unavailable";
}

export function displayPercent(value: number | null | undefined) {
  return typeof value === "number" ? `${Math.round(value)}%` : "Unavailable";
}

export function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function metricOrUnavailable(value: number | string | null | undefined, unit?: string) {
  if (value == null || value === "") return "Unavailable";
  if (typeof value === "number" && Number.isNaN(value)) return "Unavailable";
  return unit ? `${value} ${unit}` : String(value);
}

export function containsForbiddenReportClaims(text: string) {
  return FORBIDDEN_REPORT_CLAIMS.test(text);
}

export function formatBytes(value: number | null | undefined) {
  if (typeof value !== "number") return "Unavailable";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function truncateText(value: string | null | undefined, max = 120) {
  const text = (value ?? "").replace(/\s+/g, " ").trim();
  if (!text) return "";
  if (text.length <= max) return text;
  return `${text.slice(0, Math.max(0, max - 1)).trimEnd()}…`;
}

export type NamedCount = {
  id: string;
  label: string;
  count: number;
  color: string;
};

export type ScoreHistoryPoint = {
  analyzed_at: string;
  score: number;
};

export const PAGE_DISTRIBUTION_META: Array<{ id: "healthy" | "have_issues" | "broken" | "redirects" | "blocked"; label: string; color: string }> = [
  { id: "healthy", label: "Healthy", color: "#10B981" },
  { id: "have_issues", label: "Have issues", color: "#D97706" },
  { id: "broken", label: "Broken", color: "#DC2626" },
  { id: "redirects", label: "Redirects", color: "#64748B" },
  { id: "blocked", label: "Blocked", color: "#94A3B8" },
];

export const SEVERITY_SLICE_META: Array<{ id: string; label: string; color: string }> = [
  { id: "critical", label: "Critical", color: "#EF4444" },
  { id: "high", label: "High", color: "#EA580C" },
  { id: "medium", label: "Medium", color: "#EAB308" },
  { id: "low", label: "Low", color: "#3B82F6" },
];

const SEVERITY_RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

export function headerStatusLabel(scanStatus: string | undefined, reportStatus: string | undefined) {
  if (scanStatus === "failed") return "Failed";
  if (scanStatus === "cancelled") return "Cancelled";
  if (scanStatus === "running" || scanStatus === "queued") return "In progress";
  if (reportStatus === "partial") return "Completed · Partial";
  if (scanStatus === "completed" || reportStatus === "ready") return "Completed";
  return titleCase(scanStatus || reportStatus || "Unavailable");
}

export function analyzedViewport(report: ScanReportResponse) {
  const labeled = report.scan.viewport?.trim();
  if (labeled) return labeled;
  const env = report.performance.environment as { viewport_name?: string } | null | undefined;
  if (typeof env?.viewport_name === "string" && env.viewport_name.trim()) {
    return titleCase(env.viewport_name);
  }
  return null;
}

export function previewScreenshot(screenshots: ScanReportResponse["screenshots"]) {
  if (!screenshots.available || screenshots.items.length === 0) return null;
  const desktop = screenshots.items.find((item) => /desktop/i.test(item.viewport));
  return desktop ?? screenshots.items[0];
}

export function crawledPageSlices(report: ScanReportResponse): NamedCount[] {
  if (!report.pages.available) return [];
  const dist = report.pages.distribution;
  if (dist) {
    return PAGE_DISTRIBUTION_META.map((item) => ({
      id: item.id,
      label: item.label,
      color: item.color,
      count: typeof dist[item.id] === "number" ? dist[item.id]! : 0,
    }));
  }
  const healthy = report.pages.pages_without_issues;
  const issues = report.pages.pages_with_issues;
  const broken = report.pages.summary?.failed;
  const slices: NamedCount[] = [];
  if (typeof healthy === "number") slices.push({ id: "healthy", label: "Healthy", color: "#10B981", count: healthy });
  if (typeof issues === "number") slices.push({ id: "have_issues", label: "Have issues", color: "#D97706", count: issues });
  if (typeof broken === "number") slices.push({ id: "broken", label: "Broken", color: "#DC2626", count: broken });
  return slices;
}

export function severitySlices(bySeverity: Record<string, number> | undefined): NamedCount[] {
  const slices = SEVERITY_SLICE_META.map((item) => ({
    ...item,
    count: typeof bySeverity?.[item.id] === "number" ? bySeverity[item.id] : 0,
  }));
  const info = bySeverity?.info;
  if (typeof info === "number" && info > 0) {
    slices.push({ id: "info", label: "Info", count: info, color: "#64748B" });
  }
  return slices;
}

export function recommendationCategoryRows(byCategory: Record<string, number> | undefined) {
  return Object.entries(byCategory ?? {})
    .filter(([, count]) => typeof count === "number" && count > 0)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([label, count]) => ({ id: label, label, count }));
}

export function availableCategoryBars(categories: ScanReportResponse["categories"]) {
  return categories
    .filter((row) => row.available && typeof row.score === "number")
    .map((row) => ({
      id: row.category,
      label: compactCategoryLabel(row.name || row.category),
      score: row.score as number,
      href: row.href,
    }));
}

export function compactCategoryLabel(name: string) {
  if (name === "AEO / AI Search Readiness") return "AEO";
  if (name === "Trust & Credibility") return "Trust";
  return name;
}

export function scoreHistoryFromReport(report: ScanReportResponse): ScoreHistoryPoint[] {
  void report;
  return [];
}

export function previousScanDelta(report: ScanReportResponse): number | null {
  void report;
  return null;
}

export function percentOf(count: number, total: number) {
  if (total <= 0) return 0;
  return (count / total) * 100;
}

export function formatPercent(count: number, total: number) {
  if (total <= 0) return "0%";
  const value = (count / total) * 100;
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? `${rounded}%` : `${rounded.toFixed(1)}%`;
}

export function topIssues(report: ScanReportResponse, limit = 5) {
  const items = [...report.issues.priority_issues];
  items.sort((a, b) => {
    const severity = (SEVERITY_RANK[a.severity] ?? 9) - (SEVERITY_RANK[b.severity] ?? 9);
    if (severity !== 0) return severity;
    const priority = (SEVERITY_RANK[a.priority] ?? 9) - (SEVERITY_RANK[b.priority] ?? 9);
    if (priority !== 0) return priority;
    return (b.affected_page_count ?? 0) - (a.affected_page_count ?? 0);
  });
  return items.slice(0, limit);
}

export function severitySummary(slices: NamedCount[]) {
  const total = slices.reduce((sum, slice) => sum + slice.count, 0);
  const parts = slices.filter((slice) => slice.count > 0).map((slice) => `${slice.count} ${slice.label.toLowerCase()}`);
  return `${total} total issues: ${parts.join(", ") || "none"}.`;
}

export function distributionSummary(slices: NamedCount[]) {
  const total = slices.reduce((sum, slice) => sum + slice.count, 0);
  const parts = slices.map((slice) => `${slice.label} ${slice.count} (${formatPercent(slice.count, total)})`);
  return `Crawled page distribution: ${parts.join(", ")}.`;
}

export function categoryChartSummary(bars: Array<{ label: string; score: number }>) {
  if (bars.length === 0) return "No category scores are available for this scan.";
  return `Score by category: ${bars.map((bar) => `${bar.label} ${bar.score}`).join(", ")}.`;
}

const REDIRECT_REASONS = new Set(["Redirect left the scanned website.", "Too many redirects."]);
const BLOCKED_REASONS = new Set(["Disallowed destination."]);

export type ClassifiablePage = {
  crawl_status?: string;
  http_status?: number | null;
  issue_count?: number;
  skip_reason?: string | null;
  failure_reason?: string | null;
};

export function classifyPageItem(page: ClassifiablePage): "healthy" | "have_issues" | "broken" | "redirects" | "blocked" | null {
  const reason = page.skip_reason || page.failure_reason || "";
  const status = page.crawl_status;
  const http = page.http_status;
  if (REDIRECT_REASONS.has(reason)) return "redirects";
  if (BLOCKED_REASONS.has(reason)) return "blocked";
  if (status === "failed") return "broken";
  if (status === "skipped") return null;
  if (status !== "crawled") return null;
  if (typeof http === "number" && http >= 300 && http < 400) return "redirects";
  if (typeof http === "number" && http >= 400) return "broken";
  if ((page.issue_count ?? 0) > 0) return "have_issues";
  return "healthy";
}

export function pageDistributionFromItems(items: ClassifiablePage[]) {
  const buckets = { healthy: 0, have_issues: 0, broken: 0, redirects: 0, blocked: 0 };
  for (const page of items) {
    const key = classifyPageItem(page);
    if (key) buckets[key] += 1;
  }
  return buckets;
}
