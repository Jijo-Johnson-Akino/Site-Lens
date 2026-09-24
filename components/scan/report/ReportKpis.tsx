import Link from "next/link";

import { ChartCard, DonutChart, HealthScoreGauge, HorizontalStackedBar } from "@/components/scan/report/charts";
import type { ScanReportResponse } from "@/lib/scan/api";
import {
  crawledPageSlices,
  distributionSummary,
  previousScanDelta,
  recommendationCategoryRows,
  severitySlices,
  severitySummary,
} from "@/lib/scan/report-ui";

export function ReportKpis({ report }: { report: ScanReportResponse }) {
  const score = report.overview.overall_score;
  const band = typeof score === "number" ? report.overview.score_band || report.overview.score_status || "Scored" : "Unavailable";
  const delta = previousScanDelta(report);
  const pages = crawledPageSlices(report);
  const crawled = report.pages.available ? report.pages.summary?.crawled : report.overview.pages_analyzed;
  const issueSlices = severitySlices(report.issues.by_severity);
  const recRows = recommendationCategoryRows(report.recommendations.by_category);

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <ChartCard title="Website Health Score">
        <div className="flex items-center gap-4">
          <HealthScoreGauge score={score} band={band} />
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground">{typeof score === "number" ? band : "Unavailable"}</p>
            {typeof delta === "number" ? (
              <p className="mt-1 text-xs text-primary">{delta >= 0 ? `↑ +${delta}` : `↓ ${delta}`} vs last scan</p>
            ) : (
              <p className="mt-1 text-xs text-muted-foreground">No previous scan</p>
            )}
            {report.score?.partial_notice ? <p className="mt-2 text-[11px] text-muted-foreground">{report.score.partial_notice}</p> : null}
          </div>
        </div>
      </ChartCard>

      <ChartCard title="Crawled Pages">
        {report.pages.available && typeof crawled === "number" ? (
          <>
            <p className="text-[32px] leading-none font-semibold tracking-tight text-foreground">{crawled}</p>
            <div className="mt-3">
              <HorizontalStackedBar slices={pages} ariaLabel={distributionSummary(pages)} />
            </div>
            <ul className="mt-3 space-y-1">
              {pages.map((slice) => (
                <li key={slice.id} className="flex items-center justify-between gap-3 text-[12px] text-muted-foreground">
                  <span className="inline-flex items-center gap-2">
                    <span className="size-1.5 rounded-full" style={{ backgroundColor: slice.color }} aria-hidden="true" />
                    {slice.label}
                  </span>
                  <span className="tabular-nums text-foreground">{slice.count}</span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">Page records are unavailable for this scan.</p>
        )}
      </ChartCard>

      <ChartCard
        title="Issues by Severity"
        action={
          <Link href={report.issues.href} className="text-xs text-primary hover:underline">
            View all
          </Link>
        }
      >
        {report.issues.total === 0 ? (
          <p className="text-sm text-muted-foreground">{report.issues.empty_message || "No issues were detected in the completed analysis."}</p>
        ) : (
          <div className="flex items-center gap-3">
            <DonutChart
              slices={issueSlices}
              total={report.issues.total}
              centerLabel="Total issues"
              ariaLabel={severitySummary(issueSlices)}
              size={118}
              thickness={14}
            />
            <ul className="min-w-0 flex-1 space-y-1.5">
              {issueSlices.map((slice) => (
                <li
                  key={slice.id}
                  className="grid grid-cols-[8px_minmax(0,1fr)_auto] items-center gap-x-1.5 text-[11px] leading-4 text-muted-foreground"
                >
                  <span className="size-1.5 justify-self-center rounded-full" style={{ backgroundColor: slice.color }} aria-hidden="true" />
                  <span className="truncate">{slice.label}</span>
                  <span className="tabular-nums text-foreground">{slice.count}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </ChartCard>

      <ChartCard
        title="Recommendations"
        action={
          <Link href={report.recommendations.href} className="text-xs text-primary hover:underline">
            View all
          </Link>
        }
      >
        {report.recommendations.total === 0 ? (
          <p className="text-sm text-muted-foreground">{report.recommendations.empty_message || "No recommendations were generated from the available findings."}</p>
        ) : (
          <>
            <p className="text-[32px] leading-none font-semibold tracking-tight text-foreground">{report.recommendations.total}</p>
            <ul className="mt-3 space-y-1">
              {recRows.length > 0
                ? recRows.slice(0, 6).map((row) => (
                    <li key={row.id} className="flex items-center justify-between gap-3 text-[12px] text-muted-foreground">
                      <span>{row.label}</span>
                      <span className="tabular-nums text-foreground">{row.count}</span>
                    </li>
                  ))
                : Object.entries(report.recommendations.by_priority)
                    .filter(([, count]) => count > 0)
                    .map(([label, count]) => (
                      <li key={label} className="flex items-center justify-between gap-3 text-[12px] text-muted-foreground">
                        <span className="capitalize">{label}</span>
                        <span className="tabular-nums text-foreground">{count}</span>
                      </li>
                    ))}
            </ul>
          </>
        )}
      </ChartCard>
    </div>
  );
}
