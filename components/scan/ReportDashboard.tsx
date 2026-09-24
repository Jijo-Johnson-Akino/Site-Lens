"use client";

import { ScanShell, type ScanNavId } from "@/components/scan/ScanShell";
import { ExecutiveDashboard } from "@/components/scan/report/ExecutiveDashboard";
import { ReportSkeletons } from "@/components/scan/report/ReportSkeletons";
import { buttonVariants } from "@/components/ui/button";
import { captureInProgress } from "@/components/scan/IssueEvidence";
import { getPages, getRecommendations, getScanReport, ScanApiError, type ScanReportResponse } from "@/lib/scan/api";
import { emptyReportCopy, pageDistributionFromItems, recommendationCategoryRows } from "@/lib/scan/report-ui";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";

export function ReportDashboard({
  scanId,
  current = "report",
}: {
  scanId: string;
  current?: Extract<ScanNavId, "report" | "overview">;
}) {
  const { scan, error } = useScanStatus(scanId);
  const [report, setReport] = useState<ScanReportResponse | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (scan?.status !== "completed") return;
    let cancelled = false;
    let timer: number | undefined;

    const load = () => {
      getDashboardReport(scanId)
        .then((result) => {
          if (cancelled) return;
          setReport(result);
          setReportError(null);
          if (captureInProgress(result.issues.screenshot_capture?.status)) {
            timer = window.setTimeout(load, 2500);
          }
        })
        .catch((caught) => {
          if (!cancelled) {
            setReport(null);
            setReportError(caught instanceof ScanApiError ? caught.message : emptyReportCopy("error").body);
          }
        });
    };

    load();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [scan?.status, scanId, retryToken]);

  const failed = scan?.status === "failed" || Boolean(error);
  const statusLoading = !failed && !scan && !error;
  const running = !failed && scan != null && scan.status !== "completed";

  return (
    <ScanShell scanId={scanId} current={current}>
      <div className="mx-auto w-full max-w-6xl">
        {failed ? (
          <StateCard title={emptyReportCopy("unavailable").title} body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : statusLoading || running ? (
          <StateCard
            title={emptyReportCopy(statusLoading ? "loading" : "incomplete").title}
            body={scan?.current_step ?? emptyReportCopy(statusLoading ? "loading" : "incomplete").body}
            busy={statusLoading || running}
          />
        ) : reportError ? (
          <section className="rounded-xl border border-border bg-card p-6 shadow-[0_1px_3px_rgba(15,23,42,0.04)] sm:p-8">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Unable to load report</h1>
            <p className="mt-2 text-sm text-muted-foreground">{reportError}</p>
            <button type="button" className={cn(buttonVariants(), "mt-4 h-10 px-4")} onClick={() => setRetryToken((value) => value + 1)}>
              Retry
            </button>
          </section>
        ) : !report ? (
          <ReportSkeletons />
        ) : (
          <ExecutiveDashboard report={report} />
        )}
      </div>
    </ScanShell>
  );
}

function StateCard({ title, body, busy }: { title: string; body: string; busy?: boolean }) {
  return (
    <section className="rounded-xl border border-border bg-card p-6 shadow-[0_1px_3px_rgba(15,23,42,0.04)] sm:p-8" aria-busy={busy || undefined}>
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
      {busy ? <div className="mt-6 h-40 animate-pulse rounded-xl bg-muted/60" /> : null}
    </section>
  );
}

async function getDashboardReport(scanId: string): Promise<ScanReportResponse> {
  const report = await getScanReport(scanId);
  const missingCategories = recommendationCategoryRows(report.recommendations.by_category).length === 0;
  const missingDistribution = report.pages.available && !report.pages.distribution;
  await Promise.all([
    missingCategories
      ? getRecommendations(scanId, { page: 1, page_size: 1 })
          .then((result) => {
            report.recommendations.by_category = Object.fromEntries(
              Object.entries(result.summary.by_category ?? {}).filter(([, count]) => typeof count === "number" && count > 0),
            );
          })
          .catch(() => undefined)
      : Promise.resolve(),
    missingDistribution
      ? getPages(scanId, { page: 1, page_size: 100 })
          .then((result) => {
            report.pages.distribution = pageDistributionFromItems(result.items);
          })
          .catch(() => undefined)
      : Promise.resolve(),
  ]);
  return report;
}
