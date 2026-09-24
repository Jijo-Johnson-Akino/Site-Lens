"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import {
  getPages,
  ScanApiError,
  type CrawlStatus,
  type PageListItem,
  type PagesListResponse,
} from "@/lib/scan/api";
import {
  crawlStatusLabel,
  httpLabel,
  indexableLabel,
  pageTitle,
  scoreLabel,
} from "@/lib/scan/pages-ui";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const PAGE_TYPES = [
  { id: "all", label: "All" },
  { id: "homepage", label: "Homepage" },
  { id: "article", label: "Article" },
  { id: "product", label: "Product" },
  { id: "service", label: "Service" },
  { id: "contact", label: "Contact" },
  { id: "about", label: "About" },
  { id: "login", label: "Login / Signup" },
  { id: "listing", label: "Listing" },
  { id: "search", label: "Search" },
  { id: "application", label: "Application" },
  { id: "unknown", label: "Unknown" },
] as const;

const CRAWL_STATUSES = [
  { id: "all", label: "All" },
  { id: "crawled", label: "Crawled" },
  { id: "failed", label: "Failed" },
  { id: "skipped", label: "Skipped" },
] as const;

const HTTP_STATUSES = [
  { id: "all", label: "All" },
  { id: "2xx", label: "2xx" },
  { id: "3xx", label: "3xx" },
  { id: "4xx", label: "4xx" },
  { id: "5xx", label: "5xx" },
] as const;

const INDEXABLE = [
  { id: "all", label: "All" },
  { id: "true", label: "Indexable" },
  { id: "false", label: "Noindex" },
  { id: "unknown", label: "Unknown" },
] as const;

const ISSUES = [
  { id: "all", label: "All" },
  { id: "true", label: "Has Issues" },
  { id: "false", label: "No Issues" },
] as const;

const SORTS = [
  { id: "issue_count", label: "Issue count" },
  { id: "url", label: "URL" },
  { id: "title", label: "Title" },
  { id: "page_type", label: "Page type" },
  { id: "http_status", label: "HTTP status" },
  { id: "response_time", label: "Response time" },
  { id: "word_count", label: "Word count" },
  { id: "crawl_status", label: "Crawl status" },
] as const;

