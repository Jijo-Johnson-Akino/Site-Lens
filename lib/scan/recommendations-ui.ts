export const RECOMMENDATION_METHODOLOGY =
  "Recommendations are generated from SiteLens's deterministic analysis findings. They are intended as implementation guidance and do not guarantee specific search rankings, traffic, conversions, or other business outcomes.";

export const RECOMMENDATION_CATEGORIES = [
  "All",
  "SEO",
  "AEO",
  "UI/UX",
  "Accessibility",
  "Performance",
  "Content",
  "Structured Data",
  "Mobile",
  "CRO",
  "Trust",
  "Architecture",
] as const;

export function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function statusLabel(value: string) {
  if (value === "in_progress") return "In Progress";
  return titleCase(value);
}

export function emptyRecommendationsCopy(kind: "none" | "filters" | "incomplete" | "partial") {
  if (kind === "filters") {
    return {
      title: "No recommendations match your filters.",
      body: "Try a different category, priority, or search term.",
    };
  }
  if (kind === "incomplete") {
    return {
      title: "Recommendations will be available after analysis and issue aggregation complete.",
      body: "Recommendations are generated from detected issues after analysis is complete.",
    };
  }
  if (kind === "partial") {
    return {
      title: "Some analyzers did not complete.",
      body: "Recommendations are generated only from analyzers that produced findings. Failed analyzers are not assumed to have zero issues.",
    };
  }
  return {
    title: "No recommendations generated.",
    body: "Recommendations are generated from detected issues after analysis is complete.",
  };
}

export function issuesHref(scanId: string, issueIds: string[], issueKeys: string[]) {
  const params = new URLSearchParams();
  if (issueIds.length) {
    params.set("issue_ids", issueIds.slice(0, 100).join(","));
  } else if (issueKeys[0]) {
    params.set("issue_key", issueKeys[0]);
  }
  const query = params.toString();
  return query ? `/scan/${scanId}/issues?${query}` : `/scan/${scanId}/issues`;
}
