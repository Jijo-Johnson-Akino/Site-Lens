import type { RecommendationListItem, RecommendationSummary } from "@/lib/scan/api";
import { issuesHref, statusLabel, titleCase } from "@/lib/scan/recommendations-ui";

export const ACTION_PLAN_INTRO =
  "Prioritized actions generated from the findings detected during this scan.";

export const PRIORITY_GROUP_ORDER = ["critical", "high", "medium", "low", "info"] as const;

export const ACTION_PLAN_SORTS = [
  { id: "priority", label: "Priority" },
  { id: "impact", label: "Impact" },
  { id: "effort", label: "Effort" },
  { id: "affected_pages", label: "Affected pages" },
  { id: "issue_count", label: "Issue count" },
  { id: "status", label: "Status" },
] as const;

export function priorityGroupLabel(priority: string) {
  if (priority === "info") return "Info";
  return `${titleCase(priority)} Priority`;
}

export function groupActionsByPriority(items: RecommendationListItem[]) {
  return PRIORITY_GROUP_ORDER.map((id) => ({
    id,
    label: priorityGroupLabel(id),
    items: items.filter((item) => item.priority === id),
  })).filter((group) => group.items.length > 0);
}

export function bandCounts(summary: RecommendationSummary | null | undefined) {
  return {
    high: (summary?.critical || 0) + (summary?.high || 0),
    medium: summary?.medium || 0,
    low: (summary?.low || 0) + (summary?.info || 0),
  };
}

export function pagesHref(scanId: string, pageIds: string[] | undefined) {
  if (pageIds?.length === 1) {
    return `/scan/${scanId}/pages/${pageIds[0]}`;
  }
  return `/scan/${scanId}/pages`;
}

export function actionIssuesHref(scanId: string, item: RecommendationListItem) {
  return issuesHref(scanId, item.issue_ids || [], item.issue_keys);
}

export function analyzerHref(scanId: string, category: string) {
  const routes: Record<string, string> = {
    SEO: "seo",
    AEO: "aeo",
    "UI/UX": "uiux",
    Accessibility: "accessibility",
    Performance: "performance",
    Content: "content",
    "Structured Data": "structured-data",
    Mobile: "mobile",
    CRO: "cro",
    Trust: "trust",
    Architecture: "architecture",
  };
  const slug = routes[category];
  return slug ? `/scan/${scanId}/${slug}` : `/scan/${scanId}/recommendations`;
}

export function emptyActionPlanCopy(kind: "none" | "filters" | "incomplete") {
  if (kind === "filters") {
    return {
      title: "No actions match your filters.",
      body: "Try a different priority, category, status, or search term.",
    };
  }
  if (kind === "incomplete") {
    return {
      title: "The Action Plan will be available after analysis completes.",
      body: "Actions are generated from stored recommendations after the scan finishes.",
    };
  }
  return {
    title: "No actions were generated from the detected findings.",
    body: "No recommendations were generated from the detected findings.",
  };
}

export function actionStatusLabel(status: string) {
  return statusLabel(status);
}
