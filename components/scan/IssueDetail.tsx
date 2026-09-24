"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { IssueCard } from "@/components/scan/IssueCard";
import { captureInProgress } from "@/components/scan/IssueEvidence";
import { ScanBreadcrumbs } from "@/components/scan/ScanBreadcrumbs";
import { ScanShell } from "@/components/scan/ScanShell";
import { getIssue, ScanApiError, type ScreenshotCaptureSummary, type UnifiedIssueDetail } from "@/lib/scan/api";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

function sourceHref(scanId: string, issue: UnifiedIssueDetail) {
  if (!issue.source_href) {
    return null;
  }
  return `/scan/${scanId}/${issue.source_href}`;
}

export function IssueDetail({ scanId, issueId }: { scanId: string; issueId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [issue, setIssue] = useState<UnifiedIssueDetail | null>(null);
  const [capture, setCapture] = useState<ScreenshotCaptureSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    let timer: number | undefined;

    const load = () => {
      getIssue(scanId, issueId)
        .then((result) => {
          if (cancelled) {
            return;
          }
          setIssue(result.issue);
          setCapture(result.screenshot_capture ?? null);
          setLoadError(null);
          if (captureInProgress(result.screenshot_capture?.status)) {
            timer = window.setTimeout(load, 2000);
          }
        })
        .catch((caught) => {
          if (!cancelled) {
            setLoadError(caught instanceof ScanApiError ? caught.message : "Issue not found.");
          }
        });
    };

    load();
    return () => {
      cancelled = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [scan?.status, scanId, issueId]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const analyzerHref = issue ? sourceHref(scanId, issue) : null;

  return (
    <ScanShell scanId={scanId} current="issues">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <ScanBreadcrumbs
          items={[
            { href: `/scan/${scanId}`, label: "Scan" },
            { href: `/scan/${scanId}/issues`, label: "Issues" },
            { label: issue?.title || "Issue" },
          ]}
        />
        {failed ? (
          <StateCard title="Issue unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title="Loading issue" body={scan?.current_step ?? "Loading scan status…"} />
        ) : loadError ? (
          <StateCard title="Issue not found." body={loadError} />
        ) : !issue ? (
          <StateCard title="Loading issue" body="Fetching the unified finding for this scan." />
        ) : (
          <>
            {capture?.note ? <p className="text-sm text-muted-foreground">{capture.note}</p> : null}
            <IssueCard issue={issue} capturing={captureInProgress(capture?.status)} heading="h1" />

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Source</h2>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-muted-foreground">Analyzer</dt>
                  <dd className="mt-1 text-foreground">{issue.analyzer}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Check</dt>
                  <dd className="mt-1 font-mono text-xs text-foreground">{issue.check_id}</dd>
                </div>
              </dl>
              {analyzerHref ? (
                <Link href={analyzerHref} className={cn("mt-5 inline-flex h-10 items-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground")}>
                  Open {issue.category} analysis
                </Link>
              ) : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Related issues</h2>
              {(issue.related_issues || []).length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No related issues were linked for this finding.</p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {(issue.related_issues || []).map((related) => (
                    <li key={related.issue_id}>
                      <Link href={`/scan/${scanId}/issues/${related.issue_id}`} className="text-sm font-medium text-foreground hover:underline">
                        {related.title}
                      </Link>
                      <p className="text-xs text-muted-foreground">
                        {related.category} · {related.priority}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </ScanShell>
  );
}

function StateCard({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h1 className="text-lg font-semibold text-foreground">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </section>
  );
}
