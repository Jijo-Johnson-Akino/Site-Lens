"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { IssueCard } from "@/components/scan/IssueCard";
import { captureInProgress } from "@/components/scan/IssueEvidence";
import { ScanShell } from "@/components/scan/ScanShell";
import {
  getIssues,
  ScanApiError,
  type AnalyzerRunStatus,
  type IssuePriority,
  type IssuesListResponse,
  type SeoSeverity,
} from "@/lib/scan/api";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const CATEGORIES = ["All", "SEO", "AEO", "UI/UX", "Accessibility", "Performance", "Content", "Structured Data", "Mobile", "CRO", "Trust"] as const;
const SEVERITIES: Array<"all" | SeoSeverity> = ["all", "critical", "high", "medium", "low", "info"];
const PRIORITIES: Array<"all" | IssuePriority> = ["all", "critical", "high", "medium", "low"];
const STATUSES = ["all", "open", "resolved", "ignored"] as const;
const SOURCES = [
  { id: "all", label: "All analyzers" },
  { id: "seo", label: "SEO" },
  { id: "aeo", label: "AEO" },
  { id: "uiux", label: "UI/UX" },
  { id: "accessibility", label: "Accessibility" },
  { id: "performance", label: "Performance" },
  { id: "content", label: "Content" },
  { id: "structured_data", label: "Structured Data" },
  { id: "mobile", label: "Mobile" },
  { id: "cro", label: "CRO" },
  { id: "trust", label: "Trust" },
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
const SORTS = [
  { id: "priority", label: "Priority" },
  { id: "severity", label: "Severity" },
  { id: "category", label: "Category" },
  { id: "affected_pages", label: "Affected pages" },
  { id: "affected_elements", label: "Affected elements" },
  { id: "created_at", label: "Created at" },
] as const;

function statusLabel(value: AnalyzerRunStatus | undefined) {
  if (value === "completed") return "Completed";
  if (value === "failed") return "Failed";
  return "Missing";
}

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function IssuesDashboard({ scanId, pageUrl, issueKey, issueIds, categoryFilter }: { scanId: string; pageUrl?: string; issueKey?: string; issueIds?: string; categoryFilter?: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [payload, setPayload] = useState<IssuesListResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]>(
    CATEGORIES.includes((categoryFilter || "") as (typeof CATEGORIES)[number])
      ? (categoryFilter as (typeof CATEGORIES)[number])
      : "All",
  );
  const [severity, setSeverity] = useState<(typeof SEVERITIES)[number]>("all");
  const [priority, setPriority] = useState<(typeof PRIORITIES)[number]>("all");
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("open");
  const [source, setSource] = useState<(typeof SOURCES)[number]["id"]>("all");
  const [sort, setSort] = useState<(typeof SORTS)[number]["id"]>("priority");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageFilter, setPageFilter] = useState(pageUrl || "");

  const load = useCallback(async () => {
    if (scan?.status !== "completed") {
      return;
    }
    try {
      const result = await getIssues(scanId, {
        category: category === "All" ? undefined : category,
        severity: severity === "all" ? undefined : severity,
        priority: priority === "all" ? undefined : priority,
        status: status === "all" ? undefined : status,
        source: source === "all" ? undefined : source,
        search: search.trim() || undefined,
        sort,
        order,
        page,
        page_size: 25,
        page_url: pageFilter || undefined,
        issue_key: issueKey || undefined,
        issue_ids: issueIds || undefined,
      });
      setPayload(result);
      setLoadError(null);
    } catch (caught) {
      setLoadError(caught instanceof ScanApiError ? caught.message : "Issues are not available.");
    }
  }, [scan?.status, scanId, category, severity, priority, status, source, search, sort, order, page, pageFilter, issueKey, issueIds]);

  useEffect(() => {
    void load(); // eslint-disable-line react-hooks/set-state-in-effect -- fetch persisted issues
  }, [load]);

  useEffect(() => {
    if (!captureInProgress(payload?.screenshot_capture?.status)) {
      return;
    }
    const timer = window.setTimeout(() => {
      void load();
    }, 2000);
    return () => window.clearTimeout(timer);
  }, [load, payload?.screenshot_capture?.status]);

  useEffect(() => {
    setPage(1); // eslint-disable-line react-hooks/set-state-in-effect -- reset page when filters change
  }, [category, severity, priority, status, source, search, sort, order, pageFilter]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const summary = payload?.summary;
  const pagination = payload?.pagination;
  const analyzerStatus = payload?.analyzer_status || {};
  const categoryMax = useMemo(() => {
    const values = Object.values(summary?.by_category || {});
    return Math.max(1, ...values, 0);
  }, [summary]);
  const priorityMax = useMemo(() => {
    const values = Object.values(summary?.by_priority || {});
    return Math.max(1, ...values, 0);
  }, [summary]);

  return (
    <ScanShell scanId={scanId} current="issues">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="Issues unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : !scan || running ? (
          <StateCard title={scan ? "Aggregating Issues" : "Loading issues"} body={scan?.current_step ?? "Loading scan status…"} />
        ) : loadError ? (
          <StateCard title="Issues are not available." body={loadError} />
        ) : !payload ? (
          <StateCard title="Loading issues" body="Fetching aggregated findings from completed analyzers." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Issues</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Issues</h1>
              <p className="mt-1 text-sm text-muted-foreground">All detected website issues across SiteLens analyses.</p>
              {pageFilter ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  Showing issues associated with {pageFilter}.{" "}
                  <button type="button" className="font-medium text-primary hover:underline" onClick={() => { setPageFilter(""); setPage(1); }}>
                    Clear page filter
                  </button>
                </p>
              ) : null}
              {issueKey || issueIds ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  Showing issues that support a recommendation.
                </p>
              ) : null}
              {payload.truncated ? (
                <p className="mt-3 text-sm text-warn">Some findings were truncated to keep the issues list within configured limits.</p>
              ) : null}
              {payload.screenshot_capture?.note ? (
                <p className="mt-3 text-sm text-muted-foreground">{payload.screenshot_capture.note}</p>
              ) : null}
              <dl className="mt-6 grid gap-3 sm:grid-cols-5">
                <Metric label="Total Issues" value={summary?.total ?? 0} hint={occurrenceHint(summary)} />
                <Metric label="Critical" value={summary?.critical ?? 0} tone="critical" />
                <Metric label="High" value={summary?.high ?? 0} tone="high" />
                <Metric label="Medium" value={summary?.medium ?? 0} />
                <Metric label="Low" value={summary?.low ?? 0} />
              </dl>
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <h2 className="text-sm font-semibold text-foreground">Issue distribution</h2>
                <ul className="mt-4 space-y-3">
                  {CATEGORIES.filter((item) => item !== "All").map((label) => {
                    const count = summary?.by_category?.[label] ?? 0;
                    return (
                      <li key={label}>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-foreground">{label}</span>
                          <span className="font-mono text-xs text-muted-foreground">{count}</span>
                        </div>
                        <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
                          <div className="h-full rounded-full bg-primary/80" style={{ width: `${Math.round((count / categoryMax) * 100)}%` }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
              <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <h2 className="text-sm font-semibold text-foreground">Priority distribution</h2>
                <ul className="mt-4 space-y-3">
                  {PRIORITIES.filter((item) => item !== "all").map((label) => {
                    const count = summary?.by_priority?.[label] ?? 0;
                    return (
                      <li key={label}>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-foreground">{titleCase(label)}</span>
                          <span className="font-mono text-xs text-muted-foreground">{count}</span>
                        </div>
                        <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
                          <div className={cn("h-full rounded-full", barTone(label))} style={{ width: `${Math.round((count / priorityMax) * 100)}%` }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
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
                        {statusLabel(state)}
                      </span>
                    </li>
                  );
                })}
              </ul>
              {Object.values(analyzerStatus).includes("failed") ? (
                <p className="mt-3 text-sm text-muted-foreground">Failed analyzers are not assumed to have zero issues.</p>
              ) : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">Filters</h2>
                  <p className="mt-1 text-sm text-muted-foreground">Default view shows open fail and warning findings.</p>
                </div>
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value.slice(0, 200))}
                  placeholder="Search issues…"
                  className="h-10 w-full max-w-sm rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                />
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <FilterSelect label="Category" value={category} onChange={setCategory} options={CATEGORIES.map((item) => ({ id: item, label: item }))} />
                <FilterSelect label="Severity" value={severity} onChange={setSeverity} options={SEVERITIES.map((item) => ({ id: item, label: item === "all" ? "All" : titleCase(item) }))} />
                <FilterSelect label="Priority" value={priority} onChange={setPriority} options={PRIORITIES.map((item) => ({ id: item, label: item === "all" ? "All" : titleCase(item) }))} />
                <FilterSelect label="Status" value={status} onChange={setStatus} options={STATUSES.map((item) => ({ id: item, label: item === "all" ? "All" : titleCase(item) }))} />
                <FilterSelect label="Source" value={source} onChange={setSource} options={SOURCES.map((item) => ({ id: item.id, label: item.label }))} />
                <div className="grid grid-cols-[1fr_auto] gap-2">
                  <FilterSelect label="Sort" value={sort} onChange={setSort} options={SORTS.map((item) => ({ id: item.id, label: item.label }))} />
                  <button
                    type="button"
                    className="mt-6 h-10 rounded-lg border border-border px-3 text-xs font-medium text-foreground"
                    onClick={() => setOrder((current) => (current === "desc" ? "asc" : "desc"))}
                  >
                    {order === "desc" ? "Desc" : "Asc"}
                  </button>
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex items-end justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">Issues</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {pagination
                      ? `${pagination.total} matching issue type${pagination.total === 1 ? "" : "s"}`
                      : "No issues"}
                  </p>
                </div>
              </div>
              {payload.items.length === 0 ? (
                <div className="mt-6 rounded-xl border border-dashed border-border bg-muted/30 p-8 text-center">
                  {summary?.total ? (
                    <>
                      <p className="text-sm font-medium text-foreground">No issues match the current filters.</p>
                      <p className="mt-2 text-sm text-muted-foreground">Try a different category, source, or search term.</p>
                    </>
                  ) : (
                    <>
                      <p className="text-sm font-medium text-foreground">No issues were detected in the available analysis.</p>
                      <p className="mt-2 text-sm text-muted-foreground">Completed analyzers returned no actionable findings for this scan.</p>
                    </>
                  )}
                </div>
              ) : (
                <div className="mt-4 grid gap-4">
                  {payload.items.map((item) => (
                    <IssueCard
                      key={item.issue_id}
                      compact
                      capturing={captureInProgress(payload.screenshot_capture?.status)}
                      issue={{
                        ...item,
                        href: `/scan/${scanId}/issues/${item.issue_id}`,
                      }}
                    />
                  ))}
                </div>
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
          </>
        )}
      </div>
    </ScanShell>
  );
}

function FilterSelect<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: Array<{ id: T; label: string }>;
}) {
  return (
    <label className="block text-xs font-medium text-muted-foreground">
      {label}
      <select
        className="mt-1 h-10 w-full rounded-lg border border-input bg-transparent px-2 text-sm text-foreground"
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
      >
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function Metric({ label, value, hint, tone }: { label: string; value: number; hint?: string; tone?: "critical" | "high" }) {
  return (
    <div className="rounded-xl border border-border bg-muted/40 p-4">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("mt-1 text-2xl font-semibold", tone === "critical" ? "text-critical" : "text-foreground")}>{value}</dd>
      {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

function occurrenceHint(summary?: { issue_types?: number; occurrences?: number; by_page?: Record<string, number> }) {
  if (!summary || summary.issue_types == null) {
    return undefined;
  }
  const types = summary.issue_types;
  const pages = Object.keys(summary.by_page || {}).length;
  const occurrences = summary.occurrences ?? types;
  if (pages > 1) {
    return `${types} issue type${types === 1 ? "" : "s"} affecting ${pages} pages`;
  }
  if (occurrences !== types) {
    return `${types} issue type${types === 1 ? "" : "s"} · ${occurrences} occurrence${occurrences === 1 ? "" : "s"}`;
  }
  return `${types} issue type${types === 1 ? "" : "s"}`;
}

function barTone(priority: string) {
  if (priority === "critical") return "bg-critical";
  if (priority === "high") return "bg-warn";
  if (priority === "medium") return "bg-foreground/40";
  return "bg-foreground/20";
}

export function PriorityBadge({ value }: { value: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold tracking-wide uppercase",
        value === "critical" && "bg-critical/10 text-critical",
        value === "high" && "bg-warn/15 text-foreground",
        value === "medium" && "bg-muted text-foreground",
        value === "low" && "bg-muted text-muted-foreground",
      )}
    >
      {value}
    </span>
  );
}

export function SeverityBadge({ value }: { value: string }) {
  return (
    <span className={cn("text-sm", value === "critical" || value === "high" ? "text-critical" : "text-foreground")}>
      {titleCase(value)}
    </span>
  );
}

export function SourceBadge({ source, category }: { source: string; category?: string }) {
  return (
    <span className="inline-flex rounded-full border border-border bg-muted/60 px-2 py-0.5 text-[11px] font-medium text-foreground">
      {category || titleCase(source)}
    </span>
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
