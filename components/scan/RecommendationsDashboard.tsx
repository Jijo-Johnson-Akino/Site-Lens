"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { FilterSelect } from "@/components/scan/FilterSelect";
import { PriorityBadge, SourceBadge } from "@/components/scan/IssuesDashboard";
import { ScanShell } from "@/components/scan/ScanShell";
import { ScanStateCard } from "@/components/scan/ScanStateCard";
import {
  getRecommendations,
  ScanApiError,
  type AnalyzerRunStatus,
  type RecommendationEffort,
  type RecommendationImpact,
  type RecommendationListItem,
  type RecommendationPriority,
  type RecommendationsListResponse,
  type RecommendationStatus,
} from "@/lib/scan/api";
import {
  emptyRecommendationsCopy,
  issuesHref,
  RECOMMENDATION_CATEGORIES,
  RECOMMENDATION_METHODOLOGY,
  statusLabel,
  titleCase,
} from "@/lib/scan/recommendations-ui";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const PRIORITIES: Array<"all" | RecommendationPriority> = ["all", "critical", "high", "medium", "low", "info"];
const IMPACTS: Array<"all" | RecommendationImpact> = ["all", "high", "medium", "low"];
const EFFORTS: Array<"all" | RecommendationEffort> = ["all", "small", "medium", "large"];
const STATUSES: Array<"all" | RecommendationStatus> = ["all", "open", "in_progress", "completed", "dismissed"];
const SORTS = [
  { id: "priority", label: "Priority" },
  { id: "impact", label: "Impact" },
  { id: "effort", label: "Effort" },
  { id: "affected_pages", label: "Affected pages" },
  { id: "issue_count", label: "Issue count" },
  { id: "status", label: "Status" },
  { id: "category", label: "Category" },
] as const;
const ANALYZER_ORDER = [
  ["seo", "SEO"],
  ["aeo", "AEO"],
  ["uiux", "UI/UX"],
  ["accessibility", "Accessibility"],
  ["performance", "Performance"],
  ["content", "Content"],
  ["structured_data", "Structured Data"],
  ["mobile", "Mobile"],
  ["cro", "CRO"],
  ["trust", "Trust"],
] as const;

function analyzerLabel(value: AnalyzerRunStatus | undefined) {
  if (value === "completed") return "Completed";
  if (value === "failed") return "Failed";
  return "Missing";
}

