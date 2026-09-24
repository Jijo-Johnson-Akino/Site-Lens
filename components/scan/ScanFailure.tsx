import { Ban, CircleAlert } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ScanFailure({
  message,
  cancelled,
  canRetry,
  retrying,
  onRetry,
}: {
  message: string;
  cancelled?: boolean;
  canRetry: boolean;
  retrying: boolean;
  onRetry: () => void;
}) {
  return (
    <section className="scan-monitor-card mx-auto max-w-xl px-6 py-10 text-center sm:px-10">
      {cancelled ? (
        <Ban className="mx-auto size-12 text-muted-foreground" aria-hidden />
      ) : (
        <CircleAlert className="mx-auto size-12 text-critical" aria-hidden />
      )}
      <h2 className="mt-4 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        {cancelled ? "Scan cancelled" : "Analysis couldn't be completed"}
      </h2>
      <p className="mt-2 text-base text-muted-foreground">
        {cancelled
          ? "The website analysis was stopped before completion."
          : message || "Unable to analyze this website."}
      </p>
      <div className="mt-8 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
        {canRetry ? (
          <button
            type="button"
            onClick={onRetry}
            disabled={retrying}
            className={cn(buttonVariants(), "h-10 px-4")}
          >
            {retrying ? "Starting..." : cancelled ? "Start New Scan" : "Retry Scan"}
          </button>
        ) : null}
        <Link
          href="/"
          className={cn(buttonVariants({ variant: canRetry ? "outline" : "default" }), "h-10 px-4")}
        >
          Back to SiteLens
        </Link>
      </div>
    </section>
  );
}
