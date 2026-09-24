import { Check } from "lucide-react";

import { ScanStatusMessage } from "@/components/scan/ScanStatusMessage";
import type { LifecycleStageState } from "@/lib/scan/progress-ui";
import { cn } from "@/lib/utils";

export function ScanLifecycle({
  stages,
  leavePageSupported,
}: {
  stages: LifecycleStageState[];
  leavePageSupported: boolean;
}) {
  return (
    <section className="scan-monitor-card flex h-full flex-col p-5 sm:p-6">
      <h2 className="text-lg font-semibold text-ink">Scan process</h2>
      <ol className="mt-5 flex flex-col">
        {stages.map((stage, index) => {
          const isLast = index === stages.length - 1;
          return (
            <li key={stage.id} className="relative flex gap-3">
              <div className="flex w-9 shrink-0 flex-col items-center self-stretch">
                <StageMark status={stage.status} />
                {isLast ? null : (
                  <span
                    className={cn(
                      "mt-1 mb-1 w-px flex-1 min-h-6",
                      stage.status === "completed" ? "bg-pass" : stage.status === "current" ? "bg-brand" : "bg-border",
                    )}
                    aria-hidden
                  />
                )}
              </div>
              <div className={cn("min-w-0 pb-6", isLast && "pb-1", stage.status === "current" && "-mt-1 rounded-xl bg-accent px-3 py-2")}>
                <p className="text-[11px] font-semibold tracking-[0.16em] text-muted-foreground uppercase">{stage.index}</p>
                <p
                  className={cn(
                    "mt-0.5 text-sm font-semibold",
                    stage.status === "current" ? "text-brand" : stage.status === "completed" ? "text-ink" : "text-muted-foreground",
                  )}
                >
                  {stage.title}
                </p>
                <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{stage.description}</p>
              </div>
            </li>
          );
        })}
      </ol>
      {leavePageSupported ? (
        <ScanStatusMessage className="mt-auto pt-2" title="You can safely leave this page.">
          We’ll keep your scan running.
        </ScanStatusMessage>
      ) : (
        <ScanStatusMessage className="mt-auto pt-2">Keep this page open while the scan is running.</ScanStatusMessage>
      )}
    </section>
  );
}

function StageMark({ status }: { status: LifecycleStageState["status"] }) {
  if (status === "completed") {
    return (
      <span className="flex size-7 items-center justify-center rounded-full bg-pass text-white" aria-hidden>
        <Check className="size-3.5" strokeWidth={2.5} />
      </span>
    );
  }
  if (status === "current") {
    return (
      <span className="flex size-7 items-center justify-center rounded-full bg-brand text-white" aria-hidden>
        <span className="size-2 rounded-full bg-white" />
      </span>
    );
  }
  return (
    <span className="flex size-7 items-center justify-center rounded-full border border-border bg-card" aria-hidden>
      <span className="size-2 rounded-full bg-muted-foreground/40" />
    </span>
  );
}
