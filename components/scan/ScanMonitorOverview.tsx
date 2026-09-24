"use client";

import { Clock, Globe, Layers, Map, Timer } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { ScanStatusMessage } from "@/components/scan/ScanStatusMessage";
import type { ScanStatusResponse } from "@/lib/scan/api";
import { elapsedFrom } from "@/lib/scan/progress-ui";

export function ScanMonitorOverview({
  scan,
  currentStage,
  leavePageSupported,
}: {
  scan: ScanStatusResponse | null;
  currentStage: string;
  leavePageSupported: boolean;
}) {
  const running = scan?.status === "queued" || scan?.status === "running";
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    if (!scan?.created_at) {
      return;
    }
    const timeout = window.setTimeout(() => setNow(Date.now()), 0);
    const interval = running ? window.setInterval(() => setNow(Date.now()), 1000) : undefined;
    return () => {
      window.clearTimeout(timeout);
      if (interval !== undefined) {
        window.clearInterval(interval);
      }
    };
  }, [running, scan?.created_at]);

  const url = scan?.normalized_url || scan?.url;
  const pages = scan?.result?.pages?.summary;
  const elapsed = now != null ? elapsedFrom(scan?.created_at, now, running ? null : scan?.completed_at) : null;

  return (
    <section className="scan-monitor-card p-5 sm:p-6">
      <h2 className="text-lg font-semibold text-ink">Scan overview</h2>
      <dl className="mt-4 divide-y divide-border">
        <OverviewRow icon={<Globe className="size-4" aria-hidden />} label="Website">
          {url ? (
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="break-all text-brand underline-offset-4 hover:underline focus-visible:rounded-sm focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
            >
              {url}
            </a>
          ) : (
            "Unavailable"
          )}
        </OverviewRow>
        {typeof pages?.crawled === "number" ? (
          <OverviewRow icon={<Layers className="size-4" aria-hidden />} label="Pages scanned">
            {pages.crawled}
          </OverviewRow>
        ) : null}
        {typeof pages?.discovered === "number" ? (
          <OverviewRow icon={<Map className="size-4" aria-hidden />} label="Pages discovered">
            {pages.discovered}
          </OverviewRow>
        ) : null}
        <OverviewRow icon={<Timer className="size-4" aria-hidden />} label="Current stage">
          {currentStage || "Unavailable"}
        </OverviewRow>
        {elapsed ? (
          <OverviewRow icon={<Clock className="size-4" aria-hidden />} label="Elapsed time">
            {elapsed}
          </OverviewRow>
        ) : null}
      </dl>

      <div className="mt-5">
        {leavePageSupported ? (
          <ScanStatusMessage>
            SiteLens is analyzing your website. You can safely leave this page and return later.
          </ScanStatusMessage>
        ) : (
          <ScanStatusMessage>Keep this page open while the scan is running.</ScanStatusMessage>
        )}
      </div>
    </section>
  );
}

function OverviewRow({
  icon,
  label,
  children,
}: {
  icon: ReactNode;
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3 first:pt-0">
      <dt className="inline-flex items-center gap-2 text-sm text-muted-foreground">
        <span className="text-brand">{icon}</span>
        {label}
      </dt>
      <dd className="max-w-[60%] text-right text-sm font-medium text-ink">{children}</dd>
    </div>
  );
}
