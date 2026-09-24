"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ScanBreadcrumbs } from "@/components/scan/ScanBreadcrumbs";
import { PriorityBadge, SourceBadge } from "@/components/scan/IssuesDashboard";
import { ScanShell } from "@/components/scan/ScanShell";
import { ScanStateCard } from "@/components/scan/ScanStateCard";
import { analyzerHref } from "@/lib/scan/action-plan-ui";
import { formatScanDate } from "@/lib/scan/display";
import {
  getRecommendation,
  patchRecommendationStatus,
  ScanApiError,
  type RecommendationDetail,
  type RecommendationStatus,
} from "@/lib/scan/api";
import { issuesHref, RECOMMENDATION_METHODOLOGY, statusLabel, titleCase } from "@/lib/scan/recommendations-ui";
import { pageTitle } from "@/lib/scan/pages-ui";
import { useScanStatus } from "@/lib/scan/use-scan-status";

const STATUSES: RecommendationStatus[] = ["open", "in_progress", "completed", "dismissed"];

export function RecommendationDetailView({
  scanId,
  recommendationId,
  surface = "recommendations",
}: {
  scanId: string;
  recommendationId: string;
  surface?: "recommendations" | "action-plan";
}) {
  const { scan, error } = useScanStatus(scanId);
  const [item, setItem] = useState<RecommendationDetail | null>(null);
  const [methodology, setMethodology] = useState(RECOMMENDATION_METHODOLOGY);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const listHref = surface === "action-plan" ? `/scan/${scanId}/action-plan` : `/scan/${scanId}/recommendations`;
  const listLabel = surface === "action-plan" ? "Action Plan" : "Recommendations";
  const current = surface === "action-plan" ? "action-plan" : "recommendations";

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getRecommendation(scanId, recommendationId)
      .then((result) => {
        if (!cancelled) {
          setItem(result.recommendation);
          setMethodology(result.methodology || RECOMMENDATION_METHODOLOGY);
          setLoadError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setLoadError(caught instanceof ScanApiError ? caught.message : "Recommendation not found.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId, recommendationId]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";

  function onStatusChange(next: RecommendationStatus) {
    if (busy || !item || next === item.status) {
      return;
    }
    setStatusError(null);
    setBusy(true);
    patchRecommendationStatus(scanId, recommendationId, next)
      .then((result) => {
        setItem(result.recommendation);
      })
      .catch((caught) => {
        setStatusError(caught instanceof ScanApiError ? caught.message : "Unable to update status.");
      })
      .finally(() => {
        setBusy(false);
      });
  }

  return (
    <ScanShell scanId={scanId} current={current}>
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <ScanBreadcrumbs
          items={[
            { href: `/scan/${scanId}`, label: "Scan" },
            { href: listHref, label: listLabel },
            { label: item?.title || "Action" },
          ]}
        />
        {failed ? (
          <ScanStateCard title="Recommendation unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <ScanStateCard title="Loading recommendation" body={scan?.current_step ?? "Loading scan status…"} />
        ) : loadError ? (
          <ScanStateCard title="Recommendation not found." body={loadError} />
        ) : !item ? (
          <ScanStateCard title="Loading recommendation" body="Fetching implementation guidance for this scan." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-wrap items-center gap-2">
                <SourceBadge source={item.category.toLowerCase()} category={item.category} />
                <PriorityBadge value={item.priority} />
              </div>
              <h1 className="mt-3 text-2xl font-semibold tracking-tight text-foreground">{item.title}</h1>
              <p className="mt-2 text-sm text-muted-foreground">{item.summary}</p>
              <dl className="mt-6 grid gap-3 sm:grid-cols-4">
                <Metric label="Priority" value={titleCase(item.priority)} />
                <Metric label="Impact" value={titleCase(item.impact)} />
                <Metric label="Effort" value={titleCase(item.effort)} />
                <Metric label="Status" value={statusLabel(item.status)} />
              </dl>
              <label htmlFor="recommendation-status" className="mt-4 block text-xs font-medium text-muted-foreground">
                Update status
              </label>
              <select
                id="recommendation-status"
                className="mt-1 h-10 w-full max-w-xs rounded-lg border border-input bg-transparent px-2 text-sm text-foreground disabled:opacity-50"
                value={item.status}
                disabled={busy}
                aria-busy={busy}
                onChange={(event) => onStatusChange(event.target.value as RecommendationStatus)}
              >
                {STATUSES.map((value) => (
                  <option key={value} value={value}>
                    {statusLabel(value)}
                  </option>
                ))}
              </select>
              {busy ? <p className="mt-2 text-xs text-muted-foreground">Saving status…</p> : null}
              {statusError ? (
                <p className="mt-2 text-sm text-critical" role="alert">
                  {statusError}
                </p>
              ) : null}
              <p className="mt-4 text-xs text-muted-foreground">
                Created {formatScanDate(item.created_at)} · Updated {formatScanDate(item.updated_at)}
              </p>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Why this matters</h2>
              <p className="mt-2 text-sm text-muted-foreground">{item.rationale}</p>
              <p className="mt-3 text-sm">
                <Link href={analyzerHref(scanId, item.category)} className="text-primary hover:underline">
                  View {item.category} analysis
                </Link>
              </p>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Evidence</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {`${item.affected_page_count} ${item.affected_page_count === 1 ? "page" : "pages"} · ${item.issue_count} ${item.issue_count === 1 ? "finding" : "findings"}`}
              </p>
              {item.issue_keys.length ? (
                <p className="mt-2 font-mono text-xs text-muted-foreground">{item.issue_keys.join(", ")}</p>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">Supported by architecture observations from the crawled internal-link graph.</p>
              )}
              {item.issue_ids.length ? (
                <p className="mt-3 text-sm">
                  <Link href={issuesHref(scanId, item.issue_ids, item.issue_keys)} className="text-primary hover:underline">
                    View issues
                  </Link>
                </p>
              ) : null}
              {Array.isArray(item.evidence.resources) && item.evidence.resources.length ? (
                <ul className="mt-3 space-y-1 font-mono text-xs text-muted-foreground">
                  {(item.evidence.resources as string[]).slice(0, 12).map((resource) => (
                    <li key={resource}>{resource}</li>
                  ))}
                </ul>
              ) : null}
              {typeof item.evidence.lcp_note === "string" ? <p className="mt-3 text-sm text-muted-foreground">{item.evidence.lcp_note}</p> : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Action steps</h2>
              <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-foreground">
                {item.action_steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Affected pages</h2>
              {item.affected_pages && item.affected_pages.length ? (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[560px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-border text-xs text-muted-foreground">
                        <th className="py-2 pr-3 font-medium">Page</th>
                        <th className="py-2 pr-3 font-medium">Type</th>
                        <th className="py-2 pr-3 font-medium">Issue count</th>
                        <th className="py-2 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {item.affected_pages.map((page) => (
                        <tr key={page.page_id || page.url} className="border-b border-border/70 last:border-0">
                          <td className="py-3 pr-3">
                            {page.page_id ? (
                              <Link href={`/scan/${scanId}/pages/${page.page_id}`} className="font-medium text-foreground hover:underline">
                                {pageTitle(page.title)}
                              </Link>
                            ) : (
                              <span>{pageTitle(page.title)}</span>
                            )}
                            <p className="mt-1 font-mono text-[11px] text-muted-foreground">{page.url}</p>
                          </td>
                          <td className="py-3 pr-3 text-muted-foreground">{page.page_type_label || titleCase(page.page_type || "unknown")}</td>
                          <td className="py-3 pr-3 text-muted-foreground">{page.issue_count ?? "—"}</td>
                          <td className="py-3 text-muted-foreground">{titleCase(page.crawl_status || "unknown")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">No crawled page records were associated with this recommendation.</p>
              )}
            </section>

            {item.related_recommendations && item.related_recommendations.length ? (
              <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <h2 className="text-sm font-semibold text-foreground">Related recommendations</h2>
                <ul className="mt-3 space-y-2 text-sm">
                  {item.related_recommendations.map((related) => (
                    <li key={related.id}>
                      <Link href={`/scan/${scanId}/${surface}/${related.id}`} className="text-foreground hover:underline">
                        {related.title}
                      </Link>
                      <span className="ml-2 text-xs text-muted-foreground">
                        {related.category} · {titleCase(related.priority)}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <p className="text-xs text-muted-foreground">{methodology}</p>
          </>
        )}
      </div>
    </ScanShell>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-muted/40 p-4">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-foreground">{value}</dd>
    </div>
  );
}
