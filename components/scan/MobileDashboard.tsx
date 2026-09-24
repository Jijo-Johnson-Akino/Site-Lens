"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import {
  getMobile,
  ScanApiError,
  type MobileCheck,
  type MobileResultResponse,
  type SeoCheckStatus,
  type SeoSeverity,
} from "@/lib/scan/api";
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

const SHOT_TABS = [
  { id: "mobile_390", label: "390 × 844", kind: "viewport" },
  { id: "mobile_390_full", label: "390 × 844 full page", kind: "full" },
  { id: "mobile_375", label: "375 × 812", kind: "viewport" },
  { id: "mobile_375_full", label: "375 × 812 full page", kind: "full" },
] as const;

function yesNo(value: boolean | null | undefined) {
  if (value == null) {
    return "—";
  }
  return value ? "Yes" : "No";
}

function statusLabel(status: string | undefined) {
  if (status === "pass") {
    return "PASS";
  }
  if (status === "fail") {
    return "FAIL";
  }
  if (status === "warning") {
    return "WARNING";
  }
  return "N/A";
}

export function MobileDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [mobile, setMobile] = useState<MobileResultResponse | null>(null);
  const [mobileError, setMobileError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]["id"]>("all");
  const [severityFilter, setSeverityFilter] = useState<(typeof SEVERITY_FILTERS)[number]["id"]>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [shotTab, setShotTab] = useState<string>("mobile_390");

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getMobile(scanId)
      .then((result) => {
        if (!cancelled) {
          setMobile(result);
          setMobileError(null);
          const first = result.screenshots?.[0]?.viewport;
          if (first) {
            setShotTab(first);
          }
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setMobileError(caught instanceof ScanApiError ? caught.message : "Mobile analysis not available.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId]);

  const findings = mobile?.findings?.length ? mobile.findings : mobile?.checks || [];
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
      if (!needle) {
        return true;
      }
      const hay = `${check.name} ${check.group} ${check.message} ${check.selector || ""} ${check.recommendation || ""}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [findings, statusFilter, severityFilter, query]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const screenshot = mobile?.screenshots?.find((item) => item.viewport === shotTab);
  const env = mobile?.environment;
  const overview = mobile?.overview || {};

  return (
    <ScanShell scanId={scanId} current="mobile">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="Mobile analysis unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title="Running Mobile Analysis" body={scan?.current_step ?? "Loading scan status…"} />
        ) : mobileError ? (
          <StateCard title="Mobile analysis not available." body={mobileError} />
        ) : !mobile ? (
          <StateCard title="Loading mobile results" body="Fetching the mobile layout analysis for this scan." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Mobile</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Mobile</h1>
              <p className="mt-1 text-sm text-muted-foreground">Mobile website experience analysis</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                Automated analysis of responsive behavior and mobile-specific layout signals.
              </p>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Test Environment</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <Info label="Device" value={env?.device_profile === "mobile" ? "Mobile" : env?.device_profile || "—"} />
                <Info
                  label="Viewport"
                  value={
                    env?.viewport?.width && env?.viewport?.height
                      ? `${env.viewport.width} × ${env.viewport.height}`
                      : "390 × 844"
                  }
                />
                <Info label="Touch" value={env?.touch_enabled ? "Enabled" : env?.touch_enabled === false ? "Not detected" : "—"} />
                <Info label="Browser" value={env?.browser ? capitalize(env.browser) : "Chromium"} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Mobile Score</h2>
              <p className="mt-3 text-5xl font-semibold tracking-tight text-foreground">
                {mobile.score} <span className="text-2xl font-medium text-muted-foreground">/ 100</span>
              </p>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground">{mobile.narrative}</p>
              <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MiniStat label="Passed" value={mobile.summary.passed} />
                <MiniStat label="Warnings" value={mobile.summary.warnings} />
                <MiniStat label="Failed" value={mobile.summary.failed} />
                <MiniStat label="Not applicable" value={mobile.summary.not_applicable} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Mobile Overview</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <OverviewCard label="Horizontal Overflow" card={overview.overflow} />
                <OverviewCard label="Mobile Navigation" card={overview.navigation} />
                <OverviewCard label="Touch Targets" card={overview.touch} />
                <OverviewCard label="Viewport" card={overview.viewport} />
                <OverviewCard label="Content Visibility" card={overview.visibility} />
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Responsive Layout</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <Info label="Document Width" value={formatPx(mobile.viewport?.document_width)} />
                <Info label="Viewport Width" value={formatPx(mobile.viewport?.width)} />
                <Info label="Overflow" value={mobile.viewport?.horizontal_overflow ? `${mobile.viewport.overflow_px ?? "—"}px` : "None"} />
                <Info label="Affected Elements" value={String((mobile.layout?.overflowing_elements as unknown[] | undefined)?.length ?? 0)} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Touch Targets</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
                <Info label="Interactive Elements" value={String(mobile.touch_targets?.interactive_elements ?? 0)} />
                <Info label="Below Baseline" value={String(mobile.touch_targets?.below_baseline ?? 0)} />
                <Info label="Very Small" value={String(mobile.touch_targets?.very_small ?? 0)} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Mobile Navigation</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <Info label="Menu Detected" value={yesNo(mobile.navigation?.mobile_menu_detected)} />
                <Info label="Menu Tested" value={yesNo(mobile.navigation?.menu_tested)} />
                <Info label="Menu Visibility" value={statusLabel(overview.navigation?.status)} />
                <Info label="Menu Overflow" value={mobile.navigation?.overflow ? "Warning" : "Pass"} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Typography</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
                <Info label="Small Text Elements" value={String(mobile.typography?.small_text_elements ?? 0)} />
                <Info label="Clipped Text" value={String(mobile.typography?.clipped_text ?? 0)} />
                <Info label="Overflowing Headings" value={String(mobile.typography?.overflowing_headings ?? 0)} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Forms</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
                <Info label="Forms" value={String(mobile.forms?.forms ?? 0)} />
                <Info label="Overflowing Forms" value={String(mobile.forms?.overflowing_forms ?? 0)} />
                <Info label="Controls Outside Viewport" value={String(mobile.forms?.controls_outside_viewport ?? 0)} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Images & Tables</h2>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <Info label="Images overflowing" value={String(mobile.images?.overflowing ?? 0)} />
                <Info label="Images oversized" value={String(mobile.images?.oversized ?? 0)} />
                <Info label="Tables overflowing" value={String(mobile.tables?.overflowing ?? 0)} />
                <Info label="Tables responsive" value={String(mobile.tables?.responsive ?? 0)} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Screenshots</h2>
              <div className="mt-4 flex flex-wrap gap-2">
                {SHOT_TABS.map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setShotTab(tab.id)}
                    className={cn(
                      "rounded-full border px-3 py-1 text-xs font-medium",
                      shotTab === tab.id
                        ? "border-foreground/15 bg-foreground text-background"
                        : "border-border bg-background text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className="mt-4 overflow-hidden rounded-xl border border-border bg-muted/40">
                {screenshot?.url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={screenshot.url}
                    alt={`Mobile screenshot ${screenshot.viewport}`}
                    className="mx-auto max-h-[70vh] w-full object-contain object-top"
                  />
                ) : (
                  <p className="px-4 py-16 text-center text-sm text-muted-foreground">Screenshot unavailable.</p>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <h2 className="text-sm font-semibold text-foreground">Mobile Findings</h2>
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
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[44rem] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs tracking-wide text-muted-foreground uppercase">
                      <th className="py-2 pr-3 font-medium">Issue</th>
                      <th className="py-2 pr-3 font-medium">Category</th>
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
                        <td className="py-3 pr-3 capitalize text-muted-foreground">{check.group}</td>
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
                  <p className="py-6 text-center text-sm text-muted-foreground">No findings match these filters.</p>
                ) : null}
              </div>
            </section>

            {selected ? <CheckDetail check={selected} /> : null}

            <p className="text-sm text-muted-foreground">
              Mobile performance timings such as LCP are reported in{" "}
              <Link href={`/scan/${scanId}/performance`} className="underline underline-offset-2">
                Performance analysis
              </Link>
              .
            </p>

            {mobile.limitations?.length ? (
              <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
                <h2 className="text-sm font-semibold text-foreground">Limitations</h2>
                <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-muted-foreground">
                  {mobile.limitations.map((item) => (
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

function OverviewCard({
  label,
  card,
}: {
  label: string;
  card?: { status?: string; warnings?: number; failed?: number; passed?: number };
}) {
  const status = card?.status || "not_applicable";
  let value = statusLabel(status);
  if (status === "warning" && (card?.warnings || 0) > 0) {
    value = `${card?.warnings} warning${card?.warnings === 1 ? "" : "s"}`;
  }
  if (status === "fail" && (card?.failed || 0) > 0) {
    value = `${card?.failed} failed`;
  }
  return (
    <div className="rounded-xl border border-border bg-muted/40 px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold text-foreground">{value}</p>
    </div>
  );
}

function CheckDetail({ check }: { check: MobileCheck }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-sm font-semibold text-foreground">Finding Details</h2>
      <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
        <Info label="Issue" value={check.name} />
        <Info label="Category" value={capitalize(check.group)} />
        <Info label="Severity" value={check.status === "pass" || check.status === "not_applicable" ? "—" : capitalize(check.severity)} />
        <Info label="Viewport" value={check.viewport || "—"} />
        <Info label="Measured value" value={check.measured_value == null ? "—" : String(check.measured_value)} />
        <Info label="Expected value" value={check.expected_value == null ? "—" : String(check.expected_value)} />
        <Info label="Affected element" value={check.selector || check.affected_element || "—"} />
        <Info label="Affected count" value={String(check.affected_element_count || 0)} />
      </dl>
      <p className="mt-4 text-sm leading-6 text-foreground">{check.message}</p>
      {check.recommendation ? <p className="mt-3 text-sm leading-6 text-muted-foreground">{check.recommendation}</p> : null}
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

function StatusMark({ status }: { status: SeoCheckStatus | string }) {
  const label = status === "not_applicable" ? "N/A" : capitalize(status);
  return <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</span>;
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-muted/40 px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold text-foreground">{value}</p>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-all text-foreground">{value}</dd>
    </div>
  );
}

function StateCard({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h1 className="text-lg font-semibold text-foreground">{title}</h1>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p>
    </section>
  );
}

function formatPx(value: number | null | undefined) {
  if (typeof value !== "number") {
    return "—";
  }
  return `${value}px`;
}

function capitalize(value: string) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, " ") : value;
}
