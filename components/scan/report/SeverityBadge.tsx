import { AlertTriangle, Info, OctagonAlert } from "lucide-react";

import { titleCase } from "@/lib/scan/report-ui";
import { cn } from "@/lib/utils";

const STYLES: Record<string, { className: string; Icon: typeof AlertTriangle }> = {
  critical: {
    className: "bg-red-50 text-red-700 dark:bg-red-500/15 dark:text-red-300",
    Icon: OctagonAlert,
  },
  high: {
    className: "bg-orange-50 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300",
    Icon: AlertTriangle,
  },
  medium: {
    className: "bg-amber-50 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200",
    Icon: AlertTriangle,
  },
  low: {
    className: "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
    Icon: Info,
  },
  info: {
    className: "bg-slate-100 text-slate-600 dark:bg-slate-500/15 dark:text-slate-300",
    Icon: Info,
  },
};

export function CompactSeverityBadge({ value }: { value: string }) {
  const style = STYLES[value] ?? STYLES.info;
  const Icon = style.Icon;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium", style.className)}>
      <Icon className="size-3" aria-hidden="true" />
      {titleCase(value)}
    </span>
  );
}
