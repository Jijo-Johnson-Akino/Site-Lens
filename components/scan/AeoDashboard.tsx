"use client";

import { useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import { getAeo, ScanApiError, type SeoCheck, type SeoCheckStatus, type AeoResultResponse } from "@/lib/scan/api";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const CATEGORY_ORDER = [
  ["entity_understanding", "Entity Understanding"],
  ["answer_readiness", "Answer Readiness"],
  ["question_coverage", "Question Coverage"],
  ["content_structure", "Content Structure"],
  ["semantic_structure", "Semantic Structure"],
  ["authorship", "Authorship"],
  ["organization_information", "Organization"],
  ["structured_information", "Structured Information"],
  ["extractability", "Extractability"],
] as const;

const FILTERS: Array<{ id: "all" | "pass" | "warning" | "fail"; label: string }> = [
  { id: "all", label: "All" },
  { id: "pass", label: "Passed" },
  { id: "warning", label: "Warnings" },
  { id: "fail", label: "Failed" },
];

export function AeoDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [aeo, setAeo] = useState<AeoResultResponse | null>(null);
  const [aeoError, setAeoError] = useState<string | null>(null);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [explainOpen, setExplainOpen] = useState(false);

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getAeo(scanId)
      .then((result) => {
        if (!cancelled) {
          setAeo(result);
          setAeoError(null);
        }
      })
      .catch((caught) => {
        if (cancelled) {
          return;
        }
        setAeoError(caught instanceof ScanApiError ? caught.message : "Unable to load AEO results.");
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId]);

  const selected = aeo?.checks.find((check) => check.check_id === selectedId) ?? null;
  const filtered = useMemo(() => {
    if (!aeo) {
      return [];
    }
    if (filter === "all") {
      return aeo.checks;
    }
    return aeo.checks.filter((check) => check.status === filter);
  }, [aeo, filter]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";

  return (
    <ScanShell scanId={scanId} current="aeo">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="AEO analysis unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title="Running AEO analysis" body={scan?.current_step ?? "Loading scan status…"} />
        ) : aeoError ? (
          <StateCard title="Unable to load AEO results" body={aeoError} />
        ) : !aeo ? (
          <StateCard title="Loading AEO results" body="Fetching the analysis for this scan." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">AEO / AI Search</p>
              <p className="mt-2 text-sm text-muted-foreground">AI Search Readiness</p>
              <p className="mt-2 text-5xl font-semibold tracking-tight text-foreground">
                {aeo.score} <span className="text-2xl font-medium text-muted-foreground">/ 100</span>
              </p>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground">
                This score measures observable content and technical signals that can make website information easier for
                machine and answer-engine systems to interpret. It does not predict AI search rankings or citations.
              </p>
              <button
                type="button"
                className="mt-4 text-sm font-medium text-foreground underline-offset-4 hover:underline"
                onClick={() => setExplainOpen((open) => !open)}
                aria-expanded={explainOpen}
              >
                How is this score calculated?
              </button>
              {explainOpen ? (
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                  The AEO score is based on observable website signals including entity clarity, answer structure, semantic
                  content, structured data, authorship and content extractability. It is not a prediction of search ranking
                  or AI citation.
                </p>
              ) : null}
              <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MiniStat label="Passed" value={aeo.summary.passed} />
                <MiniStat label="Warnings" value={aeo.summary.warnings} />
                <MiniStat label="Failed" value={aeo.summary.failed} />
                <MiniStat label="Not applicable" value={aeo.summary.not_applicable} />
              </dl>
            </section>

            {aeo.insight ? (
              <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
                <h2 className="text-sm font-semibold tracking-[0.14em] text-foreground uppercase">AI readiness summary</h2>
                <p className="mt-3 whitespace-pre-line text-sm leading-6 text-muted-foreground">
                  {aeo.insight.replace(/^AI READINESS SUMMARY\n*/, "")}
                </p>
              </section>
            ) : null}

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Category scores</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {CATEGORY_ORDER.map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3">
                    <p className="text-sm text-muted-foreground">{label}</p>
                    <p className="text-sm font-semibold text-foreground">
                      {aeo.categories[key] == null ? "—" : aeo.categories[key]}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <Findings checks={aeo.checks} onSelect={setSelectedId} />

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="text-sm font-semibold text-foreground">AEO checks</h2>
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
                          {check.status === "pass" || check.status === "not_applicable" ? "—" : capitalize(check.severity)}
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

function Findings({ checks, onSelect }: { checks: SeoCheck[]; onSelect: (id: string) => void }) {
  const passed = checks.filter((check) => check.status === "pass").slice(0, 6);
  const warnings = checks.filter((check) => check.status === "warning");
  const failed = checks.filter((check) => check.status === "fail");
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-sm font-semibold text-foreground">AEO findings</h2>
      <div className="mt-4 grid gap-5 sm:grid-cols-3">
        <FindingList title="Passed" items={passed} tone="pass" onSelect={onSelect} />
        <FindingList title="Warnings" items={warnings} tone="warn" onSelect={onSelect} />
        <FindingList title="Failed" items={failed} tone="critical" onSelect={onSelect} />
      </div>
    </section>
  );
}

function FindingList({
  title,
  items,
  tone,
  onSelect,
}: {
  title: string;
  items: SeoCheck[];
  tone: "pass" | "warn" | "critical";
  onSelect: (id: string) => void;
}) {
  const mark = tone === "pass" ? "✓" : tone === "warn" ? "⚠" : "✕";
  return (
    <div>
      <p className="text-xs font-medium tracking-[0.16em] text-muted-foreground uppercase">{title}</p>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">None.</p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {items.map((check) => (
            <li key={check.check_id}>
              <button type="button" className="text-left text-sm text-foreground hover:underline" onClick={() => onSelect(check.check_id)}>
                <span className={cn("mr-1.5", tone === "pass" ? "text-pass" : tone === "warn" ? "text-warn" : "text-critical")}>
                  {mark}
                </span>
                {check.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
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
