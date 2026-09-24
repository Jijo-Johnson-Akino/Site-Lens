"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import { buttonVariants } from "@/components/ui/button";
import {
  getTrust,
  getTrustPage,
  ScanApiError,
  type SeoSeverity,
  type TrustCheck,
  type TrustPageDetailResponse,
  type TrustResultResponse,
} from "@/lib/scan/api";
import {
  authorSummary,
  categoryLabel,
  checkStatusLabel,
  emptyTrustCopy,
  filterFindings,
  passedSignalMessages,
  policyDetectedLabel,
  scoreLabel,
  TRUST_CRAWL_NOTE,
  TRUST_METHODOLOGY,
  TRUST_SCORE_NOTE,
} from "@/lib/scan/trust-ui";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

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

export function TrustDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [trust, setTrust] = useState<TrustResultResponse | null>(null);
  const [trustError, setTrustError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]["id"]>("all");
  const [severityFilter, setSeverityFilter] = useState<(typeof SEVERITY_FILTERS)[number]["id"]>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pageDetail, setPageDetail] = useState<TrustPageDetailResponse | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  useEffect(() => {
    if (scan?.status !== "completed") return;
    let cancelled = false;
    getTrust(scanId)
      .then((result) => {
        if (!cancelled) {
          setTrust(result);
          setTrustError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setTrustError(caught instanceof ScanApiError ? caught.message : "Trust & Credibility analysis unavailable.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId]);

  const findings = useMemo(() => (trust?.findings?.length ? trust.findings : trust?.checks || []), [trust]);
  const selected =
    findings.find((check) => check.check_id === selectedId && check.page_url === findings.find((item) => item.check_id === selectedId)?.page_url) ??
    findings.find((check) => check.check_id === selectedId) ??
    null;
  const filtered = useMemo(
    () => filterFindings(findings, { status: statusFilter, severity: severityFilter, query }),
    [findings, statusFilter, severityFilter, query],
  );

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const empty = emptyTrustCopy(running || !scan ? "incomplete" : trustError ? "unavailable" : "loading");

  function openPage(pageId: string | null | undefined) {
    if (!pageId) return;
    setPageError(null);
    getTrustPage(scanId, pageId)
      .then(setPageDetail)
      .catch((caught) => {
        setPageDetail(null);
        setPageError(caught instanceof ScanApiError ? caught.message : "Unavailable");
      });
  }

  return (
    <ScanShell scanId={scanId} current="trust">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="Trust & Credibility analysis unavailable." body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title={empty.title} body={scan?.current_step ?? empty.body} />
        ) : trustError ? (
          <StateCard title="Trust & Credibility analysis unavailable." body={trustError} />
        ) : !trust ? (
          <StateCard title={emptyTrustCopy("loading").title} body={emptyTrustCopy("loading").body} />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Trust & Credibility</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Trust & Credibility</h1>
              <p className="mt-2 text-sm text-muted-foreground">{TRUST_SCORE_NOTE}</p>
              <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Stat label="Trust Signals Score" value={scoreLabel(trust.score)} />
                <Stat label="Pages analyzed" value={String(trust.summary.pages_analyzed ?? trust.pages?.length ?? 0)} />
                <Stat label="Identity signals" value={String(trust.summary.identity_signals ?? 0)} />
                <Stat label="Contact signals" value={String(trust.summary.contact_signals ?? 0)} />
                <Stat label="Policy signals" value={String(trust.summary.policy_signals ?? 0)} />
                <Stat label="Authorship signals" value={String(trust.summary.authorship_signals ?? 0)} />
                <Stat label="Social proof signals" value={String(trust.summary.social_proof_signals ?? 0)} />
              </div>
              <p className="mt-4 text-sm text-muted-foreground">{TRUST_METHODOLOGY}</p>
              <p className="mt-2 text-sm text-muted-foreground">{TRUST_CRAWL_NOTE}</p>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Observable Signal Coverage</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {(trust.category_cards || Object.entries(trust.categories).map(([id, score]) => ({ id, name: id, score, finding_count: 0 }))).map((card) => (
                  <div key={card.id} className="rounded-xl border border-border bg-muted/40 p-4">
                    <p className="text-xs text-muted-foreground">{card.name}</p>
                    <p className="mt-1 text-2xl font-semibold">{scoreLabel(card.score)}</p>
                    <p className="mt-1 text-xs text-muted-foreground">Observable Signal Coverage</p>
                  </div>
                ))}
              </div>
            </section>

            <ExplorerTable
              title="Signal explorer"
              columns={["Signal", "Category", "Page", "Evidence", "Status"]}
              rows={(trust.signals || []).map((row) => [row.signal, categoryLabel(row.category), row.page_url, row.evidence || "—", checkStatusLabel(row.status)])}
              empty="No relevant trust signals were detected in the available pages."
            />

            <ExplorerTable
              title="Potential gaps"
              columns={["Signal", "Category", "Page", "Evidence", "Status"]}
              rows={(trust.gaps || []).map((row) => [row.signal, categoryLabel(row.category), row.page_url, row.evidence || "—", checkStatusLabel(row.status)])}
              empty="No potential gaps were recorded from the crawled pages."
              note="Missing detection is limited to the SiteLens crawl and is not proof of wrongdoing."
            />

            <ExplorerTable
              title="Social proof explorer"
              columns={["Type", "Page", "Evidence", "Detected"]}
              rows={(trust.social_proof || []).map((row) => [row.kind, row.page_url, row.evidence, row.detected ? (row.potential ? "Potential" : "Detected") : "Not detected within crawl"])}
              empty="No social-proof sections were detected. That is not a failure for every website type."
              note="Detected social proof is not verified for authenticity."
            />

            <ExplorerTable
              title="Policy explorer"
              columns={["Policy", "Detected", "Page"]}
              rows={(trust.policies || []).map((row) => [row.policy, policyDetectedLabel(row.detected, row.note), row.page_url || "—"])}
              empty="No policy pages were inspected."
            />

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Author explorer</h2>
              {(trust.authors || []).length ? <p className="mt-1 text-sm text-muted-foreground">{authorSummary(trust.authors)}</p> : null}
              <div className="mt-4 overflow-x-auto">
                {(trust.authors || []).length ? (
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-border text-xs text-muted-foreground">
                        <th className="py-2 pr-3 font-medium">Article</th>
                        <th className="py-2 pr-3 font-medium">Author</th>
                        <th className="py-2 pr-3 font-medium">Publication date</th>
                        <th className="py-2 pr-3 font-medium">Modified date</th>
                        <th className="py-2 font-medium">Author schema</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(trust.authors || []).map((row) => (
                        <tr key={`${row.page_id || row.page_url}`} className="border-b border-border/70">
                          <td className="py-2 pr-3">{row.title || row.page_url}</td>
                          <td className="py-2 pr-3">{row.available === false ? "Unavailable" : row.author || "Unavailable"}</td>
                          <td className="py-2 pr-3">{row.publication_date || "Unavailable"}</td>
                          <td className="py-2 pr-3">{row.modified_date || "Unavailable"}</td>
                          <td className="py-2">{row.author_schema || "Unavailable"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="text-sm text-muted-foreground">No article pages were available to inspect.</p>
                )}
              </div>
            </section>

            <ExplorerTable
              title="Entity consistency"
              columns={["Field", "Visible", "Schema", "Footer", "About", "Status"]}
              rows={(trust.consistency || []).map((row) => [row.field, row.visible || "Unavailable", row.schema_value || "Unavailable", row.footer || "Unavailable", row.about || "Unavailable", row.status])}
              empty="Organization names could not be compared."
              note="SiteLens does not decide which published value is correct."
            />

            <ExplorerTable
              title="Security signals"
              columns={["Signal", "Detected", "Evidence"]}
              rows={(trust.security || []).map((row) => [row.signal, row.detected ? "Detected" : "Not detected within crawl", row.evidence])}
              empty="No security presentation signals were recorded."
              note="HTTPS describes the scanned URL scheme. It is not a security certification."
            />

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <h2 className="text-sm font-semibold text-foreground">Findings</h2>
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search findings" className="h-9 rounded-lg border border-input bg-transparent px-3 text-sm" />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {STATUS_FILTERS.map((item) => (
                  <button key={item.id} type="button" className={cn("h-8 rounded-full border px-3 text-xs", statusFilter === item.id ? "border-foreground" : "border-border")} onClick={() => setStatusFilter(item.id)}>
                    {item.label}
                  </button>
                ))}
                {SEVERITY_FILTERS.map((item) => (
                  <button key={item.id} type="button" className={cn("h-8 rounded-full border px-3 text-xs", severityFilter === item.id ? "border-foreground" : "border-border")} onClick={() => setSeverityFilter(item.id)}>
                    {item.label}
                  </button>
                ))}
              </div>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs text-muted-foreground">
                      <th className="py-2 pr-3 font-medium">Finding</th>
                      <th className="py-2 pr-3 font-medium">Category</th>
                      <th className="py-2 pr-3 font-medium">Severity</th>
                      <th className="py-2 pr-3 font-medium">Page</th>
                      <th className="py-2 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((check) => (
                      <tr key={`${check.check_id}-${check.page_url}`} className="border-b border-border/70">
                        <td className="py-2 pr-3">
                          <button type="button" className="text-left font-medium text-foreground underline-offset-2 hover:underline" onClick={() => setSelectedId(check.check_id)}>
                            {check.name}
                          </button>
                        </td>
                        <td className="py-2 pr-3">{categoryLabel(check.group)}</td>
                        <td className="py-2 pr-3 capitalize">{check.severity}</td>
                        <td className="py-2 pr-3 font-mono text-xs">{check.page_url}</td>
                        <td className="py-2">{checkStatusLabel(check.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {selected ? <FindingDetail scanId={scanId} check={selected} /> : null}
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Pages</h2>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs text-muted-foreground">
                      <th className="py-2 pr-3 font-medium">Page</th>
                      <th className="py-2 pr-3 font-medium">Type</th>
                      <th className="py-2 pr-3 font-medium">Score</th>
                      <th className="py-2 font-medium">Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(trust.pages || []).map((page) => (
                      <tr key={page.page_id || page.url} className="border-b border-border/70">
                        <td className="py-2 pr-3 font-mono text-xs">{page.url}</td>
                        <td className="py-2 pr-3">{page.page_type}</td>
                        <td className="py-2 pr-3">{scoreLabel(page.score)}</td>
                        <td className="py-2">
                          <button type="button" className="text-sm underline-offset-2 hover:underline" onClick={() => openPage(page.page_id)}>
                            View page trust
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {pageError ? <p className="mt-3 text-sm text-muted-foreground">{pageError}</p> : null}
              {pageDetail ? <PageTrustDetail detail={pageDetail} /> : null}
            </section>

            <div className="flex flex-wrap gap-3">
              <Link href={`/scan/${scanId}/issues?category=Trust`} className={cn(buttonVariants(), "h-10 px-4")}>
                View Trust issues
              </Link>
              <Link href={`/scan/${scanId}/recommendations?category=Trust`} className={cn(buttonVariants({ variant: "outline" }), "h-10 px-4")}>
                View Trust recommendations
              </Link>
            </div>
          </>
        )}
      </div>
    </ScanShell>
  );
}

function PageTrustDetail({ detail }: { detail: TrustPageDetailResponse }) {
  const groups: Array<{ id: string; label: string }> = [
    { id: "identity", label: "Identity signals" },
    { id: "contact", label: "Contact signals" },
    { id: "authorship", label: "Authorship signals" },
    { id: "social_proof", label: "Social proof" },
    { id: "policies", label: "Policies" },
    { id: "business", label: "Business information" },
    { id: "security", label: "Security signals" },
    { id: "consistency", label: "Consistency findings" },
  ];
  return (
    <div className="mt-4 rounded-xl border border-border bg-muted/40 p-4">
      <p className="text-sm font-medium">{detail.page.url}</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Page Trust Signals Score: {scoreLabel(detail.page.score)} · {detail.page.page_type} · {detail.checks.length} checks
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {groups.map((group) => {
          const messages = passedSignalMessages(detail.checks, group.id);
          return (
            <div key={group.id}>
              <p className="text-xs font-medium text-muted-foreground">{group.label}</p>
              <p className="mt-1 text-sm text-foreground">{messages[0] || "Unavailable"}</p>
              {messages.length > 1 ? <p className="mt-1 text-xs text-muted-foreground">{messages.length} signals on this page.</p> : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FindingDetail({ scanId, check }: { scanId: string; check: TrustCheck }) {
  return (
    <div className="mt-4 rounded-xl border border-border bg-muted/40 p-4">
      <p className="text-sm font-medium">{check.name}</p>
      <p className="mt-2 text-sm text-muted-foreground">{check.message}</p>
      {check.recommendation ? <p className="mt-2 text-sm text-muted-foreground">{check.recommendation}</p> : null}
      <div className="mt-3 flex flex-wrap gap-3">
        <Link href={`/scan/${scanId}/issues?issue_key=${encodeURIComponent(check.check_id)}`} className="text-sm underline-offset-2 hover:underline">
          Related issues
        </Link>
        <Link href={`/scan/${scanId}/recommendations?category=Trust`} className="text-sm underline-offset-2 hover:underline">
          Related recommendations
        </Link>
      </div>
    </div>
  );
}

function ExplorerTable({
  title,
  columns,
  rows,
  empty,
  note,
}: {
  title: string;
  columns: string[];
  rows: string[][];
  empty: string;
  note?: string;
}) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      {note ? <p className="mt-1 text-sm text-muted-foreground">{note}</p> : null}
      <div className="mt-4 overflow-x-auto">
        {rows.length ? (
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                {columns.map((column) => (
                  <th key={column} className="py-2 pr-3 font-medium">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${title}-${index}`} className="border-b border-border/70">
                  {row.map((cell, cellIndex) => (
                    <td key={`${title}-${index}-${cellIndex}`} className="py-2 pr-3">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-muted-foreground">{empty}</p>
        )}
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-muted/40 p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function StateCard({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </section>
  );
}
