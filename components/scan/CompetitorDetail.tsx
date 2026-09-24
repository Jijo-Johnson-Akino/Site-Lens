"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import { buttonVariants } from "@/components/ui/button";
import { getCompetitor, rescanCompetitor, ScanApiError, type CompetitorDetailResponse } from "@/lib/scan/api";
import { COMPETITOR_LIMITATIONS, competitorStatusLabel, displayCell, formatTimestamp } from "@/lib/scan/competitors-ui";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

export function CompetitorDetailView({ scanId, competitorId }: { scanId: string; competitorId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [payload, setPayload] = useState<CompetitorDetailResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (scan?.status !== "completed") return;
    let cancelled = false;
    getCompetitor(scanId, competitorId)
      .then((result) => {
        if (!cancelled) {
          setPayload(result);
          setLoadError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setLoadError(caught instanceof ScanApiError ? caught.message : "Competitor not found.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId, competitorId]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const item = payload?.competitor;
  const snapshot = payload?.snapshot;
  const categories = snapshot?.categories || {};

  return (
    <ScanShell scanId={scanId} current="competitors">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <p className="text-sm">
          <Link href={`/scan/${scanId}/competitors`} className="text-muted-foreground hover:text-foreground hover:underline">
            ← Competitors
          </Link>
        </p>
        {failed ? (
          <StateCard title="Competitor unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <StateCard title="Loading competitor" body={scan?.current_step ?? "Loading scan status…"} />
        ) : loadError ? (
          <StateCard title="Competitor not found." body={loadError} />
        ) : !item ? (
          <StateCard title="Loading competitor" body="Fetching competitor scan summary." />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
              <h1 className="text-2xl font-semibold tracking-tight text-foreground">{item.name}</h1>
              <p className="mt-2 font-mono text-xs text-muted-foreground">{item.normalized_url}</p>
              <p className="mt-4 text-sm">Status: {competitorStatusLabel(item.status)}</p>
              <p className="mt-1 text-sm text-muted-foreground">Scanned {formatTimestamp(item.completed_at || item.created_at)}</p>
              {item.status === "failed" ? <p className="mt-3 text-sm text-critical">Competitor scan failed. {item.error?.message || "Unable to retrieve the website."}</p> : null}
              <div className="mt-4 flex flex-wrap gap-2">
                <Link href={`/scan/${item.competitor_scan_id}`} className={cn(buttonVariants(), "h-9 px-3")}>
                  Open full scan
                </Link>
                <Link href={`/scan/${item.competitor_scan_id}/pages`} className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}>
                  Pages
                </Link>
                <Link href={`/scan/${item.competitor_scan_id}/issues`} className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}>
                  Issues
                </Link>
                <Link href={`/scan/${item.competitor_scan_id}/recommendations`} className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}>
                  Recommendations
                </Link>
                <Link href={`/scan/${item.competitor_scan_id}/architecture`} className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}>
                  Architecture
                </Link>
                <button
                  type="button"
                  className={cn(buttonVariants({ variant: "outline" }), "h-9 px-3")}
                  disabled={busy}
                  onClick={() => {
                    setBusy(true);
                    rescanCompetitor(scanId, competitorId)
                      .then((result) => setPayload((current) => (current ? { ...current, competitor: result.competitor } : current)))
                      .catch(() => undefined)
                      .finally(() => setBusy(false));
                  }}
                >
                  {item.status === "failed" ? "Retry" : "Rescan"}
                </button>
              </div>
            </section>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Category scores</h2>
              <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                {Object.entries(categories).map(([key, value]) => (
                  <div key={key} className="rounded-xl border border-border bg-muted/40 p-4">
                    <dt className="text-xs text-muted-foreground">{value && "label" in value ? String((value as { label?: string }).label || key) : key}</dt>
                    <dd className="mt-1 text-lg font-semibold">{displayCell(Boolean(value?.available), value?.score)}</dd>
                  </div>
                ))}
              </dl>
            </section>
            <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-foreground">Coverage</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Pages crawled: {displayCell(Boolean(snapshot?.pages?.available), snapshot?.pages?.crawled)}. Issue types:{" "}
                {displayCell(Boolean(snapshot?.issues?.available), snapshot?.issues?.total)}.
              </p>
            </section>
            {snapshot?.screenshots?.length ? (
              <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <h2 className="text-sm font-semibold text-foreground">Screenshots</h2>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  {snapshot.screenshots.map((shot) => (
                    <figure key={shot.url}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img alt="" src={shot.url} className="w-full rounded-lg border border-border" />
                      <figcaption className="mt-1 text-xs text-muted-foreground">{shot.viewport}</figcaption>
                    </figure>
                  ))}
                </div>
              </section>
            ) : null}
            <p className="text-xs text-muted-foreground">{COMPETITOR_LIMITATIONS}</p>
          </>
        )}
      </div>
    </ScanShell>
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
