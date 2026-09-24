import { BenchmarkForm } from "@/components/landing/benchmark-form";

const TRUST = [
  "No credit card required",
  "Comprehensive website analysis",
  "Actionable recommendations",
] as const;

export function FinalCta({
  initialUrl,
  initialError,
}: {
  initialUrl?: string;
  initialError?: string;
}) {
  return (
    <section className="landing-container pb-16 sm:pb-20 lg:pb-28">
      <div className="relative overflow-hidden rounded-[1.25rem] bg-[#0B1220] px-5 py-14 text-white sm:px-10 sm:py-16 lg:px-16 lg:py-20">
        <div className="pointer-events-none absolute inset-0 landing-grid-navy" aria-hidden="true" />
        <div className="pointer-events-none absolute inset-0 landing-glow-navy" aria-hidden="true" />
        <div className="relative max-w-2xl">
          <h2 className="text-[1.75rem] leading-[1.15] font-semibold tracking-tight sm:text-4xl lg:text-[2.75rem]">
            Get a complete website analysis in minutes.
          </h2>
          <p className="mt-4 max-w-md text-base leading-relaxed text-slate-300">
            See what&apos;s working, what needs attention, and what to do next.
          </p>
          <div className="mt-8">
            <BenchmarkForm
              initialUrl={initialUrl}
              initialError={initialError}
              tone="dark"
              formId="benchmark-cta"
              trustItems={TRUST}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
