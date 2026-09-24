export const HEALTH_SCORE_NOTE =
  "The SiteLens Health Score is a composite website analysis metric based on the categories included in the scan. It is not a prediction of search rankings, traffic, revenue, conversions, business success, or user trust.";

export const HEALTH_COVERAGE_NOTE =
  "Score coverage reflects how much of the configured scoring model was supported by completed analysis. It is not a statistical confidence interval.";

export const HEALTH_PARTIAL_NOTICE =
  "Some analysis categories were unavailable. The overall score uses the available categories and renormalizes their configured weights.";

export const HEALTH_LIMITED_NOTICE = "Limited analysis data is available. Treat the overall score as provisional.";

const FORBIDDEN_HEALTH_CLAIMS =
  /google ranking|chatgpt ranking|predicted traffic|predict traffic|revenue increase|conversion probability|this company is trustworthy|this company is legitimate/i;

export function emptyHealthCopy(kind: "loading" | "unavailable" | "incomplete") {
  if (kind === "incomplete") {
    return {
      title: "Calculating Health Score",
      body: "The overall score appears after analyzers, issues, and recommendations complete.",
    };
  }
  if (kind === "unavailable") {
    return {
      title: "Health score unavailable",
      body: "SiteLens could not calculate the score from the available analysis results.",
    };
  }
  return {
    title: "Loading Health Score",
    body: "Fetching the overall website health score for this scan.",
  };
}

export function coverageLabel(status: string | undefined) {
  if (status === "complete") return "Complete";
  if (status === "partial") return "Partial";
  if (status === "limited") return "Limited";
  return "Unavailable";
}

export function categoryStatusLabel(status: string | undefined) {
  if (status === "available") return "Available";
  if (status === "partial") return "Partial";
  if (status === "failed") return "Failed";
  return "Unavailable";
}

export function scoreOutOf100(score: number | null | undefined) {
  if (typeof score !== "number") return "Unavailable";
  return `${score} out of 100`;
}

export function weightPercent(weight: number | null | undefined) {
  if (typeof weight !== "number") return "—";
  const text = Number.isInteger(weight) ? String(weight) : String(weight);
  return `${text}%`;
}

export function containsForbiddenHealthClaims(text: string) {
  return FORBIDDEN_HEALTH_CLAIMS.test(text);
}
