"use client";

import { useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import {
  getContent,
  ScanApiError,
  type ContentCheck,
  type ContentResultResponse,
  type SeoCheckStatus,
  type SeoSeverity,
} from "@/lib/scan/api";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const CATEGORY_ORDER = [
  ["structure", "Structure"],
  ["depth", "Depth"],
  ["readability", "Readability"],
  ["headings", "Headings"],
  ["duplication", "Duplication"],
  ["freshness", "Freshness"],
  ["authorship", "Authorship"],
  ["completeness", "Completeness"],
] as const;

const SIGNAL_CARDS = [
  ["thin_content", "Content depth", "thin"],
  ["duplicate_content", "Duplication", "dup"],
  ["repeated_content", "Repetition", "rep"],
  ["boilerplate_ratio", "Boilerplate", "boiler"],
  ["publication_date_detected", "Freshness", "fresh"],
  ["author_detected", "Authorship", "auth"],
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

export function ContentDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [content, setContent] = useState<ContentResultResponse | null>(null);
  const [contentError, setContentError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]["id"]>("all");
  const [severityFilter, setSeverityFilter] = useState<(typeof SEVERITY_FILTERS)[number]["id"]>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getContent(scanId)
      .then((result) => {
        if (!cancelled) {
          setContent(result);
          setContentError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setContentError(caught instanceof ScanApiError ? caught.message : "Content analysis not available.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId]);

  const findings = content?.findings?.length ? content.findings : content?.checks || [];
  const selected = findings.find((check) => check.check_id === selectedId) ?? null;
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return findings.filter((check) => {
      if (statusFilter !== "all" && check.status !== statusFilter) return false;
      if (severityFilter !== "all" && check.severity !== severityFilter) return false;
      if (!needle) return true;
      const hay = `${check.name} ${check.group} ${check.message} ${check.detected || ""}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [findings, statusFilter, severityFilter, query]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const typeLabel = content?.page_type?.type ? capitalize(content.page_type.type) : "Unknown";
  const confidence = content?.page_type?.confidence != null ? `${Math.round(content.page_type.confidence * 100)}%` : "—";
  const readabilityUnavailable = !content?.readability?.supported || content.readability.flesch_reading_ease == null;

  return (
    <ScanShell scanId={scanId} current="content">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="Content analysis unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title="Running content analysis" body={scan?.current_step ?? "Loading scan status…"} />
        ) : contentError ? (
          <StateCard title="Content analysis not available." body={contentError} />
        ) : !content ? (
          <StateCard title="Loading content results" body="Fetching the deterministic content measurements for this scan." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Content</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Content</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Deterministic analysis of content structure, depth, readability, and measurable content signals.
              </p>
              <p className="mt-4 text-5xl font-semibold tracking-tight text-foreground">
                {content.score} <span className="text-2xl font-medium text-muted-foreground">/ 100</span>
              </p>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Page overview</h2>
              <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <MiniStat label="Page type" value={typeLabel} />
                <MiniStat label="Confidence" value={confidence} />
                <MiniStat label="Word count" value={formatNumber(content.metrics?.word_count)} />
                <MiniStat label="Paragraphs" value={formatNumber(content.metrics?.paragraph_count)} />
                <MiniStat label="Headings" value={formatNumber(content.metrics?.heading_count)} />
                <MiniStat label="Sections" value={formatNumber(content.metrics?.section_count)} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Content structure</h2>
              <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MiniStat label="Main content" value={content.signals?.main_content_detected ? "Detected" : "Not clearly detected"} />
                <MiniStat label="H1" value={formatNumber(content.metrics?.h1_count ?? content.structure?.h1_count)} />
                <MiniStat label="H2" value={formatNumber(content.metrics?.h2_count ?? content.structure?.h2_count)} />
                <MiniStat label="H3" value={formatNumber(content.metrics?.h3_count ?? content.structure?.h3_count)} />
                <MiniStat label="Lists" value={formatNumber(content.metrics?.list_count)} />
                <MiniStat label="Tables" value={formatNumber(content.metrics?.table_count)} />
                <MiniStat label="Internal content links" value={formatNumber(content.metrics?.internal_content_links)} />
                <MiniStat label="CTA" value={content.signals?.cta_detected ? "Detected" : "Not detected"} />
              </dl>
              <div className="mt-5 space-y-2">
                <Bar label="Primary copy" percent={Math.round((1 - (content.signals?.boilerplate_ratio || 0)) * 100)} />
                <Bar label="Boilerplate estimate" percent={Math.round((content.signals?.boilerplate_ratio || 0) * 100)} />
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Readability</h2>
              {readabilityUnavailable ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  {content.readability?.reason || "Readability unavailable for this language."}
                </p>
              ) : (
                <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <MiniStat label="Flesch Reading Ease" value={String(content.readability?.flesch_reading_ease)} />
                  <MiniStat label="Grade level" value={String(content.readability?.flesch_kincaid_grade)} />
                  <MiniStat label="Language" value={content.readability?.language || content.page?.language || "—"} />
                  {content.readability?.label ? <MiniStat label="Ease band" value={content.readability.label} /> : null}
                </dl>
              )}
              <p className="mt-4 text-sm leading-6 text-muted-foreground">
                Readability formulas provide statistical reading-level signals and do not judge the quality or accuracy of the content.
              </p>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Content signals</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {SIGNAL_CARDS.map(([key, label]) => (
                  <MiniStat key={key} label={label} value={signalValue(content, key)} />
                ))}
                <MiniStat label="Completeness" value={categoryValue(content, "completeness")} />
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Category scores</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {CATEGORY_ORDER.map(([key, label]) => (
                  <MiniStat key={key} label={label} value={categoryValue(content, key)} />
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Duplicate content</h2>
              {content.duplicates?.length ? (
                <ul className="mt-3 space-y-2 text-sm">
                  {content.duplicates.map((item, index) => (
                    <li key={`${item.url}-${item.kind}-${index}`} className="rounded-xl border border-border bg-muted/40 px-4 py-3">
                      <p className="font-mono text-xs break-all">{item.url}</p>
                      <p className="mt-1 text-muted-foreground">
                        Similarity {Math.round(item.similarity * 100)}% · {item.kind === "exact" ? "Exact duplicate" : "Near duplicate"}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">Site-wide duplicate analysis requires multiple crawled pages.</p>
              )}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <h2 className="text-sm font-semibold text-foreground">Content findings</h2>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search name, category, evidence, message"
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

            {content.limitations?.length ? (
              <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
                <h2 className="text-sm font-semibold text-foreground">Limitations</h2>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-muted-foreground">
                  {content.limitations.map((item) => (
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

function CheckDetail({ check }: { check: ContentCheck }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-lg font-semibold text-foreground">{check.name}</h2>
      <dl className="mt-4 space-y-3 text-sm">
        <Detail label="Status" value={statusLabel(check.status)} />
        <Detail label="Category" value={capitalize(check.group.replace("_", " "))} />
        <Detail label="Severity" value={check.status === "pass" || check.status === "not_applicable" ? "—" : capitalize(check.severity)} />
        <Detail label="Evidence" value={check.detected || "—"} />
        <Detail label="Affected content" value={check.selector || (check.affected_element_count ? String(check.affected_element_count) : "—")} />
        <Detail label="Why it matters" value={check.why || check.message} />
        {check.recommendation ? <Detail label="Recommendation" value={check.recommendation} /> : null}
      </dl>
    </section>
  );
}

function Bar({ label, percent }: { label: string; percent: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
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

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-foreground">{value}</dd>
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

function formatNumber(value?: number | boolean | null) {
  if (typeof value !== "number") return "—";
  return value.toLocaleString();
}

function categoryValue(content: ContentResultResponse, key: string) {
  const score = content.categories?.[key];
  return score == null ? "—" : String(score);
}

function signalValue(content: ContentResultResponse, key: string) {
  const signals = content.signals || {};
  if (key === "boilerplate_ratio") {
    return `${Math.round((signals.boilerplate_ratio || 0) * 100)}%`;
  }
  if (key === "thin_content") {
    return signals.thin_content ? "Low word count" : "No thin-content warning";
  }
  if (key === "duplicate_content") {
    return signals.duplicate_content ? "Similar pages found" : "Not detected";
  }
  if (key === "repeated_content") {
    return signals.repeated_content ? "Repeated blocks" : "Not detected";
  }
  if (key === "publication_date_detected") {
    return signals.publication_date_detected ? "Date detected" : "Not detected";
  }
  if (key === "author_detected") {
    return signals.author_detected ? "Author detected" : "Not detected";
  }
  return "—";
}
