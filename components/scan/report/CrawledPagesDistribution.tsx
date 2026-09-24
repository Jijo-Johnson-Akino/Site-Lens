import Link from "next/link";

import { ChartCard, DonutChart } from "@/components/scan/report/charts";
import type { ScanReportResponse } from "@/lib/scan/api";
import { crawledPageSlices, distributionSummary, formatPercent } from "@/lib/scan/report-ui";

export function CrawledPagesDistribution({ report }: { report: ScanReportResponse }) {
  const slices = crawledPageSlices(report);
  const total = slices.reduce((sum, slice) => sum + slice.count, 0);

  return (
    <ChartCard
      title="Crawled Pages Distribution"
      action={
        <Link href={report.pages.href} className="text-xs text-primary hover:underline">
          View pages →
        </Link>
      }
    >
      {!report.pages.available || slices.length === 0 ? (
        <p className="text-sm text-muted-foreground">{report.pages.empty_message || "Page records are unavailable for this scan."}</p>
      ) : (
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
          <DonutChart slices={slices} total={total} centerLabel="Pages" ariaLabel={distributionSummary(slices)} size={156} />
          <ul className="w-full min-w-0 flex-1 space-y-2">
            {slices.map((slice) => (
              <li key={slice.id} className="flex items-start justify-between gap-3 text-[13px]">
                <span className="inline-flex items-center gap-2 text-muted-foreground">
                  <span className="size-2 rounded-full" style={{ backgroundColor: slice.color }} aria-hidden="true" />
                  {slice.label}
                </span>
                <span className="text-right">
                  <span className="font-medium tabular-nums text-foreground">{slice.count}</span>
                  <span className="ml-1 text-[12px] text-muted-foreground">({formatPercent(slice.count, total)})</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ChartCard>
  );
}
