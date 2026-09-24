"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { FilterSelect } from "@/components/scan/FilterSelect";
import { HelpHint } from "@/components/scan/HelpHint";
import { PriorityBadge, SourceBadge } from "@/components/scan/IssuesDashboard";
import { ScanShell } from "@/components/scan/ScanShell";
import { ScanSkeletonCards, ScanStateCard } from "@/components/scan/ScanStateCard";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  getRecommendations,
  patchRecommendationStatus,
  ScanApiError,
  type RecommendationEffort,
  type RecommendationImpact,
  type RecommendationListItem,
  type RecommendationPriority,
  type RecommendationsListResponse,
  type RecommendationStatus,
} from "@/lib/scan/api";
import {
  ACTION_PLAN_INTRO,
  ACTION_PLAN_SORTS,
  actionIssuesHref,
  analyzerHref,
  bandCounts,
  emptyActionPlanCopy,
  groupActionsByPriority,
  pagesHref,
} from "@/lib/scan/action-plan-ui";
import { RECOMMENDATION_CATEGORIES, RECOMMENDATION_METHODOLOGY, statusLabel, titleCase } from "@/lib/scan/recommendations-ui";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const PRIORITIES: Array<"all" | RecommendationPriority> = ["all", "critical", "high", "medium", "low", "info"];
const IMPACTS: Array<"all" | RecommendationImpact> = ["all", "high", "medium", "low"];
const EFFORTS: Array<"all" | RecommendationEffort> = ["all", "small", "medium", "large"];
const STATUSES: Array<"all" | RecommendationStatus> = ["all", "open", "in_progress", "completed", "dismissed"];

