import { Clock } from "lucide-react";

import { activityDetail, activityHeadline, percentFromStep } from "@/lib/scan/progress-ui";
import { cn } from "@/lib/utils";

export function ScanProgressHero({
  url,
  currentStep,
  stepNumber,
  stepTotal,
}: {
  url?: string;
  currentStep: string;
  stepNumber: number;
  stepTotal: number;
}) {
  const pct = percentFromStep(stepNumber, stepTotal);
  const headline = activityHeadline(currentStep);
  const detail = activityDetail(currentStep);

  return (
    <section className="scan-monitor-card p-5 sm:p-7">
      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:gap-8">
        <ProgressRing value={pct} />
        <div className="min-w-0 w-full overflow-hidden text-center sm:text-left">
          <h2 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">Analyzing your website</h2>
          {url ? (
            <p className="mt-1 truncate text-sm text-brand" title={url}>
              {url}
            </p>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">Preparing scan</p>
          )}
          <p className="mt-3 text-sm text-muted-foreground">
            Step {stepNumber} of {stepTotal}
          </p>
        </div>
      </div>

      <div className="mt-6">
        <div
          className="h-2.5 overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
          aria-label="Scan progress"
        >
          <div
            className={cn("h-full rounded-full transition-[width] duration-500", pct >= 100 ? "bg-pass" : "bg-brand")}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-2 text-sm font-medium text-ink">{pct}%</p>
      </div>

      <div className="mt-6 flex flex-col gap-4 border-t border-border pt-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">Current activity</p>
          <p className="mt-1 text-base font-semibold text-ink" aria-live="polite">
            {headline}
          </p>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{detail}</p>
        </div>
        <div className="flex shrink-0 items-start gap-2 rounded-xl border border-border bg-muted px-3 py-2.5 text-left">
          <Clock className="mt-0.5 size-4 text-brand" aria-hidden />
          <div>
            <p className="text-xs font-medium text-muted-foreground">Estimated time remaining</p>
            <p className="text-sm font-semibold text-ink">Analysis in progress</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function ProgressRing({ value }: { value: number }) {
  const size = 148;
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = Number((2 * Math.PI * radius).toFixed(3));
  const offset = Number((circumference - (value / 100) * circumference).toFixed(3));
  const complete = value >= 100;

  return (
    <div className="relative size-[148px] shrink-0">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={complete ? "var(--pass)" : "var(--primary)"}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="motion-safe:transition-[stroke-dashoffset] motion-safe:duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <p className="text-4xl font-semibold tracking-tight text-ink tabular-nums sm:text-5xl">{value}%</p>
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Complete</p>
      </div>
      <span className="sr-only">{value} percent complete</span>
    </div>
  );
}
