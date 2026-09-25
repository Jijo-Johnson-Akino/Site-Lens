import type { ScanStepStatus } from "@/lib/scan/api";
import { SCAN_STEPS, type ScanStepDefinition } from "@/lib/scan/steps";

export type LifecycleStageId = "init" | "crawl" | "analyze" | "insights" | "final";

export type LifecycleStageDef = {
  id: LifecycleStageId;
  index: string;
  title: string;
  description: string;
  stepIds: string[];
};

export type LifecycleStageState = LifecycleStageDef & {
  status: "completed" | "current" | "pending";
};

export const SCAN_LIFECYCLE: LifecycleStageDef[] = [
  {
    id: "init",
    index: "01",
    title: "Initializing",
    description: "Setting up the scan",
    stepIds: ["validate", "connect"],
  },
  {
    id: "crawl",
    index: "02",
    title: "Crawling",
    description: "Discovering pages",
    stepIds: ["fetch", "parse", "pages"],
  },
  {
    id: "analyze",
    index: "03",
    title: "Analyzing",
    description: "Running website analysis",
    stepIds: ["seo", "aeo", "render", "uiux", "shots", "a11y", "perf", "content", "schema", "mobile", "cro", "trust"],
  },
  {
    id: "insights",
    index: "04",
    title: "Generating insights",
    description: "Preparing findings",
    stepIds: ["issues", "recommendations", "score"],
  },
  {
    id: "final",
    index: "05",
    title: "Finalizing",
    description: "Preparing your results",
    stepIds: ["ready"],
  },
];

const ACTIVITY_HEADLINES: Record<string, string> = {
  "Validating website": "Validating website...",
  Connecting: "Connecting to website...",
  "Fetching homepage": "Fetching homepage...",
  "Parsing website": "Parsing website...",
  "Discovering pages": "Discovering pages...",
  "SEO analysis": "Running SEO analysis...",
  "AEO analysis": "Running AEO analysis...",
  "Rendering website": "Rendering website...",
  "UI/UX analysis": "Running UI/UX analysis...",
  "Capturing screenshots": "Capturing screenshots...",
  "Accessibility analysis": "Running accessibility analysis...",
  "Performance analysis": "Running performance analysis...",
  "Content analysis": "Running content analysis...",
  "Structured Data Analysis": "Running structured data analysis...",
  "Mobile Analysis": "Running mobile analysis...",
  "CRO Analysis": "Running CRO analysis...",
  "Trust & Credibility Analysis": "Running Trust & Credibility analysis...",
  "Aggregating Issues": "Aggregating issues...",
  "Generating Recommendations": "Generating recommendations...",
  "Calculating Health Score": "Calculating Health Score...",
  "Analysis complete": "Preparing report...",
};

const ACTIVITY_DETAILS: Record<string, string> = {
  "Validating website": "Checking that the website URL is reachable and valid.",
  Connecting: "Establishing a connection to your website.",
  "Fetching homepage": "Retrieving the homepage so analysis can begin.",
  "Parsing website": "Reading page structure, content, and technical signals.",
  "Discovering pages": "Finding and analyzing all accessible pages on your website.",
  "SEO analysis": "Evaluating search visibility, metadata, and on-page SEO.",
  "AEO analysis": "Checking how well the site is prepared for AI search and answers.",
  "Rendering website": "Rendering key pages to capture the real user experience.",
  "UI/UX analysis": "Reviewing layout, hierarchy, and interaction quality.",
  "Capturing screenshots": "Capturing visual evidence of key pages.",
  "Accessibility analysis": "Checking accessibility barriers that affect real users.",
  "Performance analysis": "Measuring load, responsiveness, and page-speed signals.",
  "Content analysis": "Reviewing content quality, clarity, and coverage.",
  "Structured Data Analysis": "Inspecting structured data that helps search engines understand the site.",
  "Mobile Analysis": "Evaluating the mobile experience across key pages.",
  "CRO Analysis": "Reviewing conversion paths, calls to action, and friction.",
  "Trust & Credibility Analysis": "Checking trust signals, credibility, and confidence cues.",
  "Aggregating Issues": "Collecting and prioritizing issues found across analyzers.",
  "Generating Recommendations": "Turning findings into an actionable improvement plan.",
  "Calculating Health Score": "Calculating your Website Health Score from completed analysis.",
  "Analysis complete": "Preparing your results and report.",
};

export const COLLAPSED_STEP_COUNT = 9;

export function clampProgress(value: number | null | undefined): number {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return 0;
  }
  return Math.min(100, Math.max(0, Math.round(value)));
}

