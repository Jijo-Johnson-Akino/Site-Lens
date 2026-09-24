import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

export function CheckItems({
  items,
  tone = "light",
  layout = "row",
}: {
  items: readonly string[];
  tone?: "light" | "dark";
  layout?: "row" | "stack";
}) {
  return (
    <ul
      className={cn(
        "flex gap-2",
        layout === "stack" ? "flex-col" : "flex-col sm:flex-row sm:flex-wrap sm:gap-x-5",
      )}
    >
      {items.map((item) => (
        <li
          key={item}
          className={cn(
            "flex items-center gap-2 text-[13px] leading-snug",
            tone === "dark" ? "text-slate-300" : "text-muted-foreground",
          )}
        >
          <Check
            className={cn("size-3.5 shrink-0", tone === "dark" ? "text-emerald-400" : "text-pass")}
            strokeWidth={2.5}
            aria-hidden="true"
          />
          {item}
        </li>
      ))}
    </ul>
  );
}