export function ActionPlanDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [payload, setPayload] = useState<RecommendationsListResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [category, setCategory] = useState<(typeof RECOMMENDATION_CATEGORIES)[number]>("All");
  const [priority, setPriority] = useState<(typeof PRIORITIES)[number]>("all");
  const [impact, setImpact] = useState<(typeof IMPACTS)[number]>("all");
  const [effort, setEffort] = useState<(typeof EFFORTS)[number]>("all");
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("all");
  const [sort, setSort] = useState<(typeof ACTION_PLAN_SORTS)[number]["id"]>("priority");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [retryToken, setRetryToken] = useState(0);
  const debounceRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(debounceRef.current);
  }, [search]);

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getRecommendations(scanId, {
      category: category === "All" ? undefined : category,
      priority,
      impact,
      effort,
      status,
      search: debouncedSearch,
      sort,
      order,
      page: 1,
      page_size: 100,
    })
      .then((result) => {
        if (!cancelled) {
          setPayload(result);
          setLoadError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setLoadError(caught instanceof ScanApiError ? caught.message : "Unable to load the Action Plan.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId, category, priority, impact, effort, status, debouncedSearch, sort, order, retryToken]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const summary = payload?.summary;
  const bands = bandCounts(summary);
  const groups = payload ? groupActionsByPriority(payload.items) : [];

  function replaceItem(next: RecommendationListItem) {
    setPayload((current) => {
      if (!current) return current;
      const items = current.items.map((item) => (item.id === next.id ? { ...item, ...next } : item));
      return { ...current, items };
    });
  }

  return (
    <ScanShell scanId={scanId} current="action-plan">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        {failed ? (
          <ScanStateCard
            title="Unable to load the Action Plan."
            body={scan?.error?.message ?? error ?? "This scan did not complete."}
            actionHref="/"
            actionLabel="Start New Scan"
          />
        ) : running || !scan ? (
          <>
            <header>
              <h1 className="text-2xl font-semibold tracking-tight text-foreground">Action Plan</h1>
              <p className="mt-2 text-sm text-muted-foreground">{scan?.current_step ?? "Loading scan status…"}</p>
            </header>
            <ScanSkeletonCards label="Loading Action Plan" />
          </>
        ) : loadError ? (
          <ScanStateCard
            title="Unable to load the Action Plan."
            body={loadError}
            actionLabel="Retry"
            onAction={() => {
              setPayload(null);
              setLoadError(null);
              setRetryToken((current) => current + 1);
            }}
          />
        ) : !payload ? (
          <ScanSkeletonCards label="Loading Action Plan" />
        ) : (
          <>
            <header>
              <h1 className="text-2xl font-semibold tracking-tight text-foreground">Action Plan</h1>
              <p className="mt-2 text-sm text-muted-foreground">{ACTION_PLAN_INTRO}</p>
            </header>

            <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <SummaryCard label="Total Actions" value={summary?.total ?? 0} />
              <SummaryCard label="Open" value={summary?.open ?? 0} />
              <SummaryCard label="In Progress" value={summary?.in_progress ?? 0} />
              <SummaryCard label="Completed" value={summary?.completed ?? 0} />
              <SummaryCard label="Dismissed" value={summary?.dismissed ?? 0} />
            </section>

            <section className="grid gap-3 sm:grid-cols-3">
              <SummaryCard label="High Priority" value={bands.high} tone="high" />
              <SummaryCard label="Medium Priority" value={bands.medium} />
              <SummaryCard label="Low Priority" value={bands.low} />
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <label htmlFor="action-search" className="block text-xs font-medium text-muted-foreground">
                Search
              </label>
              <input
                id="action-search"
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search recommendations..."
                className="mt-1 h-10 w-full max-w-sm rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              />
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <FilterSelect label="Priority" value={priority} onChange={setPriority} options={PRIORITIES.map((item) => ({ id: item, label: item === "all" ? "All" : titleCase(item) }))} />
                <FilterSelect label="Category" value={category} onChange={setCategory} options={RECOMMENDATION_CATEGORIES.map((item) => ({ id: item, label: item }))} />
                <FilterSelect label="Status" value={status} onChange={setStatus} options={STATUSES.map((item) => ({ id: item, label: item === "all" ? "All" : statusLabel(item) }))} />
                <FilterSelect label="Effort" value={effort} onChange={setEffort} options={EFFORTS.map((item) => ({ id: item, label: item === "all" ? "All" : titleCase(item) }))} />
                <FilterSelect label="Impact" value={impact} onChange={setImpact} options={IMPACTS.map((item) => ({ id: item, label: item === "all" ? "All" : titleCase(item) }))} />
                <div className="grid grid-cols-[1fr_auto] gap-2">
                  <FilterSelect label="Sort" value={sort} onChange={setSort} options={ACTION_PLAN_SORTS.map((item) => ({ id: item.id, label: item.label }))} />
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

            {payload.items.length === 0 ? (
              <ScanStateCard
                title={summary?.total ? emptyActionPlanCopy("filters").title : emptyActionPlanCopy("none").title}
                body={summary?.total ? emptyActionPlanCopy("filters").body : emptyActionPlanCopy("none").body}
              />
            ) : (
              groups.map((group) => (
                <section key={group.id} className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
                  <h2 className="text-sm font-semibold text-foreground">
                    {group.label}
                    <span className="ml-2 font-normal text-muted-foreground">{group.items.length}</span>
                  </h2>
                  <ul className="mt-4 space-y-3">
                    {group.items.map((item) => (
                      <ActionCard key={item.id} scanId={scanId} item={item} onUpdated={replaceItem} />
                    ))}
                  </ul>
                </section>
              ))
            )}

            <p className="text-xs text-muted-foreground">{payload.methodology || RECOMMENDATION_METHODOLOGY}</p>
          </>
        )}
      </div>
    </ScanShell>
  );
}

function ActionCard({
  scanId,
  item,
  onUpdated,
}: {
  scanId: string;
  item: RecommendationListItem;
  onUpdated: (item: RecommendationListItem) => void;
}) {
  const [busy, setBusy] = useState<RecommendationStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const steps = item.action_steps || [];

  async function updateStatus(next: RecommendationStatus) {
    setStatusError(null);
    setBusy(next);
    try {
      const result = await patchRecommendationStatus(scanId, item.id, next);
      onUpdated({ ...item, ...result.recommendation, status: result.recommendation.status });
    } catch (caught) {
      setStatusError(caught instanceof ScanApiError ? caught.message : "Unable to update status.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <li className="rounded-xl border border-border bg-muted/30 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link href={`/scan/${scanId}/action-plan/${item.id}`} className="font-medium text-foreground hover:underline">
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
      <dl className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
        <div>
          <dt className="inline">Affected Pages: </dt>
          <dd className="inline text-foreground">{item.affected_page_count}</dd>
        </div>
        <div>
          <dt className="inline">Related Issues: </dt>
          <dd className="inline text-foreground">{item.issue_count}</dd>
        </div>
      </dl>
      {steps.length ? (
        <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-foreground">
          {steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <Link href={actionIssuesHref(scanId, item)} className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3 text-sm")}>
          View Issues
        </Link>
        <Link href={pagesHref(scanId, item.page_ids)} className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3 text-sm")}>
          View Pages
        </Link>
        <Link href={analyzerHref(scanId, item.category)} className={cn(buttonVariants({ variant: "ghost" }), "h-9 px-3 text-sm")}>
          View analysis
        </Link>
        {item.status !== "in_progress" ? (
          <Button type="button" variant="secondary" className="h-9 px-3" disabled={busy !== null} onClick={() => void updateStatus("in_progress")}>
            {busy === "in_progress" ? "Saving…" : "Mark In Progress"}
          </Button>
        ) : null}
        {item.status !== "completed" ? (
          <Button type="button" className="h-9 px-3" disabled={busy !== null} onClick={() => void updateStatus("completed")}>
            {busy === "completed" ? "Saving…" : "Mark Completed"}
          </Button>
        ) : null}
        {item.status !== "dismissed" ? (
          <Button type="button" variant="ghost" className="h-9 px-3" disabled={busy !== null} onClick={() => void updateStatus("dismissed")}>
            {busy === "dismissed" ? "Saving…" : "Dismiss"}
          </Button>
        ) : null}
      </div>
      {statusError ? (
        <p className="mt-2 text-sm text-critical" role="alert">
          {statusError}
        </p>
      ) : null}
    </li>
  );
}

function SummaryCard({ label, value, tone }: { label: string; value: number; tone?: "high" }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <p className="text-sm text-muted-foreground">
        {label === "High Priority" ? (
          <HelpHint label={label}>Includes critical and high priority recommendations from this scan.</HelpHint>
        ) : (
          label
        )}
      </p>
      <p className={cn("mt-1 text-3xl font-semibold tracking-tight", tone === "high" ? "text-warn" : "text-foreground")}>{value}</p>
    </div>
  );
}
