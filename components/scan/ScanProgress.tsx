"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { ScanCompletion } from "@/components/scan/ScanCompletion";
import { ScanFailure } from "@/components/scan/ScanFailure";
import { ScanHeader } from "@/components/scan/ScanHeader";
import { ScanLifecycle } from "@/components/scan/ScanLifecycle";
import { ScanMonitorNav } from "@/components/scan/ScanMonitorNav";
import { ScanMonitorOverview } from "@/components/scan/ScanMonitorOverview";
import { ScanOverview } from "@/components/scan/ScanOverview";
import { ScanProgressHero } from "@/components/scan/ScanProgressHero";
import { ScanScope } from "@/components/scan/ScanScope";
import { ScanStepList } from "@/components/scan/ScanStepList";
import { createScan } from "@/lib/scan/api";
import {
  currentStepNumber,
  displayProgress,
  lifecycleForSteps,
} from "@/lib/scan/progress-ui";
import { statusesForScan } from "@/lib/scan/steps";
import { useScanStatus } from "@/lib/scan/use-scan-status";

/** Backend `run()` continues after the client unmounts and stops polling. */
const LEAVE_PAGE_SUPPORTED = true;

export function ScanProgress({ scanId }: { scanId: string }) {
  const router = useRouter();
  const { scan, error } = useScanStatus(scanId);
  const [retrying, setRetrying] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [sawRunning, setSawRunning] = useState(false);
  if ((scan?.status === "queued" || scan?.status === "running") && !sawRunning) {
    setSawRunning(true);
  }

  const status = scan?.status ?? (error ? "failed" : "queued");
  const currentStep = scan?.current_step ?? "Validating website";
  const failed = status === "failed" || (!scan && Boolean(error));
  const completed = status === "completed";
  const cancelled = status === "cancelled";
  const failureMessage = scan?.error?.message ?? error ?? "Unable to analyze this website.";
  const href = scan?.normalized_url || scan?.url;
  const steps = statusesForScan({
    progress: typeof scan?.progress === "number" ? scan.progress : 0,
    currentStep,
    status: failed && !scan ? "failed" : status,
  });
  const percent = displayProgress(scan?.progress, steps);
  const stages = lifecycleForSteps(steps);
  const { current: stepNumber, total: stepTotal } = currentStepNumber(steps);

  async function retry() {
    const url = scan?.url;
    if (!url) {
      router.push("/");
      return;
    }
    setRetrying(true);
    try {
      const created = await createScan(url);
      router.push(`/scan/${created.scan_id}`);
    } catch {
      setRetrying(false);
    }
  }

  if (completed && scan && (showDashboard || !sawRunning)) {
    return <ScanOverview scan={scan} />;
  }

  if (completed && scan) {
    return (
      <ScanMonitorShell
        scanId={scanId}
        url={href}
        showDetails
        onViewDetails={() => setShowDashboard(true)}
      >
        <ScanCompletion scanId={scanId} url={href} onViewOverview={() => setShowDashboard(true)} />
      </ScanMonitorShell>
    );
  }

  if (cancelled) {
    return (
      <ScanMonitorShell scanId={scanId} url={href}>
        <ScanFailure
          cancelled
          message={failureMessage}
          canRetry={Boolean(scan?.url)}
          retrying={retrying}
          onRetry={() => void retry()}
        />
      </ScanMonitorShell>
    );
  }

  if (failed && (error || scan)) {
    return (
      <ScanMonitorShell scanId={scanId} url={href}>
        <ScanFailure
          message={failureMessage}
          canRetry={Boolean(scan?.url)}
          retrying={retrying}
          onRetry={() => void retry()}
        />
      </ScanMonitorShell>
    );
  }

  return (
    <ScanMonitorShell scanId={scanId} url={href}>
      <ScanHeader leavePageSupported={LEAVE_PAGE_SUPPORTED} />
      <div className="scan-monitor-layout mt-10">
        <div className="scan-area-life min-w-0">
          <ScanLifecycle stages={stages} leavePageSupported={LEAVE_PAGE_SUPPORTED} />
        </div>
        <div className="scan-area-hero min-w-0">
          <ScanProgressHero
            progress={percent}
            url={href}
            currentStep={currentStep}
            stepNumber={stepNumber}
            stepTotal={stepTotal}
          />
        </div>
        <div className="scan-area-steps min-w-0">
          <ScanStepList steps={steps} />
        </div>
        <div className="scan-area-side flex min-w-0 flex-col gap-6">
          <ScanMonitorOverview
            scan={scan}
            currentStage={currentStep}
            leavePageSupported={LEAVE_PAGE_SUPPORTED}
          />
          <ScanScope />
        </div>
      </div>
    </ScanMonitorShell>
  );
}

function ScanMonitorShell({
  children,
  scanId,
  url,
  showDetails,
  onViewDetails,
}: {
  children: ReactNode;
  scanId: string;
  url?: string;
  showDetails?: boolean;
  onViewDetails?: () => void;
}) {
  return (
    <div className="scan-monitor relative min-h-svh overflow-x-hidden bg-background text-foreground">
      <div className="scan-monitor-grid pointer-events-none absolute inset-0" aria-hidden />
      <ScanMonitorNav scanId={scanId} url={url} showDetails={showDetails} onViewDetails={onViewDetails} />
      <main className="scan-monitor-container relative py-8 sm:py-10 lg:py-12">{children}</main>
      <p className="scan-monitor-container relative pb-10 text-center text-sm text-muted-foreground">
        <Link
          href="/"
          className="font-medium text-ink underline-offset-4 hover:text-brand hover:underline focus-visible:rounded-md focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
        >
          Back to SiteLens
        </Link>
      </p>
    </div>
  );
}
