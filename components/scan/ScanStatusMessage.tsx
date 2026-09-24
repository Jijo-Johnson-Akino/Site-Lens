import { Info } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function ScanStatusMessage({
  title,
  children,
  className,
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex gap-3 rounded-xl border border-border bg-accent px-3.5 py-3 text-sm text-accent-foreground",
        className,
      )}
    >
      <Info className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden />
      <div className="min-w-0 leading-relaxed">
        {title ? <p className="font-medium text-ink">{title}</p> : null}
        <p className={title ? "mt-1 text-muted-foreground" : undefined}>{children}</p>
      </div>
    </div>
  );
}
