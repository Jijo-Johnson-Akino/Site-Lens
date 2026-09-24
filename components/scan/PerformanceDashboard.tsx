"use client";

import { useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import {
  getPerformance,
  ScanApiError,
  type PerfCheck,
  type PerfResourceRow,
  type PerfResultResponse,
  type PerfVital,
  type SeoCheckStatus,
  type SeoSeverity,
} from "@/lib/scan/api";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const CATEGORY_ORDER = [
  ["vitals", "Core Web Vitals"],
  ["loading", "Loading"],
  ["server", "Server"],
  ["javascript", "JavaScript"],
  ["css", "CSS"],
  ["images", "Images"],
  ["fonts", "Fonts"],
  ["caching", "Caching"],
  ["compression", "Compression"],
  ["third_party", "Third party"],
  ["blocking", "Render blocking"],
  ["dom", "DOM"],
  ["redirects", "Redirects"],
] as const;

const STATUS_FILTERS: Array<{ id: "all" | "fail" | "warning" | "pass"; label: string }> = [
  { id: "all", label: "All" },
  { id: "fail", label: "Failed" },
  { id: "warning", label: "Warnings" },
  { id: "pass", label: "Passed" },
];

const SEVERITY_FILTERS: Array<{ id: "all" | SeoSeverity; label: string }> = [
  { id: "all", label: "All severity" },
  { id: "critical", label: "Critical" },
  { id: "high", label: "High" },
  { id: "medium", label: "Medium" },
  { id: "low", label: "Low" },
];

type SortKey = "url" | "type" | "transfer_bytes" | "duration_ms";

export function PerformanceDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [perf, setPerf] = useState<PerfResultResponse | null>(null);
  const [perfError, setPerfError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]["id"]>("all");
  const [severityFilter, setSeverityFilter] = useState<(typeof SEVERITY_FILTERS)[number]["id"]>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [resourceQuery, setResourceQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("transfer_bytes");
  const [selectedResource, setSelectedResource] = useState<string | null>(null);

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getPerformance(scanId)
      .then((result) => {
        if (!cancelled) {
          setPerf(result);
          setPerfError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setPerfError(caught instanceof ScanApiError ? caught.message : "Performance analysis not available.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId]);

  const findings = perf?.findings?.length ? perf.findings : perf?.checks || [];
  const selected = findings.find((check) => check.check_id === selectedId) ?? null;
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return findings.filter((check) => {
      if (statusFilter !== "all" && check.status !== statusFilter) return false;
      if (severityFilter !== "all" && check.severity !== severityFilter) return false;
      if (categoryFilter !== "all" && check.group !== categoryFilter) return false;
      if (!needle) return true;
      const hay = `${check.name} ${check.group} ${check.message} ${check.resource_url || ""} ${check.detected || ""}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [findings, statusFilter, severityFilter, categoryFilter, query]);

  const resources = perf?.resource_table || [];
  const resourceRows = useMemo(() => {
    const needle = resourceQuery.trim().toLowerCase();
    const rows = resources.filter((item) => {
      if (!needle) return true;
      return `${item.url} ${item.type} ${item.domain || ""}`.toLowerCase().includes(needle);
    });
    rows.sort((a, b) => {
      if (sortKey === "url" || sortKey === "type") {
        return String(a[sortKey] || "").localeCompare(String(b[sortKey] || ""));
      }
      return Number(b[sortKey] || 0) - Number(a[sortKey] || 0);
    });
    return rows;
  }, [resources, resourceQuery, sortKey]);
  const selectedRow = resources.find((item) => item.url === selectedResource) ?? null;

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const env = perf?.environment;
  const viewport = env?.viewport
    ? `${env.viewport.width || "—"} × ${env.viewport.height || "—"}`
    : "—";

  return (
    <ScanShell scanId={scanId} current="performance">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="Performance analysis unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title="Running performance analysis" body={scan?.current_step ?? "Loading scan status…"} />
        ) : perfError ? (
          <StateCard title="Performance analysis not available." body={perfError} />
        ) : !perf ? (
          <StateCard title="Loading performance results" body="Fetching the automated browser performance measurements for this scan." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Performance</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Performance</h1>
              <p className="mt-1 text-sm text-muted-foreground">Automated browser performance analysis of the scanned website.</p>
              <p className="mt-4 text-5xl font-semibold tracking-tight text-foreground">
                {perf.score} <span className="text-2xl font-medium text-muted-foreground">/ 100</span>
              </p>
              <div className="mt-4 rounded-xl border border-border bg-muted/40 px-4 py-3 text-sm leading-6 text-muted-foreground">
                Lab measurement from one Chromium run. This is not a guarantee of how fast the site loads for every user.
              </div>
              <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MiniStat label="Browser" value={capitalize(env?.browser || "Chromium")} />
                <MiniStat label="Viewport" value={viewport} />
                <MiniStat label="Cache" value={capitalize(env?.cache_mode || "cold")} />
                <MiniStat label="Network" value={capitalize(env?.network_profile || "default")} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Core Web Vitals</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <VitalCard label="LCP" vital={perf.vitals?.lcp} formatter={formatMs} />
                <VitalCard label="CLS" vital={perf.vitals?.cls} formatter={formatCls} />
                <VitalCard label="INP" vital={perf.vitals?.inp} formatter={formatMs} />
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Loading metrics</h2>
              <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MiniStat label="TTFB" value={formatMs(perf.timing?.ttfb_ms)} />
                <MiniStat label="DOM Content Loaded" value={formatMs(perf.timing?.dom_content_loaded_ms)} />
                <MiniStat label="Load event" value={formatMs(perf.timing?.load_event_ms)} />
                <MiniStat label="Redirect time" value={formatMs(perf.timing?.redirect_ms)} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Resource summary</h2>
              <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MiniStat label="Requests" value={String(perf.resources?.total_requests ?? 0)} />
                <MiniStat label="Transfer" value={formatBytes(perf.resources?.transfer_bytes)} />
                <MiniStat label="JavaScript" value={formatBytes(perf.resources?.js_bytes)} />
                <MiniStat label="Images" value={formatBytes(perf.resources?.image_bytes)} />
                <MiniStat label="CSS" value={formatBytes(perf.resources?.css_bytes)} />
                <MiniStat label="HTML" value={formatBytes(perf.resources?.html_bytes)} />
                <MiniStat label="Fonts" value={formatBytes(perf.resources?.font_bytes)} />
                <MiniStat label="Third party" value={formatBytes(perf.resources?.third_party_bytes)} />
              </dl>
              <div className="mt-5 space-y-2">
                {(["javascript", "images", "css", "html", "fonts", "third_party"] as const).map((key) => (
                  <Bar key={key} label={key.replace("_", " ")} percent={perf.resources?.percentages?.[key] ?? 0} />
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Category scores</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {CATEGORY_ORDER.map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setCategoryFilter((current) => (current === key ? "all" : key))}
                    className={cn(
                      "flex items-center justify-between rounded-xl border px-4 py-3 text-left",
                      categoryFilter === key ? "border-foreground/20 bg-muted" : "border-border bg-muted/40",
                    )}
                  >
                    <p className="text-sm text-muted-foreground">{label}</p>
                    <p className="text-sm font-semibold text-foreground">
                      {perf.categories[key] == null ? "—" : perf.categories[key]}
                    </p>
                  </button>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <h2 className="text-sm font-semibold text-foreground">Performance findings</h2>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search name, category, resource, message"
                  className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm lg:max-w-sm"
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {STATUS_FILTERS.map((item) => (
                  <FilterChip key={item.id} active={statusFilter === item.id} onClick={() => setStatusFilter(item.id)} label={item.label} />
                ))}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {SEVERITY_FILTERS.map((item) => (
                  <FilterChip key={item.id} active={severityFilter === item.id} onClick={() => setSeverityFilter(item.id)} label={item.label} />
                ))}
              </div>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[48rem] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs tracking-wide text-muted-foreground uppercase">
                      <th className="py-2 pr-3 font-medium">Check</th>
                      <th className="py-2 pr-3 font-medium">Category</th>
                      <th className="py-2 pr-3 font-medium">Status</th>
                      <th className="py-2 pr-3 font-medium">Severity</th>
                      <th className="py-2 font-medium">Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((check) => (
                      <tr
                        key={check.check_id}
                        className={cn(
                          "cursor-pointer border-b border-border/80 last:border-0 hover:bg-muted/40",
                          selectedId === check.check_id && "bg-muted/60",
                        )}
                        onClick={() => setSelectedId(check.check_id)}
                      >
                        <td className="py-3 pr-3 text-foreground">{check.name}</td>
                        <td className="py-3 pr-3 capitalize text-muted-foreground">{check.group.replace("_", " ")}</td>
                        <td className="py-3 pr-3">
                          <StatusMark status={check.status} />
                        </td>
                        <td className="py-3 pr-3 text-muted-foreground">
                          {check.status === "pass" || check.status === "not_applicable" ? "—" : capitalize(check.severity)}
                        </td>
                        <td className="py-3 text-muted-foreground">{check.detected || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filtered.length === 0 ? (
                  <p className="py-6 text-center text-sm text-muted-foreground">No findings match these filters.</p>
                ) : null}
              </div>
            </section>

            {selected ? <CheckDetail check={selected} /> : null}

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <h2 className="text-sm font-semibold text-foreground">Resource explorer</h2>
                <input
                  value={resourceQuery}
                  onChange={(event) => setResourceQuery(event.target.value)}
                  placeholder="Search resource URL or type"
                  className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm lg:max-w-sm"
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {(["url", "type", "transfer_bytes", "duration_ms"] as const).map((key) => (
                  <FilterChip key={key} active={sortKey === key} onClick={() => setSortKey(key)} label={`Sort: ${key.replace("_", " ")}`} />
                ))}
              </div>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[48rem] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs tracking-wide text-muted-foreground uppercase">
                      <th className="py-2 pr-3 font-medium">Resource</th>
                      <th className="py-2 pr-3 font-medium">Type</th>
                      <th className="py-2 pr-3 font-medium">Transfer</th>
                      <th className="py-2 pr-3 font-medium">Duration</th>
                      <th className="py-2 pr-3 font-medium">Party</th>
                      <th className="py-2 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resourceRows.slice(0, 80).map((item, index) => (
                      <tr
                        key={`${item.url}-${item.type}-${index}`}
                        className={cn(
                          "cursor-pointer border-b border-border/80 last:border-0 hover:bg-muted/40",
                          selectedResource === item.url && "bg-muted/60",
                        )}
                        onClick={() => setSelectedResource(item.url)}
                      >
                        <td className="max-w-[18rem] truncate py-3 pr-3 font-mono text-xs text-foreground">{item.url}</td>
                        <td className="py-3 pr-3 text-muted-foreground">{item.type}</td>
                        <td className="py-3 pr-3 text-muted-foreground">{formatBytes(item.transfer_bytes)}</td>
                        <td className="py-3 pr-3 text-muted-foreground">{formatMs(item.duration_ms)}</td>
                        <td className="py-3 pr-3 text-muted-foreground">{item.first_party ? "First" : "Third"}</td>
                        <td className="py-3 text-muted-foreground">{item.status ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {selectedRow ? <ResourceDetail row={selectedRow} /> : null}
            </section>

            {perf.limitations?.length ? (
              <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
                <h2 className="text-sm font-semibold text-foreground">Limitations</h2>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-muted-foreground">
                  {perf.limitations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            ) : null}
          </>
        )}
      </div>
    </ScanShell>
  );
}

function VitalCard({ label, vital, formatter }: { label: string; vital?: PerfVital; formatter: (value: number | null | undefined) => string }) {
  const unavailable = !vital || vital.status === "unavailable" || vital.value == null;
  return (
    <div className="rounded-xl border border-border bg-muted/40 px-4 py-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-foreground">{unavailable ? "Unavailable" : formatter(vital.value)}</p>
      <p className="mt-1 text-xs text-muted-foreground">
        {unavailable ? vital?.reason || "Not measured in this automated run." : capitalize(vital.status.replace("_", " "))}
      </p>
    </div>
  );
}

function CheckDetail({ check }: { check: PerfCheck }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-lg font-semibold text-foreground">{check.name}</h2>
      <dl className="mt-4 space-y-3 text-sm">
        <Detail label="Status" value={statusLabel(check.status)} />
        <Detail label="Category" value={capitalize(check.group.replace("_", " "))} />
        <Detail label="Severity" value={check.status === "pass" || check.status === "not_applicable" ? "—" : capitalize(check.severity)} />
        <Detail label="Measured evidence" value={check.detected || "—"} />
        <Detail label="Why it matters" value={check.why || check.message} />
        {check.recommendation ? <Detail label="Recommendation" value={check.recommendation} /> : null}
        {check.resource_url ? <Detail label="Affected resource" value={check.resource_url} mono /> : null}
        <Detail label="Page" value={check.page_url} mono />
      </dl>
    </section>
  );
}

function ResourceDetail({ row }: { row: PerfResourceRow }) {
  return (
    <dl className="mt-5 grid gap-3 rounded-xl border border-border bg-muted/40 p-4 text-sm sm:grid-cols-2">
      <Detail label="URL" value={row.url} mono />
      <Detail label="Domain" value={row.domain || "—"} />
      <Detail label="Type" value={row.type} />
      <Detail label="Transfer" value={formatBytes(row.transfer_bytes)} />
      <Detail label="Decoded" value={formatBytes(row.decoded_bytes)} />
      <Detail label="Duration" value={formatMs(row.duration_ms)} />
      <Detail label="Cache-Control" value={row.cache_control || "—"} />
      <Detail label="Compression" value={row.content_encoding || "none recorded"} />
      <Detail label="Party" value={row.first_party ? "First-party" : "Third-party"} />
      <Detail label="Initiator" value={row.initiator || "—"} />
    </dl>
  );
}

function Bar({ label, percent }: { label: string; percent: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-muted-foreground">
        <span className="capitalize">{label}</span>
        <span>{percent}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-foreground/30" style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} />
      </div>
    </div>
  );
}

function FilterChip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs font-medium",
        active ? "border-foreground/15 bg-foreground text-background" : "border-border bg-background text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </button>
  );
}

function StatusMark({ status }: { status: SeoCheckStatus }) {
  if (status === "pass") return <span className="font-medium text-pass">✓ Pass</span>;
  if (status === "warning") return <span className="font-medium text-warn">⚠ Warning</span>;
  if (status === "fail") return <span className="font-medium text-critical">✕ Fail</span>;
  return <span className="font-medium text-muted-foreground">— N/A</span>;
}

function StateCard({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h1 className="text-lg font-semibold text-foreground">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </section>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-muted/50 px-3 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold text-foreground">{value}</p>
    </div>
  );
}

function Detail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className={cn("mt-1 text-foreground", mono && "font-mono text-xs break-all")}>{value}</dd>
    </div>
  );
}

function statusLabel(status: SeoCheckStatus) {
  if (status === "pass") return "Passed";
  if (status === "warning") return "Warning";
  if (status === "fail") return "Failed";
  return "Not applicable";
}

function capitalize(value: string) {
  return value.slice(0, 1).toUpperCase() + value.slice(1);
}

function formatBytes(value?: number | null) {
  if (value == null) return "Unavailable";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatMs(value?: number | null) {
  if (value == null) return "Unavailable";
  if (value >= 1000) return `${(value / 1000).toFixed(2)}s`;
  return `${Math.round(value)}ms`;
}

function formatCls(value?: number | null) {
  if (value == null) return "Unavailable";
  return value.toFixed(3);
}
