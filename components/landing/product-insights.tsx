import { AlertTriangle, Check } from "lucide-react";

import { CheckItems } from "@/components/landing/check-items";
import { LandingSection, SectionEyebrow, SectionHeading } from "@/components/landing/section";

const INCLUDED = [
  "Website Health Score",
  "Detailed issue analysis",
  "Page-level insights",
  "Prioritized recommendations",
  "Professional reports and action plans",
] as const;

export function ProductInsights() {
  return (
    <LandingSection id="insights" className="bg-card/60">
      <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
        <div className="relative">
          <p className="mb-3 font-mono text-[10px] tracking-[0.16em] text-muted-foreground uppercase">
            Illustrative metrics · not a live scan
          </p>
          <div className="grid gap-3 sm:grid-cols-2" aria-hidden="true">
            <article className="rounded-2xl border border-border bg-card p-4 shadow-landing sm:translate-y-2">
              <p className="text-[11px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">Performance</p>
              <dl className="mt-3 space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">LCP</dt>
                  <dd className="font-mono font-semibold text-ink">2.1s</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">CLS</dt>
                  <dd className="font-mono font-semibold text-ink">0.08</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">INP</dt>
                  <dd className="font-mono font-semibold text-ink">178ms</dd>
                </div>
              </dl>
            </article>

            <article className="rounded-2xl border border-border bg-card p-4 shadow-landing">
              <p className="text-[11px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">SEO</p>
              <ul className="mt-3 space-y-2 text-sm">
                <SeoRow ok label="Title tags" />
                <SeoRow ok={false} label="Meta descriptions" />
                <SeoRow ok label="Canonicals" />
                <SeoRow ok label="Sitemap" />
              </ul>
            </article>

            <article className="rounded-2xl border border-border bg-card p-4 shadow-landing">
              <p className="text-[11px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">Accessibility</p>
              <p className="mt-2 text-2xl font-semibold tracking-tight text-ink">28 Issues</p>
              <ul className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-[13px] text-muted-foreground">
                <li>
                  <span className="font-medium text-critical">1</span> Critical
                </li>
                <li>
                  <span className="font-medium text-warn">7</span> High
                </li>
                <li>
                  <span className="font-medium text-foreground">12</span> Medium
                </li>
                <li>
                  <span className="font-medium text-muted-foreground">8</span> Low
                </li>
              </ul>
            </article>

            <article className="rounded-2xl border border-border bg-card p-4 shadow-landing sm:translate-y-2">
              <p className="text-[11px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">CRO</p>
              <p className="mt-2 text-3xl font-semibold tracking-tight text-ink">
                72 <span className="text-lg text-muted-foreground">/ 100</span>
              </p>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
                <div className="h-full w-[72%] rounded-full bg-brand" />
              </div>
            </article>
          </div>
        </div>

        <div>
          <SectionEyebrow>See the big picture</SectionEyebrow>
          <SectionHeading>
            Everything you need
            <br />
            to improve your website.
          </SectionHeading>
          <p className="mt-4 max-w-md text-base leading-relaxed text-muted-foreground">
            From technical SEO to content, performance, accessibility, CRO and trust signals — SiteLens
            gives you a complete view of what&apos;s working and what to improve.
          </p>
          <div className="mt-6">
            <CheckItems items={INCLUDED} layout="stack" />
          </div>
        </div>
      </div>
    </LandingSection>
  );
}

function SeoRow({ ok, label }: { ok: boolean; label: string }) {
  return (
    <li className="flex items-center gap-2 text-ink">
      {ok ? (
        <Check className="size-3.5 text-pass" strokeWidth={2.5} />
      ) : (
        <AlertTriangle className="size-3.5 text-warn" strokeWidth={2} />
      )}
      {label}
    </li>
  );
}