export function RecommendationsDashboard({ scanId, categoryFilter }: { scanId: string; categoryFilter?: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [payload, setPayload] = useState<RecommendationsListResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [category, setCategory] = useState<(typeof RECOMMENDATION_CATEGORIES)[number]>(
    RECOMMENDATION_CATEGORIES.includes((categoryFilter || "") as (typeof RECOMMENDATION_CATEGORIES)[number])
      ? (categoryFilter as (typeof RECOMMENDATION_CATEGORIES)[number])
      : "All",
  );
  const [priority, setPriority] = useState<(typeof PRIORITIES)[number]>("all");
  const [impact, setImpact] = useState<(typeof IMPACTS)[number]>("all");
  const [effort, setEffort] = useState<(typeof EFFORTS)[number]>("all");
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("all");
  const [sort, setSort] = useState<(typeof SORTS)[number]["id"]>("priority");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const debounceRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getRecommendations(scanId, {
      category: category === "All" ? undefined : category,
      priority: priority === "all" ? undefined : priority,
      impact: impact === "all" ? undefined : impact,
      effort: effort === "all" ? undefined : effort,
      status: status === "all" ? undefined : status,
      search: debouncedSearch.trim() || undefined,
      sort,
      order,
      page,
      page_size: 25,
    })
      .then((result) => {
        if (!cancelled) {
          setPayload(result);
          setLoadError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setLoadError(caught instanceof ScanApiError ? caught.message : "Recommendations are not available.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId, category, priority, impact, effort, status, debouncedSearch, sort, order, page]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const summary = payload?.summary;
  const pagination = payload?.pagination;
  const analyzerStatus = payload?.analyzer_status || {};
  const hasFailedAnalyzer = Object.values(analyzerStatus).includes("failed");
  const categoryMax = useMemo(() => Math.max(1, ...Object.values(summary?.by_category || {}), 0), [summary]);

  return (
    <ScanShell scanId={scanId} current="recommendations">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <ScanStateCard title="Recommendations unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : !scan || running ? (
          <ScanStateCard
            title={scan ? emptyRecommendationsCopy("incomplete").title : "Loading recommendations"}
            body={scan?.current_step ?? emptyRecommendationsCopy("incomplete").body}
          />
        ) : loadError ? (
          <ScanStateCard title="Recommendations are not available." body={loadError} />
        ) : !payload ? (
          <ScanStateCard title="Loading recommendations" body="Fetching implementation guidance from stored findings." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Recommendations</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Recommendations</h1>
              <p className="mt-1 text-sm text-muted-foreground">Prioritized implementation guidance generated from detected issues.</p>
              <div className="mt-3 flex flex-wrap gap-4">
                <Link href={`/scan/${scanId}/action-plan`} className="text-sm underline-offset-2 hover:underline">
                  Open Action Plan
                </Link>
                <Link href={`/scan/${scanId}/report`} className="text-sm underline-offset-2 hover:underline">
                  View report
                </Link>
              </div>
            </section>

            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <SummaryCard label="Open" value={summary?.open ?? 0} />
              <SummaryCard label="High Priority" value={summary?.high_priority ?? 0} tone="high" />
              <SummaryCard label="In Progress" value={summary?.in_progress ?? 0} />
              <SummaryCard label="Completed" value={summary?.completed ?? 0} />
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">By category</h2>
              <ul className="mt-4 space-y-3">
                {RECOMMENDATION_CATEGORIES.filter((item) => item !== "All").map((label) => {
                  const count = summary?.by_category?.[label] ?? 0;
                  const high = summary?.high_priority_by_category?.[label] ?? 0;
                  return (
                    <li key={label}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-foreground">{label}</span>
                        <span className="font-mono text-xs text-muted-foreground">
                          {count} · {high} high priority
                        </span>
                      </div>
                      <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary/80" style={{ width: `${Math.round((count / categoryMax) * 100)}%` }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Analyzer availability</h2>
              <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {ANALYZER_ORDER.map(([id, label]) => {
                  const state = analyzerStatus[id];
                  return (
                    <li key={id} className="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm">
                      <span>{label}</span>
                      <span className={cn("text-xs font-medium", state === "failed" ? "text-critical" : state === "completed" ? "text-pass" : "text-muted-foreground")}>
                        {analyzerLabel(state)}
                      </span>
                    </li>
                  );
                })}
              </ul>
              {hasFailedAnalyzer ? <p className="mt-3 text-sm text-muted-foreground">{emptyRecommendationsCopy("partial").body}</p> : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">Filters</h2>
                  <p className="mt-1 text-sm text-muted-foreground">Default view shows the highest priority first.</p>
                </div>
                <div>
                  <label htmlFor="recommendation-search" className="block text-xs font-medium text-muted-foreground">
                    Search
                  </label>
                  <input
                    id="recommendation-search"
                    value={search}
                    onChange={(event) => {
                      const next = event.target.value.slice(0, 200);
                      setSearch(next);
                      window.clearTimeout(debounceRef.current);
                      debounceRef.current = window.setTimeout(() => {
                        setDebouncedSearch(next);
                        setPage(1);
                      }, 300);
                    }}
                    placeholder="Search title, summary, or URL…"
                    className="mt-1 h-10 w-full max-w-sm rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  />
                </div>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <FilterSelect label="Category" value={category} onChange={(value) => { setCategory(value); setPage(1); }} options={RECOMMENDATION_CATEGORIES.map((item) => ({ id: item, label: item }))} />
                <FilterSelect label="Priority" value={priority} onChange={(value) => { setPriority(value); setPage(1); }} options={PRIORITIES.map((item) => ({ id: item, label: item === "all" ? "All" : titleCase(item) }))} />
                <FilterSelect label="Impact" value={impact} onChange={(value) => { setImpact(value); setPage(1); }} options={IMPACTS.map((item) => ({ id: item, label: item === "all" ? "All" : titleCase(item) }))} />
                <FilterSelect label="Effort" value={effort} onChange={(value) => { setEffort(value); setPage(1); }} options={EFFORTS.map((item) => ({ id: item, label: item === "all" ? "All" : titleCase(item) }))} />
                <FilterSelect label="Status" value={status} onChange={(value) => { setStatus(value); setPage(1); }} options={STATUSES.map((item) => ({ id: item, label: item === "all" ? "All" : statusLabel(item) }))} />
                <div className="grid grid-cols-[1fr_auto] gap-2">
                  <FilterSelect label="Sort" value={sort} onChange={(value) => { setSort(value); setPage(1); }} options={SORTS.map((item) => ({ id: item.id, label: item.label }))} />
                  <button type="button" className="mt-6 h-10 rounded-lg border border-border px-3 text-xs font-medium text-foreground" onClick={() => { setOrder((current) => (current === "desc" ? "asc" : "desc")); setPage(1); }}>
                    {order === "desc" ? "Desc" : "Asc"}
                  </button>
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Recommendations</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {pagination ? `${pagination.total} matching recommendation${pagination.total === 1 ? "" : "s"}` : "No recommendations"}
              </p>
              {payload.items.length === 0 ? (
                <div className="mt-6 rounded-xl border border-dashed border-border bg-muted/30 p-8 text-center">
                  {summary?.total ? (
                    <>
                      <p className="text-sm font-medium text-foreground">{emptyRecommendationsCopy("filters").title}</p>
                      <p className="mt-2 text-sm text-muted-foreground">{emptyRecommendationsCopy("filters").body}</p>
                    </>
                  ) : (
                    <>
                      <p className="text-sm font-medium text-foreground">{emptyRecommendationsCopy("none").title}</p>
                      <p className="mt-2 text-sm text-muted-foreground">{emptyRecommendationsCopy("none").body}</p>
                    </>
                  )}
                </div>
              ) : (
                <ul className="mt-4 space-y-3">
                  {payload.items.map((item) => (
                    <RecommendationRow key={item.id} scanId={scanId} item={item} />
                  ))}
                </ul>
              )}
              {pagination && pagination.pages > 1 ? (
                <div className="mt-5 flex items-center justify-between text-sm">
                  <p className="text-muted-foreground">
                    Page {pagination.page} of {pagination.pages}
                  </p>
                  <div className="flex gap-2">
                    <button type="button" className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40" disabled={pagination.page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
                      Previous
                    </button>
                    <button type="button" className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40" disabled={pagination.page >= pagination.pages} onClick={() => setPage((current) => current + 1)}>
                      Next
                    </button>
                  </div>
                </div>
              ) : null}
            </section>

            <p className="text-xs text-muted-foreground">{payload.methodology || RECOMMENDATION_METHODOLOGY}</p>
          </>
        )}
      </div>
    </ScanShell>
  );
}

function RecommendationRow({ scanId, item }: { scanId: string; item: RecommendationListItem }) {
  return (
    <li className="rounded-xl border border-border bg-muted/30 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link href={`/scan/${scanId}/recommendations/${item.id}`} className="font-medium text-foreground hover:underline">
            {item.title}
          </Link>
          <p className="mt-1 text-sm text-muted-foreground">{item.summary}</p>
        </div>
        <span className="rounded-full border border-border bg-background px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
          {statusLabel(item.status)}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <SourceBadge source={item.category.toLowerCase()} category={item.category} />
        <PriorityBadge value={item.priority} />
        <span className="text-muted-foreground">Impact: {titleCase(item.impact)}</span>
        <span className="text-muted-foreground">Effort: {titleCase(item.effort)}</span>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        {`${item.affected_page_count} ${item.affected_page_count === 1 ? "page" : "pages"} affected · ${item.issue_count} ${item.issue_count === 1 ? "finding" : "findings"}`}
      </p>
      {item.issue_keys.length ? (
        <p className="mt-2 text-xs">
          <Link href={issuesHref(scanId, [], item.issue_keys)} className="text-primary hover:underline">
            View issues
          </Link>
        </p>
      ) : null}
    </li>
  );
}

function SummaryCard({ label, value, tone }: { label: string; value: number; tone?: "high" }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={cn("mt-1 text-3xl font-semibold tracking-tight", tone === "high" ? "text-warn" : "text-foreground")}>{value}</p>
    </div>
  );
}
