import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ScanStateCard({
  title,
  body,
  actionHref,
  actionLabel,
  onAction,
}: {
  title: string;
  body: string;
  actionHref?: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8" aria-live="polite">
      <h1 className="text-lg font-semibold text-foreground">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
      {onAction && actionLabel ? (
        <button type="button" onClick={onAction} className={cn(buttonVariants(), "mt-4 h-10 px-4")}>
          {actionLabel}
        </button>
      ) : actionHref && actionLabel ? (
        <Link href={actionHref} className={cn(buttonVariants(), "mt-4 h-10 px-4")}>
          {actionLabel}
        </Link>
      ) : null}
    </section>
  );
}

export function ScanSkeletonCards({ count = 3, label = "Loading" }: { count?: number; label?: string }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label={label}>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="h-40 animate-pulse rounded-2xl border border-border bg-muted/60" />
      ))}
    </div>
  );
}
