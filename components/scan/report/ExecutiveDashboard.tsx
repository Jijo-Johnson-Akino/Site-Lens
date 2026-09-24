import Link from "next/link";

import { CrawledPagesDistribution } from "@/components/scan/report/CrawledPagesDistribution";
import { ReportHeader } from "@/components/scan/report/ReportHeader";
import { ReportKpis } from "@/components/scan/report/ReportKpis";
import { ThematicReports } from "@/components/scan/report/ThematicReports";
import { TopIssuesTable } from "@/components/scan/report/TopIssuesTable";
import { CategoryBarChart, ChartCard, ScoreTrendArea } from "@/components/scan/report/charts";
import type { ScanReportResponse } from "@/lib/scan/api";
import {
  availableCategoryBars,
  categoryChartSummary,
  scoreHistoryFromReport,
} from "@/lib/scan/report-ui";

export function ExecutiveDashboard({ report }: { report: ScanReportResponse }) {
  const history = scoreHistoryFromReport(report);
  const bars = availableCategoryBars(report.categories);

  return (
    <div className="space-y-4">
      <ReportHeader report={report} />
      <ReportKpis report={report} />

      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Score Trend" action={<span className="text-xs text-muted-foreground">Last 6 scans</span>}>
          {history.length < 2 ? (
            <div className="flex min-h-[180px] flex-col justify-center rounded-lg bg-muted/40 px-4 py-8 text-center">
              <p className="text-sm font-medium text-foreground">Not enough scan history yet</p>
              <p className="mt-1 text-sm text-muted-foreground">Run another scan to compare health score changes over time.</p>
            </div>
          ) : (
            <ScoreTrendArea points={history} />
          )}
        </ChartCard>

        <ChartCard
          title="Score by Category"
          action={
            <Link href={`/scan/${report.scan.scan_id}/score`} className="text-xs text-primary hover:underline">
              Score breakdown →
            </Link>
          }
        >
          {bars.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">Category scores are unavailable for this scan.</p>
          ) : (
            <CategoryBarChart bars={bars} ariaLabel={categoryChartSummary(bars)} />
          )}
        </ChartCard>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.45fr)_minmax(280px,0.85fr)]">
        <TopIssuesTable report={report} />
        <CrawledPagesDistribution report={report} />
      </div>

      <ThematicReports report={report} />

      <details id="methodology" className="rounded-xl border border-border bg-card p-4 shadow-[0_1px_3px_rgba(15,23,42,0.04)]">
        <summary className="cursor-pointer text-[15px] font-semibold text-foreground">Methodology</summary>
        <div className="mt-3 space-y-2 text-[13px] text-muted-foreground">
          {report.methodology.paragraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
          {report.limitations.length > 0 ? (
            <ul className="list-disc space-y-1 pl-5">
              {report.limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
        </div>
      </details>
    </div>
  );
}
