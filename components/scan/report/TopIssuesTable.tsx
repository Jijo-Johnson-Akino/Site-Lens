import { IssueCard } from "@/components/scan/IssueCard";
import { captureInProgress } from "@/components/scan/IssueEvidence";
import { ChartCard } from "@/components/scan/report/charts";
import type { ScanReportResponse } from "@/lib/scan/api";
import { topIssues } from "@/lib/scan/report-ui";
import Link from "next/link";

export function TopIssuesTable({ report }: { report: ScanReportResponse }) {
  const items = topIssues(report, 5);
  const capturing = captureInProgress(report.issues.screenshot_capture?.status);

  return (
    <ChartCard
      title="Top Issues"
      action={
        <Link href={report.issues.href} className="text-xs font-medium text-primary hover:underline">
          View all issues →
        </Link>
      }
      className="min-w-0"
    >
      {report.issues.screenshot_capture?.note ? (
        <p className="mb-3 text-xs text-muted-foreground">{report.issues.screenshot_capture.note}</p>
      ) : null}
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{report.issues.empty_message || "No issues were detected in the completed analysis."}</p>
      ) : (
        <div className="grid gap-3">
          {items.map((item) => (
            <IssueCard
              key={item.issue_id}
              compact
              capturing={capturing}
              className="p-4 shadow-none sm:p-4"
              issue={{
                ...item,
                whats_wrong: item.whats_wrong || item.description,
                how_to_fix: item.how_to_fix || item.recommendation,
              }}
            />
          ))}
        </div>
      )}
    </ChartCard>
  );
}
