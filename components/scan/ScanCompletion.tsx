import { CheckCircle2 } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { hostnameOf } from "@/lib/scan/display";
import { cn } from "@/lib/utils";

export function ScanCompletion({
  scanId,
  url,
  onViewOverview,
}: {
  scanId: string;
  url?: string;
  onViewOverview: () => void;
}) {
  const host = hostnameOf(url);

  return (
    <section className="scan-monitor-card mx-auto max-w-xl px-6 py-10 text-center sm:px-10">
      <CheckCircle2 className="mx-auto size-12 text-pass" aria-hidden />
      <h2 className="mt-4 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Analysis complete</h2>
      <p className="mt-2 text-base text-muted-foreground">
        Your website analysis{host ? ` for ${host}` : ""} is ready.
      </p>
      <div className="mt-8 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
        <Link href={`/scan/${scanId}/score`} className={cn(buttonVariants(), "h-10 px-4")}>
          View Website Health
        </Link>
        <Link href={`/scan/${scanId}/report`} className={cn(buttonVariants({ variant: "outline" }), "h-10 px-4")}>
          View Report
        </Link>
      </div>
      <button
        type="button"
        onClick={onViewOverview}
        className="mt-5 text-sm font-medium text-brand underline-offset-4 hover:underline focus-visible:rounded-md focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
      >
        View scan overview
      </button>
    </section>
  );
}
