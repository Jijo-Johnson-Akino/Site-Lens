"use client";

import { Check, ChevronDown, Circle, LoaderCircle, X } from "lucide-react";
import { useState } from "react";

import type { ScanStepStatus } from "@/lib/scan/api";
import { COLLAPSED_STEP_COUNT, stepStatusLabel } from "@/lib/scan/progress-ui";
import type { ScanStepDefinition } from "@/lib/scan/steps";
import { cn } from "@/lib/utils";

type Step = ScanStepDefinition & { status: ScanStepStatus };

export function ScanStepList({ steps }: { steps: Step[] }) {
  const [expanded, setExpanded] = useState(false);
  const remaining = Math.max(0, steps.length - COLLAPSED_STEP_COUNT);
  const visible = expanded || remaining === 0 ? steps : steps.slice(0, COLLAPSED_STEP_COUNT);

  return (
    <section className="scan-monitor-card p-5 sm:p-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">Scan progress</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">{steps.length} steps</p>
        </div>
      </div>

      <ol className="mt-4 divide-y divide-border">
        {visible.map((step) => {
          const number = steps.findIndex((item) => item.id === step.id) + 1;
          return (
            <li key={step.id} className={cn("flex items-start gap-3 py-3 sm:items-center", step.status === "active" && "rounded-lg bg-accent px-2 sm:px-3")}>
              <StepIcon status={step.status} />
              <span className="hidden w-6 shrink-0 text-xs font-medium text-muted-foreground tabular-nums sm:inline">{number}</span>
              <div className="min-w-0 flex-1">
                <p
                  className={cn(
                    "text-sm font-medium",
                    step.status === "pending" ? "text-muted-foreground" : "text-ink",
                    step.status === "failed" && "text-critical",
                  )}
                >
                  {step.label}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground sm:hidden">{stepStatusLabel(step.status)}</p>
              </div>
              <span
                className={cn(
                  "hidden shrink-0 text-xs font-medium sm:inline",
                  step.status === "completed" && "text-pass",
                  step.status === "active" && "text-brand",
                  step.status === "pending" && "text-muted-foreground",
                  step.status === "failed" && "text-critical",
                )}
              >
                {stepStatusLabel(step.status)}
              </span>
              <span className="sr-only">
                Step {number}: {step.label}, {stepStatusLabel(step.status)}
              </span>
            </li>
          );
        })}
      </ol>

      {remaining > 0 ? (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-brand underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
        >
          <ChevronDown className={cn("size-4 transition-transform", expanded && "rotate-180")} aria-hidden />
          {expanded ? "Show fewer steps" : `Show remaining steps (${remaining})`}
        </button>
      ) : null}
    </section>
  );
}

function StepIcon({ status }: { status: ScanStepStatus }) {
  if (status === "completed") {
    return (
      <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-pass text-white sm:mt-0">
        <Check className="size-3" strokeWidth={2.75} aria-hidden />
      </span>
    );
  }
  if (status === "active") {
    return (
      <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center text-brand sm:mt-0">
        <LoaderCircle className="size-5 motion-safe:animate-spin" aria-hidden />
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-critical text-white sm:mt-0">
        <X className="size-3" strokeWidth={2.75} aria-hidden />
      </span>
    );
  }
  return (
    <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center text-muted-foreground/50 sm:mt-0">
      <Circle className="size-4" aria-hidden />
    </span>
  );
}
