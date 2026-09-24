"use client";

import { useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import {
  getAccessibility,
  ScanApiError,
  type A11yCheck,
  type A11yResultResponse,
  type SeoCheckStatus,
  type SeoSeverity,
} from "@/lib/scan/api";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const CATEGORY_ORDER = [
  ["document", "Document"],
  ["landmarks", "Landmarks"],
  ["forms", "Forms"],
  ["images", "Images"],
  ["aria", "ARIA"],
  ["keyboard", "Keyboard"],
  ["contrast", "Contrast"],
  ["controls", "Controls"],
  ["headings", "Headings"],
  ["links", "Links"],
  ["tables", "Tables"],
  ["media", "Media"],
  ["other", "Other"],
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

export function AccessibilityDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [a11y, setA11y] = useState<A11yResultResponse | null>(null);
  const [a11yError, setA11yError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]["id"]>("all");
  const [severityFilter, setSeverityFilter] = useState<(typeof SEVERITY_FILTERS)[number]["id"]>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getAccessibility(scanId)
      .then((result) => {
        if (!cancelled) {
          setA11y(result);
          setA11yError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setA11yError(caught instanceof ScanApiError ? caught.message : "Accessibility analysis not available.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId]);

  const findings = a11y?.findings?.length ? a11y.findings : a11y?.checks || [];
  const desktopShot = a11y?.screenshots?.find((item) => item.viewport === "desktop") ?? a11y?.screenshots?.[0];
  const selected = findings.find((check) => check.check_id === selectedId) ?? null;
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return findings.filter((check) => {
      if (statusFilter !== "all" && check.status !== statusFilter) {
        return false;
      }
      if (severityFilter !== "all" && check.severity !== severityFilter) {
        return false;
      }
      if (categoryFilter !== "all" && check.group !== categoryFilter) {
        return false;
      }
      if (!needle) {
        return true;
      }
      const hay = `${check.name} ${check.group} ${check.message} ${check.selector || ""} ${check.wcag_reference || ""}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [findings, statusFilter, severityFilter, categoryFilter, query]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";

  return (
    <ScanShell scanId={scanId} current="accessibility">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="Accessibility analysis unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title="Running accessibility analysis" body={scan?.current_step ?? "Loading scan status…"} />
        ) : a11yError ? (
          <StateCard title="Accessibility analysis not available." body={a11yError} />
        ) : !a11y ? (
          <StateCard title="Loading accessibility results" body="Fetching the automated accessibility audit for this scan." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Accessibility</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Accessibility</h1>
              <p className="mt-1 text-sm text-muted-foreground">Automated accessibility analysis of the scanned website.</p>
              <p className="mt-4 text-5xl font-semibold tracking-tight text-foreground">
                {a11y.score} <span className="text-2xl font-medium text-muted-foreground">/ 100</span>
              </p>
              <div className="mt-4 rounded-xl border border-border bg-muted/40 px-4 py-3 text-sm leading-6 text-muted-foreground">
                Automated audit only. Passing these checks does not guarantee WCAG or legal compliance. This analysis
                identifies detectable accessibility issues but does not replace manual accessibility testing.
              </div>
              {a11y.tool ? (
                <p className="mt-3 text-xs text-muted-foreground">
                  Tool: {a11y.tool.name}
                  {a11y.tool.version ? ` ${a11y.tool.version}` : ""} · {a11y.standard?.name || "WCAG-oriented automated checks"}
                  {typeof a11y.tool.axe_passes === "number" ? ` · axe passes ${a11y.tool.axe_passes}` : ""}
                </p>
              ) : null}
              <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MiniStat label="Passed" value={a11y.summary.passed} />
                <MiniStat label="Warnings" value={a11y.summary.warnings} />
                <MiniStat label="Failed" value={a11y.summary.failed} />
                <MiniStat label="Manual review" value={a11y.summary.manual_review ?? 0} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Category scores</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
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
                      {a11y.categories[key] == null ? "—" : a11y.categories[key]}
                    </p>
                  </button>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <h2 className="text-sm font-semibold text-foreground">Accessibility findings</h2>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search name, category, selector, message"
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
              <div className="mt-2 flex flex-wrap gap-2">
                <FilterChip active={categoryFilter === "all"} onClick={() => setCategoryFilter("all")} label="All categories" />
                {CATEGORY_ORDER.map(([key, label]) => (
                  <FilterChip key={key} active={categoryFilter === key} onClick={() => setCategoryFilter(key)} label={label} />
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
                      <th className="py-2 pr-3 font-medium">Affected</th>
                      <th className="py-2 font-medium">WCAG</th>
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
                        <td className="py-3 pr-3 capitalize text-muted-foreground">{check.group}</td>
                        <td className="py-3 pr-3">
                          <StatusMark status={check.status} manual={check.manual_review} />
                        </td>
                        <td className="py-3 pr-3 text-muted-foreground">
                          {check.status === "pass" || check.status === "not_applicable" ? "—" : capitalize(check.severity)}
                        </td>
                        <td className="py-3 pr-3 text-muted-foreground">{check.affected_element_count || "—"}</td>
                        <td className="py-3 text-muted-foreground">{check.wcag_reference || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filtered.length === 0 ? (
                  <p className="py-6 text-center text-sm text-muted-foreground">No findings match these filters.</p>
                ) : null}
              </div>
            </section>

            {desktopShot?.url ? (
              <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
                <h2 className="text-sm font-semibold text-foreground">Rendered page</h2>
                <p className="mt-1 text-sm text-muted-foreground">Desktop capture from the UI/UX scan. No additional accessibility screenshots are generated.</p>
                <div className="mt-4 overflow-hidden rounded-xl border border-border bg-muted/40">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={desktopShot.url} alt="Desktop screenshot of the analyzed homepage" className="mx-auto max-h-[40vh] w-full object-contain object-top" />
                </div>
              </section>
            ) : null}

            {selected ? <CheckDetail check={selected} /> : null}

            {a11y.limitations?.length ? (
              <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
                <h2 className="text-sm font-semibold text-foreground">Limitations</h2>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-muted-foreground">
                  {a11y.limitations.map((item) => (
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

function CheckDetail({ check }: { check: A11yCheck }) {
  const source =
    check.source === "axe" ? "axe-core" : check.source === "manual-review" ? "Manual review" : "SiteLens rule";
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-lg font-semibold text-foreground">{check.name}</h2>
      {check.manual_review ? (
        <p className="mt-2 text-sm font-medium text-warn">Manual review recommended</p>
      ) : null}
      <dl className="mt-4 space-y-3 text-sm">
        <Detail label="Status" value={statusLabel(check.status)} />
        <Detail label="Impact" value={check.status === "pass" ? "—" : capitalize(check.severity)} />
        <Detail label="Affected" value={check.affected_element_count ? `${check.affected_element_count} element(s)` : "—"} />
        {check.selector ? <Detail label="Selector" value={check.selector} mono /> : null}
        <Detail label="Why it matters" value={check.why || check.message} />
        {check.recommendation ? <Detail label="Recommendation" value={check.recommendation} /> : null}
        <Detail label="Detected" value={check.detected || check.message} />
        <Detail label="WCAG" value={check.wcag_reference || "—"} />
        <Detail label="Source" value={source} />
        {check.help_url ? <Detail label="Reference" value={check.help_url} mono /> : null}
        <Detail label="Page" value={check.page_url} mono />
      </dl>
    </section>
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

function StatusMark({ status, manual }: { status: SeoCheckStatus; manual?: boolean }) {
  if (manual && status === "warning") {
    return <span className="font-medium text-warn">Manual review</span>;
  }
  if (status === "pass") {
    return <span className="font-medium text-pass">✓ Pass</span>;
  }
  if (status === "warning") {
    return <span className="font-medium text-warn">⚠ Warning</span>;
  }
  if (status === "fail") {
    return <span className="font-medium text-critical">✕ Fail</span>;
  }
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

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-muted/50 px-3 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold text-foreground">{value}</p>
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
