"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Download, ScanLine } from "lucide-react";

import { ScanBreadcrumbs } from "@/components/scan/ScanBreadcrumbs";
import { buttonVariants } from "@/components/ui/button";
import { createScan, ScanApiError, type ScanReportResponse } from "@/lib/scan/api";
import { hostnameOf } from "@/lib/scan/display";
import { analyzedViewport, formatReportDate, headerStatusLabel, previewScreenshot } from "@/lib/scan/report-ui";
import { cn } from "@/lib/utils";

export function ReportHeader({ report }: { report: ScanReportResponse }) {
  const host = hostnameOf(report.scan.website || report.scan.url) || report.scan.website;
  const pages = report.pages.available ? report.pages.summary?.crawled : report.overview.pages_analyzed;
  const issues = report.issues.total;
  const viewport = analyzedViewport(report);
  const preview = previewScreenshot(report.screenshots);
  const analyzed = formatReportDate(report.scan.analyzed_at || report.scan.completed_at);
  const status = headerStatusLabel(report.scan.status, report.report_status);
  const meta = [
    analyzed !== "Unavailable" ? `Analyzed ${analyzed}` : null,
    typeof pages === "number" ? `${pages} pages` : null,
    `${issues} issues`,
    viewport,
  ].filter(Boolean);

  return (
    <header className="rounded-xl border border-border bg-card p-4 shadow-[0_1px_3px_rgba(15,23,42,0.04)] sm:p-5">
      <ScanBreadcrumbs
        items={[
          { href: "/", label: "SiteLens" },
          { href: `/scan/${report.scan.scan_id}`, label: host },
          { label: "Site Audit" },
        ]}
      />
      <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 flex-1 gap-4">
          {preview ? (
            <figure className="hidden w-[180px] shrink-0 overflow-hidden rounded-xl border border-border bg-muted sm:block sm:w-[200px]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={preview.url} alt={preview.alt || `Preview of ${host}`} className="h-28 w-full object-cover object-top" />
              <figcaption className="sr-only">Website preview captured during the scan</figcaption>
            </figure>
          ) : null}
          <div className="min-w-0 flex-1">
            <h1 className="text-[28px] leading-tight font-semibold tracking-tight text-foreground sm:text-[30px]">
              Website Analysis Report
            </h1>
            <p className="mt-1 text-xl font-medium text-foreground sm:text-[22px]">{host}</p>
            <p className="mt-2 text-[12px] text-muted-foreground sm:text-[13px]">{meta.join(" • ")}</p>
            <p className="mt-3">
              <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300">
                {status}
              </span>
            </p>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-start gap-2 print:hidden">
          <button type="button" className={cn(buttonVariants({ variant: "outline", size: "sm" }), "h-8 px-3")} onClick={() => window.print()}>
            <Download className="size-3.5" aria-hidden="true" />
            Download PDF
          </button>
          <NewScanButton url={report.scan.url || report.scan.website} />
        </div>
      </div>
    </header>
  );
}

function NewScanButton({ url }: { url: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        disabled={pending}
        className={cn(buttonVariants({ size: "sm" }), "h-8 px-3")}
        onClick={async () => {
          setPending(true);
          setError(null);
          try {
            const created = await createScan(url);
            router.push(`/scan/${created.scan_id}`);
          } catch (caught) {
            setError(caught instanceof ScanApiError ? caught.message : "Unable to start a new scan.");
            setPending(false);
          }
        }}
      >
        <ScanLine className="size-3.5" aria-hidden="true" />
        {pending ? "Starting…" : "New Scan"}
      </button>
      {error ? <span className="text-[11px] text-critical">{error}</span> : null}
    </span>
  );
}
