"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import { buttonVariants } from "@/components/ui/button";
import {
  addCompetitor,
  deleteCompetitor,
  getCompetitorComparison,
  getCompetitors,
  getPageComparison,
  getPages,
  rescanCompetitor,
  ScanApiError,
  type ComparisonCell,
  type ComparisonResponse,
  type CompetitorCard,
  type CompetitorListResponse,
  type PageComparisonResponse,
  type PageListItem,
} from "@/lib/scan/api";
import {
  barWidth,
  COMPETITOR_LIMITATIONS,
  COMPETITOR_METHODOLOGY,
  competitorStatusLabel,
  displayCell,
  emptyCompetitorsCopy,
  formatTimestamp,
} from "@/lib/scan/competitors-ui";
import { pageTitle } from "@/lib/scan/pages-ui";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const POLL_MS = 1500;

export function CompetitorsDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [list, setList] = useState<CompetitorListResponse | null>(null);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [pendingRemove, setPendingRemove] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    let timer: number | undefined;

    async function load() {
      try {
        const nextList = await getCompetitors(scanId);
        const nextComparison = await getCompetitorComparison(scanId);
        if (cancelled) return;
        setList(nextList);
        setComparison(nextComparison);
        setLoadError(null);
        const pending = nextList.competitors.some((item) => item.status === "queued" || item.status === "scanning" || item.status === "running");
        if (pending) {
          timer = window.setTimeout(load, POLL_MS);
        }
      } catch (caught) {
        if (cancelled) return;
        setLoadError(caught instanceof ScanApiError ? caught.message : "Unable to load competitor comparison.");
      }
    }

    void load();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [scan?.status, scanId]);

  async function onAdd(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    if (!name.trim() || !url.trim()) {
      setFormError("Enter a competitor name and URL.");
      return;
    }
    setBusy(true);
    try {
      await addCompetitor(scanId, name.trim().slice(0, 80), url.trim().slice(0, 2048));
      setName("");
      setUrl("");
      const nextList = await getCompetitors(scanId);
      setList(nextList);
      setComparison(await getCompetitorComparison(scanId));
    } catch (caught) {
      setFormError(caught instanceof ScanApiError ? caught.message : "Unable to add this competitor.");
    } finally {
      setBusy(false);
    }
  }

  async function onRemove(id: string) {
    setBusy(true);
    try {
      await deleteCompetitor(scanId, id);
      setPendingRemove(null);
      setList(await getCompetitors(scanId));
      setComparison(await getCompetitorComparison(scanId));
    } catch (caught) {
      setFormError(caught instanceof ScanApiError ? caught.message : "Unable to remove this competitor.");
    } finally {
      setBusy(false);
    }
  }

  async function onRescan(id: string) {
    setBusy(true);
    try {
      await rescanCompetitor(scanId, id);
      setList(await getCompetitors(scanId));
      setComparison(await getCompetitorComparison(scanId));
    } catch (caught) {
      setFormError(caught instanceof ScanApiError ? caught.message : "Unable to rescan this competitor.");
    } finally {
      setBusy(false);
    }
  }

  const empty = emptyCompetitorsCopy(running ? "unavailable" : "none");

  return (
    <ScanShell scanId={scanId} current="competitors">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
          <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Competitors</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Competitor benchmarking</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Compare measurable SiteLens findings across independently scanned public websites.
          </p>
          <p className="mt-3 text-xs text-muted-foreground">{list?.limit_note || "Up to 5 competitors can be benchmarked per scan."}</p>
        </section>

        {failed ? (
          <StateCard title="Competitors unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title={empty.title} body={scan?.current_step ?? empty.body} />
        ) : loadError ? (
          <StateCard title="Unable to load competitors" body={loadError} />
        ) : (
          <>
            <AddForm name={name} url={url} busy={busy} error={formError} remaining={list?.remaining ?? 0} onName={setName} onUrl={setUrl} onSubmit={onAdd} />
            {!list?.competitors.length ? (
              <StateCard title={emptyCompetitorsCopy("none").title} body={emptyCompetitorsCopy("none").body} />
            ) : (
              <ul className="grid gap-4 md:grid-cols-2">
                {list.competitors.map((item) => (
                  <li key={item.id} className="rounded-2xl border border-border bg-card p-5 shadow-sm">
                    <p className="text-sm font-semibold text-foreground">{item.name}</p>
                    <p className="mt-1 truncate font-mono text-xs text-muted-foreground">{item.normalized_url}</p>
                    <p className="mt-3 text-sm text-foreground">{competitorStatusLabel(item.status)}</p>
                    {item.status === "scanning" && typeof item.progress === "number" ? (
                      <p className="mt-1 text-xs text-muted-foreground">{item.current_step} · {item.progress}%</p>
                    ) : null}
                    {item.status === "failed" ? <p className="mt-2 text-sm text-critical">Competitor scan failed. {item.error?.message || "Unable to retrieve the website."}</p> : null}
                    {item.status === "completed" ? (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {item.pages_crawled ?? "—"} pages · {item.issue_count ?? "—"} issue types
                      </p>
                    ) : null}
                    <p className="mt-1 text-xs text-muted-foreground">Last scanned: {formatTimestamp(item.completed_at || item.created_at)}</p>
                    {comparison?.competitors.find((row) => row.column_id === item.id)?.stale ? (
                      <p className="mt-1 text-xs text-muted-foreground">{comparison.competitors.find((row) => row.column_id === item.id)?.stale}</p>
                    ) : null}
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Link href={`/scan/${scanId}/competitors/${item.id}`} className={cn(buttonVariants(), "h-9 px-3")}>
                        View comparison
                      </Link>
                      <Link href={`/scan/${item.competitor_scan_id}`} className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}>
                        View scan
                      </Link>
                      <button type="button" className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")} disabled={busy} onClick={() => void onRescan(item.id)}>
                        {item.status === "failed" ? "Retry" : "Rescan"}
                      </button>
                      {pendingRemove === item.id ? (
                        <>
                          <button type="button" className={cn(buttonVariants({ variant: "destructive" }), "h-9 px-3")} disabled={busy} onClick={() => void onRemove(item.id)}>
                            Confirm remove
                          </button>
                          <button type="button" className={cn(buttonVariants({ variant: "ghost" }), "h-9 px-3")} onClick={() => setPendingRemove(null)}>
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button type="button" className={cn(buttonVariants({ variant: "ghost" }), "h-9 px-3")} onClick={() => setPendingRemove(item.id)}>
                          Remove
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {comparison?.incomplete ? (
              <p className="text-sm text-muted-foreground">{emptyCompetitorsCopy("incomplete").title}</p>
            ) : null}
            {comparison?.warnings?.length ? (
              <ul className="rounded-xl border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
                {comparison.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : null}
            {comparison ? <ComparisonTables comparison={comparison} /> : null}
            {list?.competitors.some((item) => item.status === "completed") ? (
              <PageCompare scanId={scanId} competitors={list.competitors.filter((item) => item.status === "completed")} />
            ) : null}
            {list?.competitors.some((item) => item.status === "completed") ? (
              <ScreenshotCompare scanId={scanId} competitors={list.competitors.filter((item) => item.status === "completed")} />
            ) : null}

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Methodology</h2>
              <p className="mt-2 text-sm text-muted-foreground">{comparison?.methodology.text || COMPETITOR_METHODOLOGY}</p>
              <p className="mt-2 text-sm text-muted-foreground">{comparison?.methodology.scope}</p>
              {comparison?.methodology.viewports ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  Viewports: {Object.entries(comparison.methodology.viewports).map(([name, size]) => `${name} ${size.width}×${size.height}`).join(", ")}.
                </p>
              ) : null}
              <p className="mt-3 text-xs text-muted-foreground">{comparison?.methodology.limitations || COMPETITOR_LIMITATIONS}</p>
            </section>
          </>
        )}
      </div>
    </ScanShell>
  );
}

function AddForm({
  name,
  url,
  busy,
  error,
  remaining,
  onName,
  onUrl,
  onSubmit,
}: {
  name: string;
  url: string;
  busy: boolean;
  error: string | null;
  remaining: number;
  onName: (value: string) => void;
  onUrl: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
}) {
  return (
    <form onSubmit={onSubmit} className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">Add competitor</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="text-xs font-medium text-muted-foreground">
          Name
          <input value={name} onChange={(event) => onName(event.target.value.slice(0, 80))} className="mt-1 h-10 w-full rounded-lg border border-input bg-transparent px-3 text-sm text-foreground" required />
        </label>
        <label className="text-xs font-medium text-muted-foreground">
          URL
          <input value={url} onChange={(event) => onUrl(event.target.value.slice(0, 2048))} placeholder="https://competitor.example" className="mt-1 h-10 w-full rounded-lg border border-input bg-transparent px-3 text-sm text-foreground" required />
        </label>
      </div>
      {error ? <p className="mt-2 text-sm text-critical">{error}</p> : null}
      <button type="submit" className={cn(buttonVariants(), "mt-4 h-10 px-4")} disabled={busy || remaining <= 0}>
        Add competitor
      </button>
    </form>
  );
}

function ComparisonTables({ comparison }: { comparison: ComparisonResponse }) {
  const columns = comparison.columns;
  const scoreMetrics = comparison.metrics.filter((row) => row.group === "scores");
  const coverage = comparison.metrics.filter((row) => row.group === "coverage");
  const architecture = comparison.metrics.filter((row) => row.group === "architecture");
  const performance = comparison.metrics.filter((row) => row.group === "performance");
  const scoreMax = Math.max(100, ...scoreMetrics.flatMap((row) => row.values.map((cell) => (typeof cell.value === "number" ? cell.value : 0))));

  return (
    <>
      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Benchmark overview</h2>
        <MetricTable columns={columns} rows={scoreMetrics} />
        <ul className="mt-6 space-y-3" aria-hidden="true">
          {scoreMetrics.map((row) => (
            <li key={row.id}>
              <p className="text-xs text-muted-foreground">{row.label}</p>
              <div className="mt-1 flex flex-col gap-1">
                {row.values.map((cell) => (
                  <div key={cell.column_id} className="flex items-center gap-2">
                    <span className="w-28 truncate text-xs text-muted-foreground">{columns.find((col) => col.id === cell.column_id)?.label}</span>
                    <div className="h-2 flex-1 rounded-full bg-muted">
                      <div className="h-full rounded-full bg-primary/80" style={{ width: `${cell.available && typeof cell.value === "number" ? barWidth(cell.value, scoreMax) : 0}%` }} />
                    </div>
                    <span className="w-16 text-right text-xs tabular-nums">{displayCell(cell.available, cell.display ?? cell.value)}</span>
                  </div>
                ))}
              </div>
            </li>
          ))}
        </ul>
      </section>
      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Category comparison</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="py-2 pr-3 font-medium">Category</th>
                {columns.map((col) => (
                  <th key={col.id} className="py-2 pr-3 font-medium">{col.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparison.categories.map((row) => (
                <tr key={row.id} className="border-b border-border/70 last:border-0">
                  <td className="py-3 pr-3 font-medium">{row.label}</td>
                  {row.values.map((cell) => (
                    <td key={cell.column_id} className="py-3 pr-3 text-muted-foreground">
                      {cell.available ? (
                        <>
                          {cell.score ?? "—"}
                          <span className="block text-[11px]">
                            {cell.issue_count ?? "—"} issues · {cell.available_checks ?? "—"} checks
                          </span>
                        </>
                      ) : (
                        "Unavailable"
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Page coverage</h2>
        <MetricTable columns={columns} rows={coverage} />
      </section>
      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Issue comparison</h2>
        <MetricTable columns={columns} rows={comparison.severity.map((row) => ({ id: row.id, label: row.label, group: "severity", values: row.values }))} />
        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="py-2 pr-3 font-medium">Issue</th>
                {columns.map((col) => (
                  <th key={col.id} className="py-2 pr-3 font-medium">{col.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparison.issues.map((row) => (
                <tr key={row.issue_key} className="border-b border-border/70 last:border-0">
                  <td className="py-3 pr-3">
                    <p className="font-medium">{row.label}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">{row.issue_key}</p>
                  </td>
                  {row.values.map((cell) => (
                    <td key={cell.column_id} className="py-3 pr-3 text-muted-foreground">{displayCell(cell.available, cell.display ?? cell.value)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Architecture</h2>
        <MetricTable columns={columns} rows={architecture} />
      </section>
      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Performance</h2>
        <p className="mt-1 text-xs text-muted-foreground">Values are measurements from this SiteLens scan environment, not live-user rankings.</p>
        <MetricTable columns={columns} rows={performance} />
      </section>
      {comparison.observations.length ? (
        <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <h2 className="text-sm font-semibold text-foreground">Observations</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-muted-foreground">
            {comparison.observations.map((item) => (
              <li key={item.id}>{item.text}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Timestamps</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {columns.map((col) => (
            <li key={col.id}>
              <span className="font-medium text-foreground">{col.label}:</span>{" "}
              <span className="text-muted-foreground">{formatTimestamp(col.completed_at || col.created_at)}</span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

function MetricTable({
  columns,
  rows,
}: {
  columns: ComparisonResponse["columns"];
  rows: Array<{ id: string; label: string; values: ComparisonCell[]; differences?: ComparisonMetricDiff[] }>;
}) {
  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-muted-foreground">
            <th className="py-2 pr-3 font-medium">Metric</th>
            {columns.map((col) => (
              <th key={col.id} className="py-2 pr-3 font-medium">{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b border-border/70 last:border-0">
              <td className="py-3 pr-3 font-medium">{row.label}</td>
              {row.values.map((cell) => {
                const diff = row.differences?.find((item) => item.column_id === cell.column_id);
                return (
                  <td key={cell.column_id} className="py-3 pr-3 text-muted-foreground">
                    {displayCell(cell.available, cell.display ?? cell.value)}
                    {diff ? <span className="ml-2 text-[11px]">Difference: {diff.display}</span> : null}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type ComparisonMetricDiff = { column_id: string; value: number; display: string };

function PageCompare({ scanId, competitors }: { scanId: string; competitors: CompetitorCard[] }) {
  const [primaryPages, setPrimaryPages] = useState<PageListItem[]>([]);
  const [competitorPages, setCompetitorPages] = useState<PageListItem[]>([]);
  const [competitorId, setCompetitorId] = useState(competitors[0]?.id || "");
  const [primaryPageId, setPrimaryPageId] = useState("");
  const [competitorPageId, setCompetitorPageId] = useState("");
  const [result, setResult] = useState<PageComparisonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = competitors.find((item) => item.id === competitorId) || competitors[0];
  const effectiveCompetitorId = competitorId || selected?.id || "";
  const effectivePrimaryPageId = primaryPageId || primaryPages.find((item) => item.is_seed)?.id || primaryPages[0]?.id || "";
  const effectiveCompetitorPageId = competitorPageId || competitorPages.find((item) => item.is_seed)?.id || competitorPages[0]?.id || "";

  useEffect(() => {
    let cancelled = false;
    getPages(scanId, { page_size: 100 })
      .then((payload) => {
        if (!cancelled) {
          setPrimaryPages(payload.items);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [scanId]);

  useEffect(() => {
    if (!selected?.competitor_scan_id) return;
    let cancelled = false;
    getPages(selected.competitor_scan_id, { page_size: 100 })
      .then((payload) => {
        if (!cancelled) {
          setCompetitorPages(payload.items);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [selected?.competitor_scan_id]);

  async function onCompare() {
    if (!effectivePrimaryPageId || !effectiveCompetitorId || !effectiveCompetitorPageId) return;
    setError(null);
    try {
      setResult(await getPageComparison(scanId, { primary_page_id: effectivePrimaryPageId, competitor_id: effectiveCompetitorId, competitor_page_id: effectiveCompetitorPageId }));
    } catch (caught) {
      setError(caught instanceof ScanApiError ? caught.message : "Unable to compare these pages.");
    }
  }

  async function onSuggest() {
    if (!effectivePrimaryPageId || !effectiveCompetitorId) return;
    try {
      const suggested = await getPageComparison(scanId, { primary_page_id: effectivePrimaryPageId, competitor_id: effectiveCompetitorId });
      const first = suggested.suggestions[0];
      if (first) setCompetitorPageId(first.page_id);
      setResult(suggested);
    } catch (caught) {
      setError(caught instanceof ScanApiError ? caught.message : "Unable to load suggested matches.");
    }
  }

  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">Page comparison</h2>
      <p className="mt-1 text-sm text-muted-foreground">Select crawled pages. Suggested matches use page type, URL path, and title text. They are not equivalent pages.</p>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <SelectField label="Your page" value={effectivePrimaryPageId} onChange={setPrimaryPageId} options={primaryPages.map((page) => ({ id: page.id, label: `${pageTitle(page.title)} · ${page.normalized_url || page.url}` }))} />
        <SelectField label="Competitor" value={effectiveCompetitorId} onChange={setCompetitorId} options={competitors.map((item) => ({ id: item.id, label: item.name }))} />
        <SelectField label="Competitor page" value={effectiveCompetitorPageId} onChange={setCompetitorPageId} options={competitorPages.map((page) => ({ id: page.id, label: `${pageTitle(page.title)} · ${page.normalized_url || page.url}` }))} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className={cn(buttonVariants(), "h-9 px-3")} onClick={() => void onCompare()}>
          Compare pages
        </button>
        <button type="button" className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")} onClick={() => void onSuggest()}>
          Use suggested match
        </button>
      </div>
      {error ? <p className="mt-2 text-sm text-critical">{error}</p> : null}
      {result?.suggestions?.length ? (
        <ul className="mt-3 text-xs text-muted-foreground">
          {result.suggestions.map((item) => (
            <li key={item.page_id}>
              {item.label}: {item.url} ({item.reasons.join(", ")})
            </li>
          ))}
        </ul>
      ) : null}
      {result?.metrics ? (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="py-2 pr-3 font-medium">Metric</th>
                <th className="py-2 pr-3 font-medium">Your page</th>
                <th className="py-2 font-medium">Competitor page</th>
              </tr>
            </thead>
            <tbody>
              {result.metrics.map((row) => (
                <tr key={row.id} className="border-b border-border/70 last:border-0">
                  <td className="py-2 pr-3 font-medium">{row.label}</td>
                  <td className="py-2 pr-3 text-muted-foreground">{row.primary_available === false ? "Unavailable" : displayCell(row.primary != null, row.primary as string | number)}</td>
                  <td className="py-2 text-muted-foreground">{row.competitor_available === false ? "Unavailable" : displayCell(row.competitor != null, row.competitor as string | number)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

function ScreenshotCompare({
  scanId,
  competitors,
}: {
  scanId: string;
  competitors: CompetitorCard[];
}) {
  const completed = competitors.filter((item) => item.status === "completed");
  if (!completed.length) return null;
  const viewports = ["desktop", "tablet", "mobile"] as const;
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">Screenshots</h2>
      <p className="mt-1 text-sm text-muted-foreground">Side-by-side captures from the UI/UX scan. No visual ranking is applied.</p>
      {viewports.map((viewport) => (
        <div key={viewport} className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{viewport}</p>
          <div className="mt-2 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            <figure className="rounded-xl border border-border bg-muted/30 p-2">
              <figcaption className="px-1 pb-2 text-xs text-muted-foreground">Your site</figcaption>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img alt="" src={`/api/scans/${scanId}/uiux/screenshots/${viewport}`} className="w-full rounded-lg border border-border" />
            </figure>
            {completed.map((item) => (
              <figure key={`${item.id}-${viewport}`} className="rounded-xl border border-border bg-muted/30 p-2">
                <figcaption className="px-1 pb-2 text-xs text-muted-foreground">{item.name}</figcaption>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img alt="" src={`/api/scans/${item.competitor_scan_id}/uiux/screenshots/${viewport}`} className="w-full rounded-lg border border-border" />
              </figure>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ id: string; label: string }>;
}) {
  return (
    <label className="text-xs font-medium text-muted-foreground">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-lg border border-input bg-transparent px-2 text-sm text-foreground">
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function StateCard({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-lg font-semibold text-foreground">{title}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </section>
  );
}
