"use client";

import { useEffect, useMemo, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import {
  getUiux,
  ScanApiError,
  type SeoCheckStatus,
  type UiuxCheck,
  type UiuxResultResponse,
} from "@/lib/scan/api";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

const CATEGORY_ORDER = [
  ["responsive", "Responsive Design"],
  ["layout", "Layout"],
  ["navigation", "Navigation"],
  ["interactive", "Interactive Elements"],
  ["typography", "Typography"],
  ["content", "Content"],
  ["forms", "Forms"],
  ["images", "Images"],
] as const;

const FINDING_GROUPS = [
  ["responsive", "Responsive experience"],
  ["layout", "Layout"],
  ["navigation", "Navigation"],
  ["interactive", "Interactive elements"],
  ["typography", "Typography"],
  ["content", "Content presentation"],
  ["forms", "Forms"],
  ["images", "Images"],
] as const;

const VIEWPORT_TABS = [
  ["desktop", "Desktop"],
  ["tablet", "Tablet"],
  ["mobile", "Mobile"],
  ["mobile_compact", "Compact mobile"],
] as const;

const FILTERS: Array<{ id: "all" | "pass" | "warning" | "fail"; label: string }> = [
  { id: "all", label: "All" },
  { id: "pass", label: "Passed" },
  { id: "warning", label: "Warnings" },
  { id: "fail", label: "Failed" },
];

function checkKey(check: UiuxCheck) {
  return `${check.check_id}:${check.viewport}`;
}

export function UiuxDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [uiux, setUiux] = useState<UiuxResultResponse | null>(null);
  const [uiuxError, setUiuxError] = useState<string | null>(null);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [viewportTab, setViewportTab] = useState<string>("desktop");

  useEffect(() => {
    if (scan?.status !== "completed") {
      return;
    }
    let cancelled = false;
    getUiux(scanId)
      .then((result) => {
        if (!cancelled) {
          setUiux(result);
          setUiuxError(null);
          const first = result.screenshots[0]?.viewport || Object.keys(result.viewports)[0];
          if (first) {
            setViewportTab(first);
          }
        }
      })
      .catch((caught) => {
        if (cancelled) {
          return;
        }
        setUiuxError(caught instanceof ScanApiError ? caught.message : "Unable to load UI/UX results.");
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId]);

  const selected = uiux?.checks.find((check) => checkKey(check) === selectedKey) ?? null;
  const filtered = useMemo(() => {
    if (!uiux) {
      return [];
    }
    if (filter === "all") {
      return uiux.checks;
    }
    return uiux.checks.filter((check) => check.status === filter);
  }, [uiux, filter]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const screenshot = uiux?.screenshots.find((item) => item.viewport === viewportTab);
  const viewportMeta = uiux?.viewports[viewportTab];

  return (
    <ScanShell scanId={scanId} current="uiux">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="UI/UX analysis unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title="Running UI/UX analysis" body={scan?.current_step ?? "Loading scan status…"} />
        ) : uiuxError ? (
          <StateCard title="Unable to load UI/UX results" body={uiuxError} />
        ) : !uiux ? (
          <StateCard title="Loading UI/UX results" body="Fetching the analysis for this scan." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">UI / UX</p>
              <p className="mt-2 text-sm text-muted-foreground">Website Experience</p>
              <p className="mt-2 text-5xl font-semibold tracking-tight text-foreground">
                {uiux.score} <span className="text-2xl font-medium text-muted-foreground">/ 100</span>
              </p>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground">
                This score is based on rendered layout measurements across desktop, tablet, and mobile viewports. It
                reports observable facts such as overflow, clipping, and missing controls — not subjective design opinions.
              </p>
              <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MiniStat label="Passed" value={uiux.summary.passed} />
                <MiniStat label="Warnings" value={uiux.summary.warnings} />
                <MiniStat label="Failed" value={uiux.summary.failed} />
                <MiniStat label="Not applicable" value={uiux.summary.not_applicable} />
              </dl>
            </section>

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h2 className="text-sm font-semibold text-foreground">Category scores</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {CATEGORY_ORDER.map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3">
                    <p className="text-sm text-muted-foreground">{label}</p>
                    <p className="text-sm font-semibold text-foreground">
                      {uiux.categories[key] == null ? "—" : uiux.categories[key]}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <ScreenshotViewer
              uiux={uiux}
              active={viewportTab}
              onChange={setViewportTab}
              screenshot={screenshot}
              viewportMeta={viewportMeta}
            />

            <Findings checks={uiux.checks} onSelect={setSelectedKey} />

            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="text-sm font-semibold text-foreground">UI/UX checks</h2>
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
                <table className="w-full min-w-[40rem] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs tracking-wide text-muted-foreground uppercase">
                      <th className="py-2 pr-3 font-medium">Check</th>
                      <th className="py-2 pr-3 font-medium">Viewport</th>
                      <th className="py-2 pr-3 font-medium">Status</th>
                      <th className="py-2 font-medium">Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((check) => (
                      <tr
                        key={checkKey(check)}
                        className={cn(
                          "cursor-pointer border-b border-border/80 last:border-0 hover:bg-muted/40",
                          selectedKey === checkKey(check) && "bg-muted/60",
                        )}
                        onClick={() => setSelectedKey(checkKey(check))}
                      >
                        <td className="py-3 pr-3 text-foreground">{check.name}</td>
                        <td className="py-3 pr-3 capitalize text-muted-foreground">{check.viewport}</td>
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

            {selected ? <CheckDetail check={selected} viewport={uiux.viewports[selected.viewport]} /> : null}
          </>
        )}
      </div>
    </ScanShell>
  );
}

function ScreenshotViewer({
  uiux,
  active,
  onChange,
  screenshot,
  viewportMeta,
}: {
  uiux: UiuxResultResponse;
  active: string;
  onChange: (viewport: string) => void;
  screenshot?: UiuxResultResponse["screenshots"][number];
  viewportMeta?: UiuxResultResponse["viewports"][string];
}) {
  const available = VIEWPORT_TABS.filter(([id]) => uiux.viewports[id] || uiux.screenshots.some((item) => item.viewport === id));
  const width = screenshot?.width ?? viewportMeta?.width;
  const height = screenshot?.height ?? viewportMeta?.height;
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-sm font-semibold text-foreground">Screenshots</h2>
        {width && height ? (
          <p className="font-mono text-xs text-muted-foreground">
            {width} × {height}
          </p>
        ) : null}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {available.map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => onChange(id)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium",
              active === id
                ? "border-foreground/15 bg-foreground text-background"
                : "border-border bg-background text-muted-foreground hover:text-foreground",
            )}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="mt-4 overflow-hidden rounded-xl border border-border bg-muted/40">
        {screenshot?.url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={screenshot.url}
            alt={`${capitalize(active)} screenshot of the analyzed homepage`}
            className="mx-auto max-h-[70vh] w-full object-contain object-top"
          />
        ) : (
          <p className="px-4 py-16 text-center text-sm text-muted-foreground">Screenshot unavailable for this viewport.</p>
        )}
      </div>
    </section>
  );
}

function Findings({ checks, onSelect }: { checks: UiuxCheck[]; onSelect: (key: string) => void }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-sm font-semibold text-foreground">UI/UX findings</h2>
      <div className="mt-5 grid gap-6 lg:grid-cols-2">
        {FINDING_GROUPS.map(([group, title]) => {
          const items = checks.filter((check) => check.group === group && check.status !== "not_applicable");
          if (items.length === 0) {
            return null;
          }
          return (
            <div key={group}>
              <p className="text-xs font-medium tracking-[0.16em] text-muted-foreground uppercase">{title}</p>
              <ul className="mt-2 space-y-1.5">
                {items
                  .filter((check) => check.status !== "pass")
                  .concat(items.filter((check) => check.status === "pass").slice(0, 3))
                  .slice(0, 8)
                  .map((check) => {
                    const tone = check.status === "fail" ? "critical" : check.status === "warning" ? "warn" : "pass";
                    const mark = tone === "pass" ? "✓" : tone === "warn" ? "⚠" : "✕";
                    return (
                      <li key={checkKey(check)}>
                        <button
                          type="button"
                          className="text-left text-sm text-foreground hover:underline"
                          onClick={() => onSelect(checkKey(check))}
                        >
                          <span className={cn("mr-1.5", tone === "pass" ? "text-pass" : tone === "warn" ? "text-warn" : "text-critical")}>
                            {mark}
                          </span>
                          {check.message}
                        </button>
                      </li>
                    );
                  })}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function CheckDetail({
  check,
  viewport,
}: {
  check: UiuxCheck;
  viewport?: UiuxResultResponse["viewports"][string];
}) {
  const size = viewport ? `${viewport.width}×${viewport.height}` : null;
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h2 className="text-lg font-semibold text-foreground">{check.name}</h2>
      <dl className="mt-4 space-y-3 text-sm">
        <Detail label="Status" value={statusLabel(check.status)} />
        <Detail
          label="Viewport"
          value={size ? `${capitalize(check.viewport)} — ${size}` : capitalize(check.viewport)}
        />
        <Detail label="Page" value={check.page_url} mono />
        {check.affected_element ? <Detail label="Affected element" value={check.affected_element} mono /> : null}
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
