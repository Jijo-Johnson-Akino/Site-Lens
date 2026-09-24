import Link from "next/link";

import { IssueEvidence, type IssueEvidenceData } from "@/components/scan/IssueEvidence";
import { CompactSeverityBadge } from "@/components/scan/report/SeverityBadge";
import { cn } from "@/lib/utils";

export type IssueCardData = IssueEvidenceData & {
  issue_id: string;
  title: string;
  category: string;
  severity: string;
  page_url?: string | null;
  pages?: string[];
  description?: string | null;
  recommendation?: string | null;
  whats_wrong?: string | null;
  why_it_matters?: string | null;
  how_to_fix?: string | null;
  href?: string;
  visual_kind?: "screenshot" | "snippet" | "none" | null;
};

export function IssueCard({
  issue,
  capturing = false,
  compact = false,
  className,
  heading: Heading = "h3",
}: {
  issue: IssueCardData;
  capturing?: boolean;
  compact?: boolean;
  className?: string;
  heading?: "h1" | "h2" | "h3";
}) {
  const wrong = issue.whats_wrong || issue.description;
  const why = issue.why_it_matters;
  const fix = issue.how_to_fix || issue.recommendation;
  const page = issue.page_url || issue.pages?.[0];
  const title = issue.href ? (
    <Link href={issue.href} className="text-foreground hover:underline">
      {issue.title}
    </Link>
  ) : (
    issue.title
  );

  return (
    <article className={cn("issue-card rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6", className)}>
      <div className="flex flex-wrap items-center gap-2">
        <CompactSeverityBadge value={issue.severity} />
        <span className="inline-flex rounded-full border border-border bg-muted/60 px-2 py-0.5 text-[11px] font-medium text-foreground">
          {issue.category}
        </span>
        <Heading className={cn("min-w-0 flex-1 text-[15px] font-semibold tracking-tight", compact ? "" : "text-lg")}>{title}</Heading>
      </div>

      <div className="mt-4">
        <IssueEvidence issue={issue} capturing={capturing && issue.visual_kind === "screenshot"} compact={compact} />
      </div>

      {wrong ? (
        <section className="mt-4">
          <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">What&apos;s wrong</h4>
          <p className="mt-1 text-sm leading-6 text-foreground">{wrong}</p>
        </section>
      ) : null}

      {why ? (
        <section className="mt-3">
          <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Why it matters</h4>
          <p className="mt-1 text-sm leading-6 text-foreground">{why}</p>
        </section>
      ) : null}

      {fix ? (
        <section className="mt-3">
          <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">How to fix</h4>
          <HowToFix text={fix} />
        </section>
      ) : null}

      {page ? (
        <p className="mt-4 font-mono text-[11px] break-all text-muted-foreground">{page}</p>
      ) : null}
    </article>
  );
}

function HowToFix({ text }: { text: string }) {
  const steps = text
    .split(/(?<=\.)\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (steps.length <= 1) {
    return <p className="mt-1 text-sm leading-6 text-foreground">{text}</p>;
  }
  return (
    <ol className="mt-1 list-decimal space-y-1 pl-5 text-sm leading-6 text-foreground">
      {steps.map((step) => (
        <li key={step}>{step}</li>
      ))}
    </ol>
  );
}
