export const CRO_METHODOLOGY =
  "SiteLens CRO analysis evaluates observable website elements that may influence conversion friction and action clarity. It does not measure actual conversion rates or guarantee business outcomes.";

export const CRO_CRAWL_NOTE = "Results are based on pages and interactions observable within the SiteLens crawl.";

export const CRO_SCORE_NOTE = "SiteLens CRO score reflects observable conversion-related website signals.";

export const CRO_CATEGORY_LABELS: Record<string, string> = {
  primary_cta: "Primary CTA",
  cta_clarity: "CTA Clarity",
  value_proposition: "Value Proposition",
  forms: "Forms",
  conversion_path: "Conversion Path",
  navigation: "Navigation Friction",
  pricing: "Pricing / Offer",
  contact: "Contact Opportunities",
  mobile: "Mobile Conversion",
  interaction: "Interaction Friction",
};

const FORBIDDEN_CRO_CLAIMS =
  /conversion probability|predicted conversion|expected conversion rate|revenue increase|guaranteed conversion|guaranteed sales|guaranteed lead/i;

export function emptyCroCopy(kind: "loading" | "unavailable" | "incomplete") {
  if (kind === "incomplete") {
    return {
      title: "Running CRO Analysis",
      body: "CRO findings appear after existing analyzers complete.",
    };
  }
  if (kind === "unavailable") {
    return {
      title: "CRO analysis unavailable.",
      body: "Other analyzers remain available. CRO did not complete for this scan.",
    };
  }
  return {
    title: "Loading CRO results",
    body: "Fetching conversion-readiness signals for this scan.",
  };
}

export function checkStatusLabel(status: string | undefined) {
  if (status === "pass") return "Pass";
  if (status === "fail") return "Fail";
  if (status === "warning") return "Warning";
  return "N/A";
}

export function scoreLabel(value: number | null | undefined) {
  if (typeof value !== "number") return "Unavailable";
  return String(value);
}

export function categoryLabel(group: string | undefined) {
  if (!group) return "CRO";
  return CRO_CATEGORY_LABELS[group] || group.replace(/_/g, " ");
}

export function filterFindings<
  T extends {
    status?: string;
    severity?: string;
    name?: string;
    group?: string;
    message?: string;
    page_url?: string;
    recommendation?: string | null;
  },
>(findings: T[], options: { status?: string; severity?: string; query?: string } = {}) {
  const status = options.status || "all";
  const severity = options.severity || "all";
  const needle = (options.query || "").trim().toLowerCase();
  return findings.filter((check) => {
    if (status !== "all" && check.status !== status) return false;
    if (severity !== "all" && check.severity !== severity) return false;
    if (!needle) return true;
    const hay = `${check.name || ""} ${check.group || ""} ${check.message || ""} ${check.page_url || ""} ${check.recommendation || ""}`.toLowerCase();
    return hay.includes(needle);
  });
}

export function conversionPathCopy(
  nodes: Array<{ page_type?: string | null; url: string }> | undefined,
  message?: string | null,
) {
  if (nodes?.length) {
    return nodes.map((node) => node.page_type || node.url).join(" → ");
  }
  return message || "No conversion path could be determined from the crawled links.";
}

export function containsForbiddenCroClaims(text: string) {
  return FORBIDDEN_CRO_CLAIMS.test(text);
}
