"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { ScanBreadcrumbs } from "@/components/scan/ScanBreadcrumbs";
import { HttpBadge, IndexableBadge, StatusBadge } from "@/components/scan/PagesDashboard";
import { ScanShell } from "@/components/scan/ScanShell";
import { getPage, ScanApiError, type PageDetail as PageDetailModel } from "@/lib/scan/api";
import { formatBytes, pageTitle, scoreLabel } from "@/lib/scan/pages-ui";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

export function PageDetail({ scanId, pageId }: { scanId: string; pageId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [page, setPage] = useState<PageDetailModel | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!scan || scan.status === "failed") {
      return;
    }
    let cancelled = false;
    getPage(scanId, pageId)
      .then((result) => {
        if (!cancelled) {
          setPage(result.page);
          setLoadError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setLoadError(caught instanceof ScanApiError ? caught.message : "Page not found.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan, scanId, pageId]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";

  return (
    <ScanShell scanId={scanId} current="pages">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <ScanBreadcrumbs
          items={[
            { href: `/scan/${scanId}`, label: "Scan" },
            { href: `/scan/${scanId}/pages`, label: "Pages" },
            { label: page ? pageTitle(page.title) : "Page" },
          ]}
        />
        {failed ? (
          <StateCard title="Pages are unavailable because this scan failed." body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : !scan ? (
          <StateCard title="Loading page" body="Loading scan status…" />
        ) : loadError ? (
          <StateCard title="Page not found." body={loadError} />
        ) : !page ? (
          <div className="h-72 animate-pulse rounded-2xl border border-border bg-muted/40" aria-busy="true" />
        ) : (
          <>
            {running ? (
              <p className="text-sm text-muted-foreground">Page analysis is still in progress.</p>
            ) : null}
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={page.crawl_status} />
                <HttpBadge code={page.http_status} />
                <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                  {page.page_type_label || page.page_type || "Unknown"}
                </span>
              </div>
              <h1 className="mt-4 text-2xl font-semibold tracking-tight text-foreground">{pageTitle(page.title)}</h1>
              <p className="mt-2 break-all font-mono text-sm text-muted-foreground">{page.final_url || page.url}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link href={`/scan/${scanId}/architecture?focus=${page.id}`} className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-muted/40">
                  View Architecture
                </Link>
                <Link
                  href={`/scan/${scanId}/issues?page_url=${encodeURIComponent(page.normalized_url)}`}
                  className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-muted/40"
                >
                  View Issues
                </Link>
              </div>
              {page.skip_reason ? <p className="mt-3 text-sm text-muted-foreground">{page.skip_reason}</p> : null}
              {page.failure_reason ? <p className="mt-3 text-sm text-critical">{page.failure_reason}</p> : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Overview</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                <Info label="Response time" value={typeof page.response_time_ms === "number" ? `${page.response_time_ms} ms` : null} />
                <Info label="Response size" value={formatBytes(page.response_size_bytes)} />
                <Info label="Word count" value={page.word_count != null ? String(page.word_count) : null} />
                <Info label="Indexability" value={null} badge={<IndexableBadge value={page.indexable} />} />
                <Info label="Canonical" value={page.canonical_url} mono />
                <Info label="Depth" value={page.depth != null ? String(page.depth) : null} />
                <Info label="Content type" value={page.content_type} />
                <Info label="Language" value={page.language} />
                <Info label="Discovered from" value={page.discovered_from} mono />
                <Info label="Discovery method" value={page.discovery_method} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">SEO</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                <Info label="Title" value={page.title} />
                <Info label="Title length" value={page.title != null ? String(page.title.length) : null} />
                <Info label="Meta description" value={page.meta_description} />
                <Info label="H1" value={page.h1} />
                <Info label="Canonical" value={page.canonical_url} mono />
                <Info label="Robots" value={page.robots_directive} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Content</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                <Info label="Page type" value={page.page_type_label || page.page_type} />
                <Info label="Word count" value={page.word_count != null ? String(page.word_count) : null} />
                <Info label="H1 count" value={page.h1_count != null ? String(page.h1_count) : null} />
                <Info label="H2 count" value={page.h2_count != null ? String(page.h2_count) : null} />
                <Info label="Paragraphs" value={page.paragraph_count != null ? String(page.paragraph_count) : null} />
                <Info label="Lists" value={page.list_count != null ? String(page.list_count) : null} />
                <Info label="Internal links" value={page.internal_link_count != null ? String(page.internal_link_count) : null} />
                <Info label="External links" value={page.external_link_count != null ? String(page.external_link_count) : null} />
                <Info label="Images" value={page.image_count != null ? String(page.image_count) : null} />
              </dl>
              {page.headings && page.headings.length > 0 ? (
                <ul className="mt-4 space-y-1 text-sm">
                  {page.headings.map((heading, index) => (
                    <li key={`${heading.level}-${index}`} className="text-muted-foreground">
                      H{heading.level}: <span className="text-foreground">{heading.text || "—"}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Issues</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {page.issue_count === 1 ? "1 open finding affecting this page." : `${page.issue_count} open findings affecting this page.`}
              </p>
              <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Metric label="Critical" value={page.severity_counts?.critical ?? 0} />
                <Metric label="High" value={page.severity_counts?.high ?? 0} />
                <Metric label="Medium" value={page.severity_counts?.medium ?? 0} />
                <Metric label="Low" value={page.severity_counts?.low ?? 0} />
              </dl>
              {page.issues && page.issues.length > 0 ? (
                <ul className="mt-5 divide-y divide-border">
                  {page.issues.map((issue) => (
                    <li key={issue.issue_id} className="py-3">
                      <Link href={`/scan/${scanId}/issues/${issue.issue_id}`} className="font-medium text-foreground hover:underline">
                        {issue.title}
                      </Link>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {issue.category} · {issue.severity} · {issue.priority}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">No open issues are associated with this page.</p>
              )}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Analyzers</h2>
              <ul className="mt-4 grid gap-3 sm:grid-cols-2">
                {(page.analyzers || []).map((analyzer) => (
                  <li key={analyzer.id} className="rounded-xl border border-border bg-muted/30 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-foreground">{analyzer.label}</p>
                      <p className={cn("text-sm", typeof analyzer.score === "number" ? "text-foreground" : "text-muted-foreground")}>
                        {scoreLabel(analyzer.score)}
                      </p>
                    </div>
                    {analyzer.available && analyzer.href && analyzer.link_label ? (
                      <Link href={analyzer.href} className="mt-2 inline-block text-sm text-primary hover:underline">
                        {analyzer.link_label}
                      </Link>
                    ) : analyzer.note ? (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {analyzer.note}
                        {analyzer.site_href ? (
                          <>
                            {" "}
                            <Link href={analyzer.site_href} className="text-primary hover:underline">
                              View site analysis
                            </Link>
                          </>
                        ) : null}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </div>
    </ScanShell>
  );
}

function Info({
  label,
  value,
  mono,
  badge,
}: {
  label: string;
  value: string | null | undefined;
  mono?: boolean;
  badge?: ReactNode;
}) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={cn("mt-1 break-all text-foreground", mono && "font-mono text-xs")}>
        {badge ?? (value && value !== "—" ? value : "—")}
      </dd>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-muted/40 px-3 py-2">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-lg font-semibold text-foreground">{value}</dd>
    </div>
  );
}

function StateCard({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-8 shadow-sm">
      <h1 className="text-xl font-semibold tracking-tight text-foreground">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </section>
  );
}
