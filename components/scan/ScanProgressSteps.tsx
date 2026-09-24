import { ScanStep } from "@/components/scan/ScanStep";
import type { ScanStepStatus } from "@/lib/scan/api";

export type ScanProgressStep = {
  id: string;
  label: string;
  status: ScanStepStatus;
};

export function ScanProgressSteps({ steps }: { steps: ScanProgressStep[] }) {
  return (
    <ol className="space-y-3">
      {steps.map((step) => (
        <ScanStep key={step.id} label={step.label} status={step.status} />
      ))}
    </ol>
  );
}
