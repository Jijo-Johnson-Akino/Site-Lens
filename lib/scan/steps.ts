import type { ScanStepStatus } from "@/lib/scan/api";

export type ScanStepDefinition = {
  id: string;
  label: string;
  progress: number;
  activity: string;
};

export const SCAN_STEPS: ScanStepDefinition[] = [
  { id: "validate", label: "Validating website", progress: 0, activity: "Validating website" },
  { id: "connect", label: "Connecting", progress: 15, activity: "Connecting" },
  { id: "fetch", label: "Fetching homepage", progress: 30, activity: "Fetching homepage" },
  { id: "parse", label: "Parsing website", progress: 40, activity: "Parsing website" },
  { id: "pages", label: "Discovering pages", progress: 45, activity: "Discovering pages" },
  { id: "seo", label: "SEO analysis", progress: 50, activity: "SEO analysis" },
  { id: "aeo", label: "AEO analysis", progress: 65, activity: "AEO analysis" },
  { id: "render", label: "Rendering website", progress: 75, activity: "Rendering website" },
  { id: "uiux", label: "UI/UX analysis", progress: 82, activity: "UI/UX analysis" },
  { id: "shots", label: "Capturing screenshots", progress: 88, activity: "Capturing screenshots" },
  { id: "a11y", label: "Accessibility analysis", progress: 92, activity: "Accessibility analysis" },
  { id: "perf", label: "Performance analysis", progress: 96, activity: "Performance analysis" },
  { id: "content", label: "Content analysis", progress: 97, activity: "Content analysis" },
  { id: "schema", label: "Structured Data Analysis", progress: 98, activity: "Structured Data Analysis" },
  { id: "mobile", label: "Mobile Analysis", progress: 99, activity: "Mobile Analysis" },
  { id: "cro", label: "CRO Analysis", progress: 99, activity: "CRO Analysis" },
  { id: "trust", label: "Trust & Credibility Analysis", progress: 99, activity: "Trust & Credibility Analysis" },
  { id: "issues", label: "Aggregating Issues", progress: 99, activity: "Aggregating Issues" },
  { id: "recommendations", label: "Generating Recommendations", progress: 99, activity: "Generating Recommendations" },
  { id: "score", label: "Calculating Health Score", progress: 99, activity: "Calculating Health Score" },
  { id: "ready", label: "Analysis complete", progress: 100, activity: "Analysis complete" },
];

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
