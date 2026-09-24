"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import { buttonVariants } from "@/components/ui/button";
import {
  getCro,
  ScanApiError,
  type CroCheck,
  type CroResultResponse,
  type SeoSeverity,
} from "@/lib/scan/api";
import {
  categoryLabel,
  checkStatusLabel,
  conversionPathCopy,
  CRO_CRAWL_NOTE,
  CRO_METHODOLOGY,
  CRO_SCORE_NOTE,
  emptyCroCopy,
  filterFindings,
  scoreLabel,
} from "@/lib/scan/cro-ui";
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

export function CroDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [cro, setCro] = useState<CroResultResponse | null>(null);
  const [croError, setCroError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]["id"]>("all");
  const [severityFilter, setSeverityFilter] = useState<(typeof SEVERITY_FILTERS)[number]["id"]>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (scan?.status !== "completed") return;
    let cancelled = false;
    getCro(scanId)
      .then((result) => {
        if (!cancelled) {
          setCro(result);
          setCroError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setCroError(caught instanceof ScanApiError ? caught.message : "CRO analysis unavailable.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId]);

  const findings = useMemo(
    () => (cro?.findings?.length ? cro.findings : cro?.checks || []),
    [cro],
  );
  const selected = findings.find((check) => check.check_id === selectedId && check.page_url === findings.find((item) => item.check_id === selectedId)?.page_url) ?? findings.find((check) => check.check_id === selectedId) ?? null;
  const filtered = useMemo(
    () => filterFindings(findings, { status: statusFilter, severity: severityFilter, query }),
    [findings, statusFilter, severityFilter, query],
  );

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const empty = emptyCroCopy(running || !scan ? "incomplete" : croError ? "unavailable" : "loading");

  return (
    <ScanShell scanId={scanId} current="cro">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="CRO analysis unavailable." body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title={empty.title} body={scan?.current_step ?? empty.body} />
        ) : croError ? (
          <StateCard title="CRO analysis unavailable." body={croError} />
        ) : !cro ? (
          <StateCard title={emptyCroCopy("loading").title} body={emptyCroCopy("loading").body} />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Conversion Optimization</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">CRO</h1>
              <p className="mt-2 text-sm text-muted-foreground">{CRO_SCORE_NOTE}</p>
              <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Stat label="CRO score" value={scoreLabel(cro.score)} />
                <Stat label="Pages analyzed" value={String(cro.summary.pages_analyzed ?? cro.pages?.length ?? 0)} />
                <Stat label="Open CRO findings" value={String(cro.summary.open_findings ?? cro.issues?.length ?? 0)} />
                <Stat label="Primary CTA issues" value={String(cro.summary.cta_issues ?? 0)} />
                <Stat label="Form friction issues" value={String(cro.summary.form_issues ?? 0)} />
                <Stat label="Mobile conversion issues" value={String(cro.summary.mobile_issues ?? 0)} />
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Category breakdown</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {(cro.category_cards || Object.entries(cro.categories).map(([id, score]) => ({ id, name: id, score, finding_count: 0 }))).map((card) => (
                  <div key={card.id} className="rounded-xl border border-border bg-muted/40 p-4">
                    <p className="text-xs text-muted-foreground">{card.name}</p>
                    <p className="mt-1 text-2xl font-semibold">{scoreLabel(card.score)}</p>
                  </div>
                ))}
              </div>
            </section>

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
                      <tr
                        key={`${check.check_id}-${check.page_url}`}
                        className="border-b border-border/70 last:border-0"
                      >
                        <td className="py-2 pr-3 font-medium">
                          <button type="button" className="text-left underline-offset-4 hover:underline" onClick={() => setSelectedId(check.check_id)}>
                            {check.name}
                          </button>
                        </td>
                        <td className="py-2 pr-3 text-muted-foreground">{categoryLabel(check.group)}</td>
                        <td className="py-2 pr-3 text-muted-foreground">{check.severity}</td>
                        <td className="py-2 pr-3 font-mono text-xs text-muted-foreground">{check.page_url}</td>
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
                      <th className="py-2 pr-3 font-medium">CRO Score</th>
                      <th className="py-2 pr-3 font-medium">CTA</th>
                      <th className="py-2 pr-3 font-medium">Forms</th>
                      <th className="py-2 pr-3 font-medium">Conversion Path</th>
                      <th className="py-2 font-medium">Issues</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(cro.pages || []).map((page) => (
                      <tr key={page.page_id || page.url} className="border-b border-border/70 last:border-0">
                        <td className="py-2 pr-3 font-mono text-xs">
                          {page.page_id ? (
                            <Link href={`/scan/${scanId}/pages/${page.page_id}`} className="underline-offset-4 hover:underline">
                              {page.url}
                            </Link>
                          ) : (
                            page.url
                          )}
                        </td>
                        <td className="py-2 pr-3 text-muted-foreground">{page.page_type}</td>
                        <td className="py-2 pr-3">{scoreLabel(page.score)}</td>
                        <td className="py-2 pr-3">{checkStatusLabel(page.cta_status || undefined)}</td>
                        <td className="py-2 pr-3">{checkStatusLabel(page.forms_status || undefined)}</td>
                        <td className="py-2 pr-3">{checkStatusLabel(page.conversion_path_status || undefined)}</td>
                        <td className="py-2">{page.issue_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">CTA explorer</h2>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs text-muted-foreground">
                      <th className="py-2 pr-3 font-medium">CTA Text</th>
                      <th className="py-2 pr-3 font-medium">Page</th>
                      <th className="py-2 pr-3 font-medium">Type</th>
                      <th className="py-2 pr-3 font-medium">Visibility</th>
                      <th className="py-2 pr-3 font-medium">Destination</th>
                      <th className="py-2 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(cro.ctas || []).map((item, index) => (
                      <tr key={`${item.text}-${item.page_url}-${index}`} className="border-b border-border/70 last:border-0">
                        <td className="py-2 pr-3 font-medium">{item.text || "Potential CTA"}</td>
                        <td className="py-2 pr-3 font-mono text-xs text-muted-foreground">{item.page_url}</td>
                        <td className="py-2 pr-3 text-muted-foreground">{item.kind}</td>
                        <td className="py-2 pr-3 text-muted-foreground">{item.visibility}</td>
                        <td className="py-2 pr-3 text-muted-foreground">{item.destination}</td>
                        <td className="py-2">{item.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!cro.ctas?.length ? <p className="mt-3 text-sm text-muted-foreground">No CTA elements were detected on analyzed pages.</p> : null}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Form explorer</h2>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs text-muted-foreground">
                      <th className="py-2 pr-3 font-medium">Page</th>
                      <th className="py-2 pr-3 font-medium">Form Purpose</th>
                      <th className="py-2 pr-3 font-medium">Fields</th>
                      <th className="py-2 pr-3 font-medium">Submit Text</th>
                      <th className="py-2 pr-3 font-medium">Mobile Status</th>
                      <th className="py-2 font-medium">Issues</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(cro.forms || []).map((item, index) => (
                      <tr key={`${item.page_url}-${index}`} className="border-b border-border/70 last:border-0">
                        <td className="py-2 pr-3 font-mono text-xs">{item.page_url}</td>
                        <td className="py-2 pr-3">{item.purpose || "Unknown"}</td>
                        <td className="py-2 pr-3">{item.fields}</td>
                        <td className="py-2 pr-3">{item.submit_text || "—"}</td>
                        <td className="py-2 pr-3">{item.mobile_status || "Unavailable"}</td>
                        <td className="py-2">{item.issue_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!cro.forms?.length ? <p className="mt-3 text-sm text-muted-foreground">No forms were detected on analyzed pages.</p> : null}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Conversion path</h2>
              {(cro.conversion_paths || []).map((path, index) => (
                <div key={index} className="mt-3 text-sm">
                  {path.nodes?.length ? (
                    <ol className="space-y-1">
                      {path.nodes.map((node, nodeIndex) => (
                        <li key={node.url}>
                          {nodeIndex > 0 ? <p className="pl-3 text-muted-foreground">↓</p> : null}
                          <span className="font-medium">{node.page_type || "page"}</span>
                          <span className="ml-2 font-mono text-xs text-muted-foreground">{node.url}</span>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="text-muted-foreground">{conversionPathCopy(path.nodes, path.message)}</p>
                  )}
                </div>
              ))}
            </section>

            {cro.screenshots?.length ? (
              <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <h2 className="text-sm font-semibold text-foreground">Viewport evidence</h2>
                <p className="mt-1 text-sm text-muted-foreground">Desktop and mobile initial viewports from the UI/UX scan. No visual ranking is applied.</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {cro.screenshots.map((shot) => (
                    <figure key={shot.viewport} className="rounded-xl border border-border bg-muted/30 p-2">
                      <figcaption className="px-1 pb-2 text-xs text-muted-foreground">{shot.viewport}</figcaption>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img alt="" src={`/api/scans/${scanId}/uiux/screenshots/${shot.viewport}`} className="w-full rounded-lg border border-border" />
                    </figure>
                  ))}
                </div>
              </section>
            ) : null}

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Methodology</h2>
              <p className="mt-2 text-sm text-muted-foreground">{cro.methodology || CRO_METHODOLOGY}</p>
              <p className="mt-2 text-sm text-muted-foreground">{cro.crawl_note || CRO_CRAWL_NOTE}</p>
              {cro.viewports ? (
                <p className="mt-2 text-sm text-muted-foreground">
                  Viewports: desktop {cro.viewports.desktop?.width}×{cro.viewports.desktop?.height}, tablet {cro.viewports.tablet?.width}×{cro.viewports.tablet?.height}, mobile {cro.viewports.mobile?.width}×{cro.viewports.mobile?.height}.
                </p>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-2">
                <Link href={`/scan/${scanId}/issues?category=CRO`} className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}>
                  CRO issues
                </Link>
                <Link href={`/scan/${scanId}/recommendations?category=CRO`} className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}>
                  CRO recommendations
                </Link>
              </div>
            </section>
          </>
        )}
      </div>
    </ScanShell>
  );
}

function FindingDetail({ scanId, check }: { scanId: string; check: CroCheck }) {
  return (
    <div className="mt-4 rounded-xl border border-border bg-muted/40 p-4 text-sm">
      <p className="font-medium">{check.name}</p>
      <p className="mt-2 text-muted-foreground">{check.message}</p>
      {check.detected ? <p className="mt-2 font-mono text-xs">Evidence: {check.detected}</p> : null}
      {check.selector ? <p className="mt-1 font-mono text-xs">Selector: {check.selector}</p> : null}
      {check.recommendation ? <p className="mt-2">{check.recommendation}</p> : null}
      <p className="mt-3 font-mono text-xs text-muted-foreground">{check.page_url}</p>
      <Link href={`/scan/${scanId}/issues?issue_key=${encodeURIComponent(check.check_id)}`} className="mt-3 inline-block text-xs underline-offset-4 hover:underline">
        Open related issues
      </Link>
    </div>
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
      <h1 className="text-lg font-semibold text-foreground">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </section>
  );
}
