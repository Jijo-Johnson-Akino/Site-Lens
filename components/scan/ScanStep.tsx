import { Check, Loader2, X } from "lucide-react";

import type { ScanStepStatus } from "@/lib/scan/api";

export function ScanStep({
  label,
  status,
}: {
  label: string;
  status: ScanStepStatus;
}) {
  return (
    <li className="flex items-center gap-3 text-sm sm:text-[15px]">
      <span
        className={`flex size-6 shrink-0 items-center justify-center rounded-full ${
          status === "completed"
            ? "bg-pass text-white"
            : status === "failed"
              ? "bg-critical text-white"
              : status === "active"
                ? "border border-primary/30 bg-primary/10 text-primary"
                : "border border-border bg-muted text-muted-foreground"
        }`}
        aria-hidden="true"
      >
        {status === "completed" ? (
          <Check className="size-3.5" strokeWidth={2.5} />
        ) : status === "failed" ? (
          <X className="size-3.5" strokeWidth={2.5} />
        ) : status === "active" ? (
          <Loader2 className="size-3.5 animate-spin" />
        ) : (
          <span className="size-1.5 rounded-full bg-current opacity-40" />
        )}
      </span>
      <span
        className={
          status === "pending"
            ? "text-muted-foreground"
            : status === "failed"
              ? "font-medium text-critical"
              : status === "active"
                ? "font-medium text-foreground"
                : "text-foreground"
        }
      >
        {label}
      </span>
      <span className="sr-only">{status}</span>
    </li>
  );
}
