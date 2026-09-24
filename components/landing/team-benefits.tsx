import { ArrowRight, Layers3, ListTodo, ScanSearch, Users } from "lucide-react";

import { LandingSection, SectionEyebrow, SectionHeading } from "@/components/landing/section";

const FEATURES = [
  {
    title: "Actionable insights",
    body: "Findings are grouped by severity and tied to the check that failed, so the next step is never generic advice.",
    icon: ListTodo,
  },
  {
    title: "Comprehensive coverage",
    body: "SEO, AEO, UX, accessibility, performance, content, structured data, mobile, CRO, trust, architecture, and competitors.",
    icon: Layers3,
  },
  {
    title: "Built for AI search",
    body: "AEO is a first-class score. SiteLens reports observable answer-engine signals — extractable content, entities, and schema — not predicted citations.",
    icon: ScanSearch,
  },
  {
    title: "Designed for teams",
    body: "One shared report for marketing, product, and engineering: scores, issues, recommendations, and an Action Plan.",
    icon: Users,
  },
] as const;

export function TeamBenefits() {
  return (
    <LandingSection id="aeo">
      <div className="grid items-start gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-16">
        <div>
          <SectionEyebrow>Built for modern website teams</SectionEyebrow>
          <SectionHeading>
            More than metrics.
            <br />
            Real progress.
          </SectionHeading>
          <p className="mt-4 max-w-md text-base leading-relaxed text-muted-foreground">
            SiteLens helps marketing, product, and technical teams understand their website, find what to
            fix, and turn insight into action — all in one place.
          </p>
          <a
            href="#benchmark"
            className="mt-7 inline-flex h-11 items-center gap-2 rounded-[10px] bg-brand px-4 text-sm font-medium text-white transition-colors hover:bg-[#1d4ed8] focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:outline-none"
          >
            Start Your Analysis
            <ArrowRight className="size-4" aria-hidden="true" />
          </a>
          <p className="mt-8 text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase">Built for</p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {["SEO teams", "Product & UX", "Engineering", "Agencies"].map((label) => (
              <li
                key={label}
                className="rounded-full border border-border bg-card px-3 py-1 text-[13px] text-muted-foreground"
              >
                {label}
              </li>
            ))}
          </ul>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {FEATURES.map((feature) => (
            <article
              key={feature.title}
              className="scroll-mt-24 rounded-2xl border border-border bg-card p-5 shadow-landing"
            >
              <span className="inline-flex size-9 items-center justify-center rounded-xl border border-border bg-muted text-brand">
                <feature.icon className="size-4" strokeWidth={1.75} aria-hidden="true" />
              </span>
              <h3 className="mt-4 text-lg font-semibold text-ink">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{feature.body}</p>
            </article>
          ))}
        </div>
      </div>
    </LandingSection>
  );
}
