"use client";

import { useEffect, useMemo, useState } from "react";

import { ArchitectureDetail } from "@/components/scan/ArchitectureDetail";
import { ArchitectureGraph } from "@/components/scan/ArchitectureGraph";
import { ScanShell } from "@/components/scan/ScanShell";
import {
  getArchitecture,
  getArchitectureLinks,
  getArchitecturePage,
  ScanApiError,
  type ArchitectureLinkRow,
  type ArchitectureNode,
  type ArchitecturePageResponse,
  type ArchitectureResponse,
} from "@/lib/scan/api";
import { crawlDepthLabel, graphLimitMessage, nodeHeading } from "@/lib/scan/architecture-ui";
import { crawlStatusLabel, pageTitle } from "@/lib/scan/pages-ui";
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

const DEPTHS = [
  { id: "all", label: "All" },
  { id: "0", label: "Depth 0" },
  { id: "1", label: "Depth 1" },
  { id: "2", label: "Depth 2" },
  { id: "3", label: "Depth 3" },
] as const;

const ISSUES = [
  { id: "all", label: "All" },
  { id: "true", label: "Has issues" },
  { id: "false", label: "No issues" },
] as const;

const ORPHANS = [
  { id: "all", label: "All" },
  { id: "true", label: "Potential orphan" },
  { id: "false", label: "Has inbound links" },
] as const;

const TERMINALS = [
  { id: "all", label: "All" },
  { id: "true", label: "Terminal page" },
  { id: "false", label: "Not terminal" },
] as const;

const SORTS = [
  { id: "depth", label: "Crawl depth" },
  { id: "inbound", label: "Inbound links" },
  { id: "outbound", label: "Outbound links" },
  { id: "issue_count", label: "Issue count" },
  { id: "url", label: "URL" },
] as const;

