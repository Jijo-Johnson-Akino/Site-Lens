import { BenchmarkForm } from "@/components/landing/benchmark-form";
import { ProductPreview } from "@/components/landing/product-preview";

export function Hero({
  initialUrl,
  initialError,
}: {
  initialUrl?: string;
  initialError?: string;
}) {
  return (
    <section className="relative overflow-x-clip py-10 sm:py-12 lg:flex lg:min-h-[calc(100svh-4.5rem)] lg:items-center lg:py-8">
      <div className="pointer-events-none absolute inset-0 landing-grid" aria-hidden="true" />
      <div className="pointer-events-none absolute inset-0 landing-glow" aria-hidden="true" />

      <div className="landing-container relative grid w-full items-center gap-8 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,0.85fr)] lg:gap-10 xl:gap-12">
        <div className="@container landing-fade-up min-w-0 text-left">
          <p className="text-xs font-semibold tracking-[0.18em] text-brand uppercase">
            Website intelligence platform
          </p>
          <h1 className="mt-3 text-[clamp(1.875rem,7.2cqi,3.5rem)] leading-[1.06] font-semibold tracking-tighter text-ink">
            <span className="block">Website intelligence,</span>
            <span className="block">
              <span className="text-brand">not another</span> SEO checker.
            </span>
          </h1>
          <div className="mt-4 max-w-[36rem] space-y-2 text-[15px] leading-relaxed text-muted-foreground sm:text-base">
            <p>
              Enter a URL. SiteLens crawls the site, analyzes available pages, and produces a Website
              Health Score, issues, recommendations, and an Action Plan.
            </p>
            <p>Built for SEO, AEO, performance, UX, accessibility, content, CRO, and trust analysis.</p>
          </div>
          <div className="mt-6">
            <BenchmarkForm initialUrl={initialUrl} initialError={initialError} />
          </div>
        </div>

        <div className="min-w-0">
          <ProductPreview />
        </div>
      </div>
    </section>
  );
}