export function percentFromStep(currentStep: number, totalSteps: number): number {
  if (!Number.isFinite(currentStep) || !Number.isFinite(totalSteps) || totalSteps <= 0) {
    return 0;
  }
  const current = Math.min(totalSteps, Math.max(0, currentStep));
  return Math.round((current / totalSteps) * 100);
}

export function scanProgressFromSteps(
  steps: Array<ScanStepDefinition & { status: ScanStepStatus }>,
  fraction?: number,
): { currentStep: number; totalSteps: number; percent: number } {
  const { current, total } = currentStepNumber(steps);
  if (total <= 0) {
    return { currentStep: 0, totalSteps: 0, percent: 0 };
  }
  const percent =
    typeof fraction === "number" && Number.isFinite(fraction)
      ? Math.round(((current - 1 + Math.min(1, Math.max(0, fraction))) / total) * 100)
      : percentFromStep(current, total);
  return {
    currentStep: current,
    totalSteps: total,
    percent: clampProgress(percent),
  };
}

/** Weighted API `progress` is ignored — circle and step text share this value. */
export function displayProgress(
  _apiProgress: number | null | undefined,
  steps: Array<ScanStepDefinition & { status: ScanStepStatus }>,
): number {
  return scanProgressFromSteps(steps).percent;
}

export function activityHeadline(activity: string | null | undefined): string {
  if (!activity) {
    return "Starting scan...";
  }
  return ACTIVITY_HEADLINES[activity] ?? `${activity}...`;
}

export function activityDetail(activity: string | null | undefined): string {
  if (!activity) {
    return "SiteLens is preparing to analyze this website.";
  }
  return ACTIVITY_DETAILS[activity] ?? "SiteLens is analyzing this website.";
}

export function formatElapsed(ms: number): string | null {
  if (!Number.isFinite(ms) || ms < 0) {
    return null;
  }
  const totalSec = Math.floor(ms / 1000);
  const hours = Math.floor(totalSec / 3600);
  const minutes = Math.floor((totalSec % 3600) / 60);
  const seconds = totalSec % 60;
  const parts: string[] = [];
  if (hours > 0) {
    parts.push(`${hours} ${hours === 1 ? "hour" : "hours"}`);
  }
  if (minutes > 0 || hours > 0) {
    parts.push(`${minutes} ${minutes === 1 ? "minute" : "minutes"}`);
  }
  parts.push(`${seconds} ${seconds === 1 ? "second" : "seconds"}`);
  return parts.join(" ");
}

export function elapsedFrom(iso: string | null | undefined, nowMs: number, endIso?: string | null): string | null {
  if (!iso) {
    return null;
  }
  const start = Date.parse(iso);
  if (Number.isNaN(start)) {
    return null;
  }
  const end = endIso ? Date.parse(endIso) : nowMs;
  const endMs = Number.isNaN(end) ? nowMs : end;
  return formatElapsed(Math.max(0, endMs - start));
}

export function currentStepNumber(
  steps: Array<ScanStepDefinition & { status: ScanStepStatus }>,
): { current: number; total: number } {
  const total = steps.length || SCAN_STEPS.length;
  const activeIndex = steps.findIndex((step) => step.status === "active" || step.status === "failed");
  if (activeIndex >= 0) {
    return { current: activeIndex + 1, total };
  }
  const completed = steps.filter((step) => step.status === "completed").length;
  return { current: Math.min(total, Math.max(1, completed)), total };
}

export function lifecycleForSteps(
  steps: Array<ScanStepDefinition & { status: ScanStepStatus }>,
): LifecycleStageState[] {
  const byId = new Map(steps.map((step) => [step.id, step.status]));
  const raw = SCAN_LIFECYCLE.map((stage) => {
    const statuses = stage.stepIds.map((id) => byId.get(id) ?? "pending");
    return {
      ...stage,
      allCompleted: statuses.length > 0 && statuses.every((status) => status === "completed"),
      hasActive: statuses.some((status) => status === "active" || status === "failed"),
    };
  });
  const activeIndex = raw.findIndex((stage) => stage.hasActive);
  const pendingIndex = raw.findIndex((stage) => !stage.allCompleted);
  const currentIndex = activeIndex >= 0 ? activeIndex : pendingIndex;

  return raw.map((stage, index) => {
    let status: LifecycleStageState["status"] = "pending";
    if (stage.allCompleted) {
      status = "completed";
    } else if (index === currentIndex) {
      status = "current";
    }
    return {
      id: stage.id,
      index: stage.index,
      title: stage.title,
      description: stage.description,
      stepIds: stage.stepIds,
      status,
    };
  });
}

export function stepStatusLabel(status: ScanStepStatus): string {
  if (status === "completed") return "Completed";
  if (status === "active") return "In progress";
  if (status === "failed") return "Failed";
  return "Pending";
}
