export const TRUST_METHODOLOGY =
  "Trust & Credibility analysis identifies observable signals presented by the website. It does not verify the truth, authenticity, legitimacy, legal compliance, or security of those claims.";

export const TRUST_CRAWL_NOTE =
  "Absence of a detected signal does not prove that the underlying information does not exist outside the SiteLens crawl scope.";

export const TRUST_SCORE_NOTE =
  "Trust Signals Score measures coverage of observable trust and credibility signals. It is not a legitimacy, fraud, safety, or legal-compliance score.";

export const TRUST_CATEGORY_LABELS: Record<string, string> = {
  identity: "Identity",
  contact: "Contactability",
  transparency: "Transparency",
  policies: "Policies",
  authorship: "Authorship",
  social_proof: "Social Proof",
  credentials: "Credentials",
  business: "Business Information",
  security: "Security Signals",
  consistency: "Entity Consistency",
};

const FORBIDDEN_TRUST_CLAIMS =
  /this company is trustworthy|this company is legitimate|this company is safe|this company is fraudulent|company trustworthiness|legitimacy score|fraud score|gdpr compliant|ccpa compliant|legally compliant|website is secure|website is safe|ssl certified/i;

export function emptyTrustCopy(kind: "loading" | "unavailable" | "incomplete") {
  if (kind === "incomplete") {
    return {
      title: "Running Trust & Credibility analysis",
      body: "Trust findings appear after existing analyzers complete.",
    };
  }
  if (kind === "unavailable") {
    return {
      title: "Trust & Credibility analysis unavailable.",
      body: "Other analyzers remain available. Trust analysis did not complete for this scan.",
    };
  }
  return {
    title: "Loading Trust & Credibility results",
    body: "Fetching observable trust and credibility signals for this scan.",
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
  if (!group) return "Trust";
  return TRUST_CATEGORY_LABELS[group] || group.replace(/_/g, " ");
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

export function authorSummary(authors: Array<{ author?: string | null; publication_date?: string | null }> | undefined) {
  const rows = authors || [];
  const withAuthor = rows.filter((row) => Boolean(row.author)).length;
  const withDate = rows.filter((row) => Boolean(row.publication_date)).length;
  if (!rows.length) {
    return "No article pages were available to inspect.";
  }
  return `${rows.length} article${rows.length === 1 ? "" : "s"} analyzed. ${withAuthor} include author information. ${withDate} include publication dates.`;
}

export function containsForbiddenTrustClaims(text: string) {
  return FORBIDDEN_TRUST_CLAIMS.test(text);
}

export function policyDetectedLabel(detected: boolean, note?: string) {
  if (detected) return note || "Detected";
  return note || "Not detected within crawl";
}

export function checksForGroup<T extends { group?: string }>(checks: T[] | undefined, group: string) {
  return (checks || []).filter((item) => item.group === group);
}

export function passedSignalMessages<T extends { group?: string; status?: string; message?: string }>(
  checks: T[] | undefined,
  group: string,
) {
  return checksForGroup(checks, group)
    .filter((item) => item.status === "pass")
    .map((item) => item.message || "")
    .filter(Boolean);
}
