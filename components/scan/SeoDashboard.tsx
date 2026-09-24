"use client";

import { useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import { getSeo, ScanApiError, type SeoCheck, type SeoCheckStatus, type SeoResultResponse } from "@/lib/scan/api";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const CATEGORY_ORDER = [
  ["metadata", "Metadata"],
  ["indexability", "Indexability"],
  ["headings", "Headings"],
  ["canonical", "Canonical"],
  ["images", "Images"],
  ["links", "Links"],
  ["technical", "Technical"],
  ["social", "Social"],
  ["robots_sitemap", "Robots & Sitemap"],
] as const;

const FILTERS: Array<{ id: "all" | "pass" | "warning" | "fail"; label: string }> = [
  { id: "all", label: "All" },
  { id: "pass", label: "Passed" },
  { id: "warning", label: "Warnings" },
  { id: "fail", label: "Failed" },
];

const SEVERITY_SECTIONS: Array<{ id: SeoCheck["severity"]; label: string }> = [
  { id: "critical", label: "Critical" },
  { id: "high", label: "High" },
  { id: "medium", label: "Medium" },
  { id: "low", label: "Low" },
  { id: "info", label: "Info" },
];

export function SeoDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [seo, setSeo] = useState<SeoResultResponse | null>(null);
  const [seoError, setSeoError] = useState<string | null>(null);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getSeo(scanId)
      .then((result) => {
        if (!cancelled) {
          setSeo(result);
          setSeoError(null);
        }
      })
      .catch((caught) => {
        if (cancelled) {
          return;
        }
        setSeoError(caught instanceof ScanApiError ? caught.message : "Unable to load SEO results.");
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId]);

  const selected = seo?.checks.find((check) => check.check_id === selectedId) ?? null;
  const filtered = useMemo(() => {
    if (!seo) {
      return [];
    }
    if (filter === "all") {
      return seo.checks;
    }
    return seo.checks.filter((check) => check.status === filter);
  }, [seo, filter]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";

  return (
    <ScanShell scanId={scanId} current="seo">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="SEO analysis unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title="Running SEO analysis" body={scan?.current_step ?? "Loading scan status…"} />
        ) : seoError ? (
          <StateCard title="Unable to load SEO results" body={seoError} />
        ) : !seo ? (
          <StateCard title="Loading SEO results" body="Fetching the analysis for this scan." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">SEO Score</p>
              <p className="mt-3 text-5xl font-semibold tracking-tight text-foreground">
                {seo.score} <span className="text-2xl font-medium text-muted-foreground">/ 100</span>
              </p>
              <p className="mt-4 whitespace-pre-line text-sm leading-6 text-muted-foreground">{seo.narrative}</p>
              <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MiniStat label="Passed" value={seo.summary.passed} />
                <MiniStat label="Warnings" value={seo.summary.warnings} />
                <MiniStat label="Failed" value={seo.summary.failed} />
                <MiniStat label="Not applicable" value={seo.summary.not_applicable} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Category scores</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {CATEGORY_ORDER.map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3">
                    <p className="text-sm text-muted-foreground">{label}</p>
                    <p className="text-sm font-semibold text-foreground">
                      {seo.categories[key] == null ? "—" : seo.categories[key]}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Page information</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                <Info label="Analyzed URL" value={seo.page?.analyzed_url ?? "—"} mono />
                <Info label="Final URL" value={seo.page?.final_url ?? "—"} mono />
                <Info label="HTTP Status" value={seo.page?.status_code != null ? String(seo.page.status_code) : "—"} />
                <Info label="Title" value={seo.page?.title ?? "—"} />
                <Info label="H1" value={seo.page?.h1 ?? "—"} />
              </dl>
            </section>

            <IssueGroups checks={seo.checks} onSelect={setSelectedId} />

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="text-sm font-semibold text-foreground">SEO checks</h2>
                <div className="flex flex-wrap gap-2">
                  {FILTERS.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setFilter(item.id)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-medium",
                        filter === item.id
                          ? "border-foreground/15 bg-foreground text-background"
                          : "border-border bg-background text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[36rem] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs tracking-wide text-muted-foreground uppercase">
                      <th className="py-2 pr-3 font-medium">Check</th>
                      <th className="py-2 pr-3 font-medium">Status</th>
                      <th className="py-2 font-medium">Severity</th>
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
                        <td className="py-3 pr-3">
                          <StatusMark status={check.status} />
                        </td>
                        <td className="py-3 text-muted-foreground">
                          {check.status === "pass" || check.status === "not_applicable"
                            ? "—"
                            : capitalize(check.severity)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filtered.length === 0 ? (
                  <p className="py-6 text-center text-sm text-muted-foreground">No checks match this filter.</p>
                ) : null}
              </div>
            </section>

            {selected ? <CheckDetail check={selected} /> : null}
          </>
        )}
      </div>
    </ScanShell>
  );
}

function IssueGroups({
  checks,
  onSelect,
}: {
  checks: SeoCheck[];
  onSelect: (id: string) => void;
}) {
  const issues = checks.filter((check) => check.status === "fail" || check.status === "warning");
  if (issues.length === 0) {
    return (
      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
        <h2 className="text-sm font-semibold text-foreground">Top SEO issues</h2>
        <p className="mt-3 text-sm text-muted-foreground">No failed checks or warnings were found on this page.</p>
      </section>
    );
  }
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-sm font-semibold text-foreground">Top SEO issues</h2>
      <div className="mt-4 space-y-5">
        {SEVERITY_SECTIONS.map((section) => {
          const items = issues.filter((check) => check.severity === section.id);
          if (items.length === 0) {
            return null;
          }
          return (
            <div key={section.id}>
              <p className="text-xs font-medium tracking-[0.16em] text-muted-foreground uppercase">{section.label}</p>
              <ul className="mt-2 space-y-1">
                {items.map((check) => (
                  <li key={check.check_id}>
                    <button
                      type="button"
                      className="text-left text-sm text-foreground hover:underline"
                      onClick={() => onSelect(check.check_id)}
                    >
                      {check.name}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function CheckDetail({ check }: { check: SeoCheck }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-lg font-semibold text-foreground">{check.name}</h2>
      <dl className="mt-4 space-y-3 text-sm">
        <Detail label="Status" value={statusLabel(check.status)} />
        <Detail label="Affected URL" value={check.page_url} mono />
        {check.why ? <Detail label="Why this matters" value={check.why} /> : null}
        {check.recommendation ? <Detail label="Recommendation" value={check.recommendation} /> : null}
        <Detail label="Detected" value={check.detected || check.message} />
      </dl>
    </section>
  );
}

function StatusMark({ status }: { status: SeoCheckStatus }) {
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

function Info({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("mt-1 break-all text-foreground", mono && "font-mono text-xs sm:text-sm")}>{value}</dd>
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