export function PagesDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [payload, setPayload] = useState<PagesListResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pageType, setPageType] = useState<(typeof PAGE_TYPES)[number]["id"]>("all");
  const [crawlStatus, setCrawlStatus] = useState<(typeof CRAWL_STATUSES)[number]["id"]>("all");
  const [httpStatus, setHttpStatus] = useState<(typeof HTTP_STATUSES)[number]["id"]>("all");
  const [indexable, setIndexable] = useState<(typeof INDEXABLE)[number]["id"]>("all");
  const [hasIssues, setHasIssues] = useState<(typeof ISSUES)[number]["id"]>("all");
  const [sort, setSort] = useState<(typeof SORTS)[number]["id"]>("issue_count");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [filtersOpen, setFiltersOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput), 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const load = useCallback(async () => {
    if (!scan || scan.status === "failed") {
      return;
    }
    try {
      const result = await getPages(scanId, {
        page_type: pageType === "all" ? undefined : pageType,
        crawl_status: crawlStatus === "all" ? undefined : crawlStatus,
        http_status: httpStatus === "all" ? undefined : httpStatus,
        indexable: indexable === "all" ? undefined : indexable,
        has_issues: hasIssues === "all" ? undefined : hasIssues,
        search: search.trim() || undefined,
        sort,
        order,
        page,
        page_size: 25,
      });
      setPayload(result);
      setLoadError(null);
    } catch (caught) {
      setLoadError(caught instanceof ScanApiError ? caught.message : "Pages are not available.");
    }
  }, [scan, scanId, pageType, crawlStatus, httpStatus, indexable, hasIssues, search, sort, order, page]);

  useEffect(() => {
    void load(); // eslint-disable-line react-hooks/set-state-in-effect -- fetch persisted pages
  }, [load]);

  useEffect(() => {
    setPage(1); // eslint-disable-line react-hooks/set-state-in-effect -- reset page when filters change
  }, [pageType, crawlStatus, httpStatus, indexable, hasIssues, search, sort, order]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const summary = payload?.summary;
  const pagination = payload?.pagination;
  const limits = payload?.limits;
  const maxPages = limits?.max_pages ?? summary?.max_pages;
  const maxDepth = limits?.max_depth ?? summary?.max_depth;
  const filtersActive = pageType !== "all" || crawlStatus !== "all" || httpStatus !== "all" || indexable !== "all" || hasIssues !== "all" || Boolean(search.trim());

  const progressLabel = useMemo(() => {
    if (!summary) {
      return null;
    }
    if (typeof maxPages === "number") {
      return `${summary.discovered} / ${maxPages} pages discovered`;
    }
    return `${summary.discovered} pages discovered`;
  }, [summary, maxPages]);

  return (
    <ScanShell scanId={scanId} current="pages">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        {failed ? (
          <StateCard title="Pages are unavailable because this scan failed." body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : !scan ? (
          <StateCard title="Loading pages" body="Loading scan status…" />
        ) : loadError ? (
          <StateCard title="Pages are not available." body={loadError} />
        ) : running && !payload?.items.length ? (
          <StateCard
            title="Discovering pages..."
            body={progressLabel ?? scan.current_step ?? "SiteLens is collecting internal pages for this scan."}
          />
        ) : !payload ? (
          <PagesSkeleton />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Pages</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Pages Explorer</h1>
              <p className="mt-1 text-sm text-muted-foreground">Inspect every page SiteLens discovered during this scan.</p>
              <p className="mt-3">
                <Link href={`/scan/${scanId}/architecture`} className="text-sm font-medium text-primary hover:underline">
                  View Architecture
                </Link>
              </p>
              {running ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  Discovering pages...{progressLabel ? ` ${progressLabel}` : ""}
                </p>
              ) : null}
              <dl className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Metric label="Discovered" value={summary?.discovered ?? 0} />
                <Metric label="Crawled" value={summary?.crawled ?? 0} />
                <Metric label="Failed" value={summary?.failed ?? 0} />
                <Metric label="Skipped" value={summary?.skipped ?? 0} />
              </dl>
              <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {typeof summary?.internal_pages === "number" ? <Metric label="Internal pages" value={summary.internal_pages} /> : null}
                {typeof summary?.external_links_discovered === "number" ? (
                  <Metric label="External links discovered" value={summary.external_links_discovered} />
                ) : null}
                {typeof summary?.max_depth_reached === "number" ? <Metric label="Maximum crawl depth" value={summary.max_depth_reached} /> : null}
                {typeof maxPages === "number" ? <Metric label="Crawl limit" value={maxPages} /> : null}
              </dl>
              {typeof maxPages === "number" && typeof maxDepth === "number" ? (
                <p className="mt-4 text-sm text-muted-foreground">
                  SiteLens analyzed up to {maxPages} pages with a maximum crawl depth of {maxDepth}.
                </p>
              ) : null}
              {summary?.page_limit_reached ? (
                <p className="mt-2 text-sm text-muted-foreground">
                  Maximum page limit reached. Additional pages may not have been analyzed.
                </p>
              ) : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">Filters</h2>
                  <p className="mt-1 text-sm text-muted-foreground">Search by URL, title, or H1. Filters combine together.</p>
                </div>
                <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center lg:w-auto">
                  <input
                    value={searchInput}
                    onChange={(event) => setSearchInput(event.target.value.slice(0, 200))}
                    placeholder="Search URL, title, or H1…"
                    className="h-10 w-full max-w-sm rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                    aria-label="Search pages"
                  />
                  <button
                    type="button"
                    className="h-10 rounded-lg border border-border px-3 text-sm font-medium lg:hidden"
                    onClick={() => setFiltersOpen((open) => !open)}
                  >
                    {filtersOpen ? "Hide filters" : "Filters"}
                  </button>
                </div>
              </div>
              <div className={cn("mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3", filtersOpen ? "grid" : "hidden lg:grid")}>
                <FilterSelect label="Page Type" value={pageType} onChange={setPageType} options={PAGE_TYPES} />
                <FilterSelect label="Crawl Status" value={crawlStatus} onChange={setCrawlStatus} options={CRAWL_STATUSES} />
                <FilterSelect label="HTTP Status" value={httpStatus} onChange={setHttpStatus} options={HTTP_STATUSES} />
                <FilterSelect label="Indexability" value={indexable} onChange={setIndexable} options={INDEXABLE} />
                <FilterSelect label="Issues" value={hasIssues} onChange={setHasIssues} options={ISSUES} />
                <div className="grid grid-cols-[1fr_auto] gap-2">
                  <FilterSelect label="Sort" value={sort} onChange={setSort} options={SORTS} />
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
                  <h2 className="text-sm font-semibold text-foreground">Pages</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {pagination
                      ? `${pagination.total} matching page${pagination.total === 1 ? "" : "s"}`
                      : "No pages"}
                  </p>
                </div>
              </div>
              {payload.items.length === 0 ? (
                <div className="mt-6 rounded-xl border border-dashed border-border bg-muted/30 p-8 text-center">
                  {filtersActive ? (
                    <>
                      <p className="text-sm font-medium text-foreground">No pages match your filters.</p>
                      <p className="mt-2 text-sm text-muted-foreground">Try a different type, status, or search term.</p>
                    </>
                  ) : running ? (
                    <>
                      <p className="text-sm font-medium text-foreground">Page analysis is still in progress.</p>
                      <p className="mt-2 text-sm text-muted-foreground">{progressLabel ?? "Discovering pages..."}</p>
                    </>
                  ) : (
                    <>
                      <p className="text-sm font-medium text-foreground">No crawled pages are available.</p>
                      <p className="mt-2 text-sm text-muted-foreground">This scan did not persist any crawl records.</p>
                    </>
                  )}
                </div>
              ) : (
                <>
                  <div className="mt-4 hidden overflow-x-auto md:block">
                    <table className="w-full min-w-[860px] text-left text-sm">
                      <thead>
                        <tr className="border-b border-border text-xs text-muted-foreground">
                          <th className="py-2 pr-3 font-medium">Page</th>
                          <th className="py-2 pr-3 font-medium">Type</th>
                          <th className="py-2 pr-3 font-medium">Status</th>
                          <th className="py-2 pr-3 font-medium">HTTP</th>
                          <th className="py-2 pr-3 font-medium">Indexable</th>
                          <th className="py-2 pr-3 font-medium">SEO</th>
                          <th className="py-2 pr-3 font-medium">Performance</th>
                          <th className="py-2 pr-3 font-medium">Content</th>
                          <th className="py-2 font-medium">Issues</th>
                        </tr>
                      </thead>
                      <tbody>
                        {payload.items.map((item) => (
                          <PageRow key={item.id} scanId={scanId} item={item} />
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <ul className="mt-4 space-y-3 md:hidden">
                    {payload.items.map((item) => (
                      <li key={item.id}>
                        <PageCard scanId={scanId} item={item} />
                      </li>
                    ))}
                  </ul>
                </>
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

function PageRow({ scanId, item }: { scanId: string; item: PageListItem }) {
  return (
    <tr className="border-b border-border/70 last:border-0">
      <td className="py-3 pr-3 align-top">
        <Link href={`/scan/${scanId}/pages/${item.id}`} className="font-medium text-foreground hover:underline">
          {pageTitle(item.title)}
        </Link>
        <p className="mt-1 break-all font-mono text-[11px] text-muted-foreground">{item.final_url || item.url}</p>
        <p className="mt-2">
          <Link href={`/scan/${scanId}/architecture?focus=${item.id}`} className="text-xs font-medium text-primary hover:underline">
            View Architecture
          </Link>
        </p>
      </td>
      <td className="py-3 pr-3 align-top text-muted-foreground">{item.page_type_label || item.page_type || "Unknown"}</td>
      <td className="py-3 pr-3 align-top">
        <StatusBadge status={item.crawl_status} />
      </td>
      <td className="py-3 pr-3 align-top">
        <HttpBadge code={item.http_status} />
      </td>
      <td className="py-3 pr-3 align-top">
        <IndexableBadge value={item.indexable} />
      </td>
      <td className="py-3 pr-3 align-top text-muted-foreground">{scoreLabel(item.seo)}</td>
      <td className="py-3 pr-3 align-top text-muted-foreground">{scoreLabel(item.performance)}</td>
      <td className="py-3 pr-3 align-top text-muted-foreground">{scoreLabel(item.content)}</td>
      <td className="py-3 align-top text-muted-foreground">{item.issue_count}</td>
    </tr>
  );
}

function PageCard({ scanId, item }: { scanId: string; item: PageListItem }) {
  return (
    <Link href={`/scan/${scanId}/pages/${item.id}`} className="block rounded-xl border border-border bg-muted/30 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-foreground">{pageTitle(item.title)}</p>
          <p className="mt-1 break-all font-mono text-[11px] text-muted-foreground">{item.final_url || item.url}</p>
        </div>
        <StatusBadge status={item.crawl_status} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
        <div>
          <dt>Type</dt>
          <dd className="text-foreground">{item.page_type_label || item.page_type || "Unknown"}</dd>
        </div>
        <div>
          <dt>HTTP</dt>
          <dd className="text-foreground">{httpLabel(item.http_status)}</dd>
        </div>
        <div>
          <dt>Indexable</dt>
          <dd className="text-foreground">{indexableLabel(item.indexable)}</dd>
        </div>
        <div>
          <dt>Issues</dt>
          <dd className="text-foreground">{item.issue_count}</dd>
        </div>
      </dl>
    </Link>
  );
}

export function StatusBadge({ status }: { status: CrawlStatus | string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium",
        status === "crawled" && "bg-pass/10 text-pass",
        status === "failed" && "bg-critical/10 text-critical",
        status === "skipped" && "bg-muted text-muted-foreground",
        (status === "queued" || status === "crawling" || status === "discovered") && "bg-primary/10 text-primary",
      )}
    >
      {crawlStatusLabel(status)}
    </span>
  );
}

export function HttpBadge({ code }: { code: number | null | undefined }) {
  if (typeof code !== "number") {
    return <span className="text-muted-foreground">—</span>;
  }
  const bucket = Math.floor(code / 100);
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 font-mono text-[11px] font-medium",
        bucket === 2 && "bg-pass/10 text-pass",
        bucket === 3 && "bg-warn/10 text-warn",
        bucket === 4 && "bg-critical/10 text-critical",
        bucket === 5 && "bg-critical/10 text-critical",
        bucket !== 2 && bucket !== 3 && bucket !== 4 && bucket !== 5 && "bg-muted text-muted-foreground",
      )}
    >
      {code}
    </span>
  );
}

export function IndexableBadge({ value }: { value: boolean | null | undefined }) {
  return (
    <span className="inline-flex rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
      {indexableLabel(value)}
    </span>
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
  options: ReadonlyArray<{ id: T; label: string }>;
}) {
  return (
    <label className="block text-sm">
      <span className="text-muted-foreground">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        className="mt-1 h-10 w-full rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
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

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-muted/40 px-4 py-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold tracking-tight text-foreground">{value}</dd>
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

function PagesSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <div className="h-48 animate-pulse rounded-2xl border border-border bg-muted/40" />
      <div className="h-32 animate-pulse rounded-2xl border border-border bg-muted/40" />
      <div className="h-72 animate-pulse rounded-2xl border border-border bg-muted/40" />
    </div>
  );
}
