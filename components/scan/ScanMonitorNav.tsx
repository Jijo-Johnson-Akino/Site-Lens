import { ExternalLink } from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/landing/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { hostnameOf } from "@/lib/scan/display";

export function ScanMonitorNav({
  url,
  scanId,
  showDetails,
  onViewDetails,
}: {
  url?: string;
  scanId: string;
  showDetails?: boolean;
  onViewDetails?: () => void;
}) {
  const host = hostnameOf(url);
  const href = url || undefined;

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-card/95 backdrop-blur-md">
      <div className="scan-monitor-container flex h-16 items-center justify-between gap-4">
        <Logo href="/" />
        <div className="flex min-w-0 items-center gap-3 sm:gap-5">
          {href ? (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-w-0 max-w-[46vw] items-center gap-1.5 truncate text-sm font-medium text-ink underline-offset-4 hover:text-brand hover:underline focus-visible:rounded-md focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none sm:max-w-none"
              title={href}
            >
              <span className="truncate">{host || href}</span>
              <ExternalLink className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
              <span className="sr-only">(opens in a new tab)</span>
            </a>
          ) : null}
          {showDetails ? (
            onViewDetails ? (
              <button
                type="button"
                onClick={onViewDetails}
                className="hidden shrink-0 text-sm font-medium text-brand underline-offset-4 hover:underline focus-visible:rounded-md focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none sm:inline"
              >
                View scan details
              </button>
            ) : (
              <Link
                href={`/scan/${scanId}/score`}
                className="hidden shrink-0 text-sm font-medium text-brand underline-offset-4 hover:underline focus-visible:rounded-md focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none sm:inline"
              >
                View scan details
              </Link>
            )
          ) : null}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
