import type { ScanStepStatus } from "@/lib/scan/api";

export type ScanStepDefinition = {
  id: string;
  label: string;
  progress: number;
  activity: string;
};

const STEP_DEFS = [
  { id: "validate", label: "Validating website", activity: "Validating website" },
  { id: "connect", label: "Connecting", activity: "Connecting" },
  { id: "fetch", label: "Fetching homepage", activity: "Fetching homepage" },
  { id: "parse", label: "Parsing website", activity: "Parsing website" },
  { id: "pages", label: "Discovering pages", activity: "Discovering pages" },
  { id: "seo", label: "SEO analysis", activity: "SEO analysis" },
  { id: "aeo", label: "AEO analysis", activity: "AEO analysis" },
  { id: "render", label: "Rendering website", activity: "Rendering website" },
  { id: "uiux", label: "UI/UX analysis", activity: "UI/UX analysis" },
  { id: "shots", label: "Capturing screenshots", activity: "Capturing screenshots" },
  { id: "a11y", label: "Accessibility analysis", activity: "Accessibility analysis" },
  { id: "perf", label: "Performance analysis", activity: "Performance analysis" },
  { id: "content", label: "Content analysis", activity: "Content analysis" },
  { id: "schema", label: "Structured Data Analysis", activity: "Structured Data Analysis" },
  { id: "mobile", label: "Mobile Analysis", activity: "Mobile Analysis" },
  { id: "cro", label: "CRO Analysis", activity: "CRO Analysis" },
  { id: "trust", label: "Trust & Credibility Analysis", activity: "Trust & Credibility Analysis" },
  { id: "issues", label: "Aggregating Issues", activity: "Aggregating Issues" },
  { id: "recommendations", label: "Generating Recommendations", activity: "Generating Recommendations" },
  { id: "score", label: "Calculating Health Score", activity: "Calculating Health Score" },
  { id: "ready", label: "Analysis complete", activity: "Analysis complete" },
] as const;

export const SCAN_STEPS: ScanStepDefinition[] = STEP_DEFS.map((step, index) => ({
  id: step.id,
  label: step.label,
  activity: step.activity,
  progress: Math.round(((index + 1) / STEP_DEFS.length) * 100),
}));

export function statusesForScan(options: {
  progress: number;
  currentStep: string;
  status: string;
}): Array<ScanStepDefinition & { status: ScanStepStatus }> {
  const { progress, currentStep, status } = options;
  if (status === "completed") {
    return SCAN_STEPS.map((step) => ({ ...step, status: "completed" }));
  }

  const currentIndex = SCAN_STEPS.findIndex((step) => step.activity === currentStep);
  return SCAN_STEPS.map((step, index) => {
    if (status === "failed" && step.activity === currentStep) {
      return { ...step, status: "failed" };
    }
    if (currentIndex >= 0) {
      if (index < currentIndex) {
        return { ...step, status: "completed" };
      }
      if (index === currentIndex) {
        return { ...step, status: "active" };
      }
      return { ...step, status: "pending" };
    }
    if (step.activity === currentStep) {
      return { ...step, status: "active" };
    }
    if (progress > step.progress) {
      return { ...step, status: "completed" };
    }
    return { ...step, status: "pending" };
  });
}
