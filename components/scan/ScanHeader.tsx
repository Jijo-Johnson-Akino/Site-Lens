import { ChartLine, Layers, ShieldCheck } from "lucide-react";

export function ScanHeader({
  failed,
  cancelled,
  leavePageSupported,
}: {
  failed?: boolean;
  cancelled?: boolean;
  leavePageSupported: boolean;
}) {
  const eyebrow = failed ? "Scan unsuccessful" : cancelled ? "Scan stopped" : "Website intelligence platform";
  const title = failed
    ? "Analysis couldn't be completed"
    : cancelled
      ? "Scan cancelled"
      : "Scanning, analyzing, and finding what matters";
  const description = failed
    ? "SiteLens stopped before a complete analysis was ready."
    : cancelled
      ? "The website analysis was stopped before completion."
      : "This may take a few minutes. We'll let you know when it's complete.";

  return (
    <section className="mx-auto max-w-4xl px-1 text-center">
      <p className="text-[11px] font-semibold tracking-[0.22em] text-brand uppercase sm:text-xs">{eyebrow}</p>
      <h1 className="mt-3 text-balance text-[1.85rem] leading-[1.15] font-semibold tracking-tight text-ink sm:text-4xl lg:text-[2.75rem]">
        {title}
      </h1>
      <p className="mx-auto mt-3 max-w-2xl text-base text-muted-foreground sm:text-lg">{description}</p>

      {!failed && !cancelled ? (
        <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-muted-foreground">
          <li className="inline-flex items-center gap-2">
            <Layers className="size-4 text-brand" aria-hidden />
            Comprehensive analysis
          </li>
          <li className="inline-flex items-center gap-2">
            <ShieldCheck className="size-4 text-brand" aria-hidden />
            {leavePageSupported ? "No need to stay on this page" : "Keep this page open"}
          </li>
          <li className="inline-flex items-center gap-2">
            <ChartLine className="size-4 text-brand" aria-hidden />
            Real insights, not just scores
          </li>
        </ul>
      ) : null}
    </section>
  );
}