export function ArchitectureDashboard({ scanId, focusPageId }: { scanId: string; focusPageId?: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [payload, setPayload] = useState<ArchitectureResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [view, setView] = useState<"graph" | "table">("graph");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [pageType, setPageType] = useState("all");
  const [crawlStatus, setCrawlStatus] = useState("all");
  const [depth, setDepth] = useState("all");
  const [hasIssues, setHasIssues] = useState("all");
  const [orphan, setOrphan] = useState("all");
  const [terminal, setTerminal] = useState("all");
  const [sort, setSort] = useState("depth");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(focusPageId || null);
  const [detail, setDetail] = useState<ArchitecturePageResponse | null>(null);
  const [links, setLinks] = useState<ArchitectureLinkRow[]>([]);
  const [linksPage, setLinksPage] = useState(1);
  const [linksSearch, setLinksSearch] = useState("");
  const [linksTotalPages, setLinksTotalPages] = useState(1);
  const [filtersOpen, setFiltersOpen] = useState(false);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 250);
    return () => window.clearTimeout(handle);
  }, [searchInput]);

  useEffect(() => {
    if (!scan || scan.status === "failed") {
      return;
    }
    let cancelled = false;
    getArchitecture(scanId, {
      search: search || undefined,
      page,
      page_size: 25,
      page_type: pageType,
      crawl_status: crawlStatus,
      depth,
      has_issues: hasIssues,
      orphan,
      terminal,
      sort,
      order,
      focus: focusPageId || undefined,
    })
      .then((result) => {
        if (!cancelled) {
          setPayload(result);
          setLoadError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setLoadError(caught instanceof ScanApiError ? caught.message : "Architecture is not available.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan, scanId, search, page, pageType, crawlStatus, depth, hasIssues, orphan, terminal, sort, order, focusPageId]);

  useEffect(() => {
    if (!scan || scan.status === "failed" || !selectedId) {
      return;
    }
    let cancelled = false;
    getArchitecturePage(scanId, selectedId)
      .then((result) => {
        if (!cancelled) {
          setDetail(result);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDetail(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan, scanId, selectedId]);

  useEffect(() => {
    if (!scan || scan.status === "failed") {
      return;
    }
    let cancelled = false;
    getArchitectureLinks(scanId, { search: linksSearch || undefined, page: linksPage, page_size: 25 })
      .then((result) => {
        if (!cancelled) {
          setLinks(result.items);
          setLinksTotalPages(result.pagination.pages);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLinks([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan, scanId, linksSearch, linksPage]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const summary = payload?.summary;
  const pagination = payload?.pagination;
  const graphMessage = payload ? graphLimitMessage(payload.graph.shown, payload.graph.matching, payload.graph.limited) : null;
  const searchHits = useMemo(() => {
    const needle = searchInput.trim().toLowerCase();
    if (!needle || !payload) {
      return [];
    }
    const pool = [...payload.items, ...payload.nodes];
    const seen = new Set<string>();
    const hits: ArchitectureNode[] = [];
    for (const item of pool) {
      if (seen.has(item.id)) {
        continue;
      }
      const blob = `${item.title || ""} ${item.h1 || ""} ${item.url} ${item.normalized_url}`.toLowerCase();
      if (!blob.includes(needle)) {
        continue;
      }
      seen.add(item.id);
      hits.push(item);
      if (hits.length >= 8) {
        break;
      }
    }
    return hits;
  }, [payload, searchInput]);
  const depthMax = Math.max(1, ...(payload?.depth_distribution.map((row) => row.page_count) || [0]));
  const typeMax = Math.max(1, ...(payload?.page_type_distribution.map((row) => row.page_count) || [0]));

  return (
    <ScanShell scanId={scanId} current="architecture">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        {failed ? (
          <StateCard title="Architecture data is unavailable for this scan." body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : !scan ? (
          <StateCard title="Loading architecture" body="Loading scan status…" />
        ) : loadError ? (
          <StateCard title="Architecture data is unavailable for this scan." body={loadError} />
        ) : running && !payload?.nodes.length && !payload?.items.length ? (
          <StateCard title="Collecting architecture…" body="Internal pages and links are still being observed for this scan." />
        ) : !payload ? (
          <div className="h-72 animate-pulse rounded-2xl border border-border bg-muted/40" aria-busy="true" />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Website Architecture</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Website Architecture</h1>
              <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
                Observed pages and internal links from this SiteLens crawl. This is a visualization of crawl relationships, not the site&apos;s visual design.
              </p>
              <dl className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Metric label="Pages" value={summary?.page_count ?? 0} />
                <Metric label="Internal links" value={summary?.internal_link_count ?? 0} />
                {typeof summary?.max_crawl_depth === "number" ? <Metric label="Max crawl depth" value={summary.max_crawl_depth} /> : null}
                {typeof summary?.average_crawl_depth === "number" ? (
                  <Metric label="Average crawl depth" value={summary.average_crawl_depth} />
                ) : null}
                <Metric
                  label="Pages without inbound links"
                  value={summary?.potential_orphan_count ?? 0}
                  hint="A crawled page with no inbound internal links found in the analyzed internal-link graph."
                />
                <Metric label="Pages without outbound links" value={summary?.no_outbound_count ?? summary?.dead_end_count ?? 0} />
                {typeof summary?.external_links_discovered === "number" ? (
                  <Metric label="External links discovered" value={summary.external_links_discovered} />
                ) : null}
              </dl>
              {payload.insights.length ? (
                <ul className="mt-5 space-y-1 text-sm text-muted-foreground">
                  {payload.insights.map((item) => (
                    <li key={item.id}>{item.text}</li>
                  ))}
                </ul>
              ) : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">Search and filters</h2>
                  <p className="mt-1 text-sm text-muted-foreground">Search by URL, title, or H1. Filters apply to the graph and table.</p>
                </div>
                <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center lg:w-auto">
                  <div className="relative w-full max-w-sm">
                    <input
                      value={searchInput}
                      onChange={(event) => setSearchInput(event.target.value.slice(0, 200))}
                      placeholder="Search URL, title, or H1…"
                      className="h-10 w-full rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                      aria-label="Search architecture pages"
                    />
                    {searchHits.length ? (
                      <ul className="absolute z-20 mt-1 w-full rounded-lg border border-border bg-card p-1 shadow-sm">
                        {searchHits.map((item) => (
                          <li key={item.id}>
                            <button
                              type="button"
                              className="w-full rounded-md px-3 py-2 text-left text-sm hover:bg-muted/40"
                              onClick={() => {
                                setSelectedId(item.id);
                                setView("graph");
                              }}
                            >
                              <span className="block font-medium">{nodeHeading(item)}</span>
                              <span className="block font-mono text-[11px] text-muted-foreground">{item.path}</span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                  <div className="flex rounded-lg border border-border p-1">
                    <button
                      type="button"
                      className={cn("rounded-md px-3 py-1.5 text-sm", view === "graph" && "bg-muted font-medium")}
                      onClick={() => setView("graph")}
                    >
                      Graph view
                    </button>
                    <button
                      type="button"
                      className={cn("rounded-md px-3 py-1.5 text-sm", view === "table" && "bg-muted font-medium")}
                      onClick={() => setView("table")}
                    >
                      Table view
                    </button>
                  </div>
                  <button type="button" className="h-10 rounded-lg border border-border px-3 text-sm lg:hidden" onClick={() => setFiltersOpen((open) => !open)}>
                    {filtersOpen ? "Hide filters" : "Filters"}
                  </button>
                </div>
              </div>
              <div className={cn("mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6", filtersOpen ? "grid" : "hidden lg:grid")}>
                <FilterSelect label="Crawl depth" value={depth} onChange={(value) => { setDepth(value); setPage(1); }} options={DEPTHS} />
                <FilterSelect label="Page type" value={pageType} onChange={(value) => { setPageType(value); setPage(1); }} options={PAGE_TYPES} />
                <FilterSelect label="Crawl status" value={crawlStatus} onChange={(value) => { setCrawlStatus(value); setPage(1); }} options={CRAWL_STATUSES} />
                <FilterSelect label="Issues" value={hasIssues} onChange={(value) => { setHasIssues(value); setPage(1); }} options={ISSUES} />
                <FilterSelect label="Potential orphan" value={orphan} onChange={(value) => { setOrphan(value); setPage(1); }} options={ORPHANS} />
                <FilterSelect label="Terminal page" value={terminal} onChange={(value) => { setTerminal(value); setPage(1); }} options={TERMINALS} />
                <div className="grid grid-cols-[1fr_auto] gap-2">
                  <FilterSelect label="Sort" value={sort} onChange={(value) => { setSort(value); setPage(1); }} options={SORTS} />
                  <button type="button" className="mt-6 h-10 rounded-lg border border-border px-3 text-xs" onClick={() => { setOrder((current) => (current === "asc" ? "desc" : "asc")); setPage(1); }}>
                    {order === "asc" ? "Asc" : "Desc"}
                  </button>
                </div>
              </div>
            </section>

            <div className={cn("grid gap-6", selectedId ? "xl:grid-cols-[minmax(0,1fr)_22rem]" : "")}>
              <div className="flex min-w-0 flex-col gap-6">
                {view === "graph" ? (
                  <section className="hidden rounded-2xl border border-border bg-card p-4 shadow-sm lg:block sm:p-6">
                    <div className="mb-3 flex items-end justify-between gap-3">
                      <div>
                        <h2 className="text-sm font-semibold text-foreground">Internal-link graph</h2>
                        <p className="mt-1 text-sm text-muted-foreground">Nodes are pages. Edges are internal links observed during the crawl.</p>
                      </div>
                    </div>
                    {graphMessage ? <p className="mb-3 text-sm text-muted-foreground">{graphMessage}</p> : null}
                    {payload.nodes.length ? (
                      <ArchitectureGraph nodes={payload.nodes} edges={payload.edges} selectedId={selectedId} onSelect={setSelectedId} />
                    ) : (
                      <p className="rounded-xl border border-dashed border-border bg-muted/30 p-8 text-sm text-muted-foreground">No pages match the current filters.</p>
                    )}
                  </section>
                ) : null}

                <section className={cn("rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8", view === "graph" ? "lg:hidden" : "")}>
                  <h2 className="text-sm font-semibold text-foreground">{view === "table" ? "Architecture table" : "Pages"}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {pagination ? `${pagination.total} matching page${pagination.total === 1 ? "" : "s"}` : "No pages"}
                  </p>
                  {payload.items.length === 0 ? (
                    <p className="mt-6 rounded-xl border border-dashed border-border bg-muted/30 p-8 text-sm text-muted-foreground">No pages match the current filters.</p>
                  ) : (
                    <div className="mt-4 overflow-x-auto">
                      <table className="w-full min-w-[720px] text-left text-sm">
                        <thead>
                          <tr className="border-b border-border text-xs text-muted-foreground">
                            <th className="pb-2 pr-3 font-medium">Page</th>
                            <th className="pb-2 pr-3 font-medium">Type</th>
                            <th className="pb-2 pr-3 font-medium">Crawl depth</th>
                            <th className="pb-2 pr-3 font-medium">Inbound</th>
                            <th className="pb-2 pr-3 font-medium">Outbound</th>
                            <th className="pb-2 pr-3 font-medium">Issues</th>
                            <th className="pb-2 font-medium">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {payload.items.map((item) => (
                            <tr key={item.id} className={cn("border-b border-border/70 last:border-0", selectedId === item.id && "bg-muted/40")}>
                              <td className="py-3 pr-3 align-top">
                                <button type="button" className="text-left font-medium text-foreground hover:underline" onClick={() => setSelectedId(item.id)}>
                                  {nodeHeading(item)}
                                </button>
                                <p className="mt-1 break-all font-mono text-[11px] text-muted-foreground">{item.path}</p>
                              </td>
                              <td className="py-3 pr-3 align-top text-muted-foreground">{item.page_type_label || item.page_type || "Unknown"}</td>
                              <td className="py-3 pr-3 align-top text-muted-foreground">{crawlDepthLabel(item.depth)}</td>
                              <td className="py-3 pr-3 align-top">{item.inbound_link_count}</td>
                              <td className="py-3 pr-3 align-top">{item.outbound_link_count}</td>
                              <td className="py-3 pr-3 align-top">{item.issue_count}</td>
                              <td className="py-3 align-top text-muted-foreground">{crawlStatusLabel(item.crawl_status)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
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
              </div>
              {detail && selectedId ? (
                <div className="min-w-0">
                  <ArchitectureDetail scanId={scanId} detail={detail} onSelectPage={setSelectedId} />
                </div>
              ) : null}
            </div>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Crawl depth distribution</h2>
              <p className="mt-1 text-sm text-muted-foreground">Crawl depth is discovery distance from the seed URL, not URL path depth.</p>
              <ul className="mt-4 space-y-2">
                {(payload.depth_distribution || []).map((row) => (
                  <li key={row.depth} className="grid grid-cols-[7rem_1fr_3rem] items-center gap-3 text-sm">
                    <span className="text-muted-foreground">{crawlDepthLabel(row.depth)}</span>
                    <span className="h-2 overflow-hidden rounded-full bg-muted">
                      <span className="block h-full rounded-full bg-primary/70" style={{ width: `${Math.max(6, (row.page_count / depthMax) * 100)}%` }} />
                    </span>
                    <span className="text-right font-medium">{row.page_count}</span>
                  </li>
                ))}
              </ul>
              {payload.limits?.max_depth != null && payload.notes.some((note) => note.includes("beyond configured crawl depth")) ? (
                <p className="mt-3 text-sm text-muted-foreground">Pages beyond configured crawl depth were not analyzed.</p>
              ) : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Page type distribution</h2>
              <ul className="mt-4 space-y-2">
                {(payload.page_type_distribution || []).map((row) => (
                  <li key={row.page_type} className="grid grid-cols-[8rem_1fr_3rem] items-center gap-3 text-sm">
                    <span className="text-muted-foreground">{row.label}</span>
                    <span className="h-2 overflow-hidden rounded-full bg-muted">
                      <span className="block h-full rounded-full bg-navy/40" style={{ width: `${Math.max(6, (row.page_count / typeMax) * 100)}%` }} />
                    </span>
                    <span className="text-right font-medium">{row.page_count}</span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">URL Path Structure</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {payload.url_path_structure.note || "URL path grouping is not a claim of true website hierarchy."}
              </p>
              <ul className="mt-4 space-y-1 font-mono text-sm">
                {(payload.url_path_structure.groups || []).map((row) => (
                  <li key={row.path} className="flex justify-between gap-3">
                    <span style={{ paddingLeft: `${row.url_path_depth * 12}px` }}>{row.path}</span>
                    <span className="text-muted-foreground">{row.page_count}</span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">Internal links</h2>
                  <p className="mt-1 text-sm text-muted-foreground">Source page, anchor text, and destination from observed crawl links.</p>
                </div>
                <input
                  value={linksSearch}
                  onChange={(event) => {
                    setLinksSearch(event.target.value.slice(0, 200));
                    setLinksPage(1);
                  }}
                  placeholder="Search links…"
                  className="h-10 w-full max-w-xs rounded-lg border border-input bg-transparent px-3 text-sm"
                  aria-label="Search internal links"
                />
              </div>
              {links.length === 0 ? (
                <p className="mt-6 text-sm text-muted-foreground">No internal links match this search.</p>
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-border text-xs text-muted-foreground">
                        <th className="pb-2 pr-3 font-medium">Source page</th>
                        <th className="pb-2 pr-3 font-medium">Anchor text</th>
                        <th className="pb-2 pr-3 font-medium">Destination page</th>
                        <th className="pb-2 font-medium">Destination type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {links.map((item) => (
                        <tr key={item.id} className="border-b border-border/70 last:border-0">
                          <td className="py-3 pr-3 align-top">
                            <button type="button" className="text-left font-medium hover:underline" onClick={() => setSelectedId(item.source_page_id)}>
                              {pageTitle(item.source_title)}
                            </button>
                            <p className="mt-1 font-mono text-[11px] text-muted-foreground">{item.source_path}</p>
                          </td>
                          <td className="py-3 pr-3 align-top text-muted-foreground">{item.anchor_text ? `“${item.anchor_text}”` : "—"}</td>
                          <td className="py-3 pr-3 align-top">
                            <button type="button" className="text-left font-medium hover:underline" onClick={() => setSelectedId(item.destination_page_id)}>
                              {pageTitle(item.destination_title)}
                            </button>
                            <p className="mt-1 font-mono text-[11px] text-muted-foreground">{item.destination_path}</p>
                          </td>
                          <td className="py-3 align-top text-muted-foreground">{item.destination_type_label || item.destination_type || "Unknown"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {linksTotalPages > 1 ? (
                <div className="mt-5 flex justify-end gap-2 text-sm">
                  <button type="button" className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40" disabled={linksPage <= 1} onClick={() => setLinksPage((current) => Math.max(1, current - 1))}>
                    Previous
                  </button>
                  <button type="button" className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40" disabled={linksPage >= linksTotalPages} onClick={() => setLinksPage((current) => current + 1)}>
                    Next
                  </button>
                </div>
              ) : null}
            </section>

            <section className="rounded-2xl border border-border bg-muted/30 p-5 text-sm text-muted-foreground">
              {(payload.notes || []).map((note) => (
                <p key={note} className="mt-2 first:mt-0">
                  {note}
                </p>
              ))}
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
  value: T | string;
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

function Metric({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="rounded-xl border border-border bg-muted/40 px-4 py-3">
      <dt className="text-xs text-muted-foreground" title={hint}>
        {label}
      </dt>
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
