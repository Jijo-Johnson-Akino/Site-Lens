const NAV = ["Overview", "SEO", "AEO", "Issues", "Report"] as const;

const CATEGORIES = [
  { name: "SEO", score: 86 },
  { name: "AEO", score: 74 },
  { name: "UI/UX", score: 81 },
  { name: "Accessibility", score: 69 },
  { name: "Performance", score: 78 },
  { name: "Content", score: 84 },
  { name: "Structured Data", score: 71 },
  { name: "Mobile", score: 88 },
  { name: "CRO", score: 72 },
  { name: "Trust", score: 80 },
] as const;

const ISSUES = [
  { label: "Missing meta descriptions", severity: "High" },
  { label: "Image elements missing alt text", severity: "Medium" },
  { label: "Organization schema incomplete", severity: "High" },
] as const;

function ScoreRing({ score, size = 72 }: { score: number; size?: number }) {
  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  return (
    <svg width={size} height={size} viewBox="0 0 88 88" aria-hidden="true">
      <circle cx="44" cy="44" r={radius} fill="none" stroke="var(--border)" strokeWidth="8" />
      <circle
        cx="44"
        cy="44"
        r={radius}
        fill="none"
        stroke="var(--primary)"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform="rotate(-90 44 44)"
      />
      <text x="44" y="42" textAnchor="middle" className="fill-ink text-[1.35rem] font-semibold">
        {score}
      </text>
      <text x="44" y="58" textAnchor="middle" className="fill-muted-foreground text-[9px]">
        / 100
      </text>
    </svg>
  );
}

export function ProductPreview() {
  return (
    <figure id="product" className="relative mx-auto w-full max-w-[34rem] scroll-mt-24 pb-5 lg:max-w-none">
      <figcaption className="sr-only">
        Product preview. Illustrative SiteLens dashboard layout, not a live scan.
      </figcaption>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -inset-4 rounded-[2rem] bg-brand/10 blur-2xl"
      />
      <div className="landing-float relative" aria-hidden="true">
        <div className="shadow-landing-lg relative overflow-hidden rounded-[1.15rem] border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border bg-muted px-3 py-1.5 sm:px-4">
            <div className="flex items-center gap-1.5" aria-hidden="true">
              <span className="size-2 rounded-full bg-critical/80" />
              <span className="size-2 rounded-full bg-warn/80" />
              <span className="size-2 rounded-full bg-pass/80" />
            </div>
            <p className="font-mono text-[10px] tracking-wide text-muted-foreground uppercase">
              Product preview · Illustrative layout
            </p>
          </div>

          <div className="grid min-w-0 md:grid-cols-[8.25rem_minmax(0,1fr)]">
            <aside className="hidden bg-[#0B1220] p-3 text-white md:block" aria-hidden="true">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/brand/sitelens-logo-on-dark.png"
                alt=""
                width={699}
                height={189}
                className="mb-3 h-5 w-auto max-w-full object-contain object-left"
              />
              <ul className="space-y-0.5">
                {NAV.map((item, index) => (
                  <li
                    key={item}
                    className={
                      index === 0
                        ? "rounded-lg bg-brand px-2.5 py-1.5 text-[13px] font-medium"
                        : "rounded-lg px-2.5 py-1.5 text-[13px] text-white/60"
                    }
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </aside>

            <div className="min-w-0 space-y-2.5 bg-background p-2.5 sm:p-3">
              <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-card p-2.5 sm:p-3">
                <div className="flex items-center gap-3">
                  <ScoreRing score={82} />
                  <div>
                    <p className="text-[10px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">
                      Website Health
                    </p>
                    <p className="text-base font-semibold tracking-tight text-ink">82 / 100</p>
                  </div>
                </div>
                <div className="min-w-[8rem] flex-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-medium text-muted-foreground">Score Coverage</span>
                    <span className="font-semibold text-ink">92%</span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                    <div className="h-full w-[92%] rounded-full bg-brand" />
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-border bg-card p-2.5 sm:p-3">
                <p className="mb-2 text-[10px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">
                  Category scores
                </p>
                <ul className="grid grid-cols-2 gap-x-3 gap-y-1">
                  {CATEGORIES.map((category) => (
                    <li key={category.name} className="flex items-center justify-between gap-2 text-[12px]">
                      <span className="truncate text-muted-foreground">{category.name}</span>
                      <span className="font-mono text-[12px] font-semibold text-ink">{category.score}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-2xl border border-border bg-card p-2.5 sm:p-3">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-[10px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">Issues</p>
                  <p className="text-[11px] text-muted-foreground">2 High · 1 Medium</p>
                </div>
                <ul className="space-y-1.5">
                  {ISSUES.map((issue) => (
                    <li key={issue.label} className="flex items-center justify-between gap-2 text-[12px] text-ink">
                      <span className="truncate">{issue.label}</span>
                      <span
                        className={
                          issue.severity === "High"
                            ? "rounded-full bg-critical/10 px-1.5 py-0.5 text-[10px] font-medium text-critical"
                            : "rounded-full bg-warn/10 px-1.5 py-0.5 text-[10px] font-medium text-warn"
                        }
                      >
                        {issue.severity}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div
          aria-hidden="true"
          className="landing-float-delay absolute right-3 -bottom-4 hidden w-40 rounded-2xl border border-border bg-card p-2.5 shadow-landing sm:block"
        >
          <p className="text-[10px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">Action Plan</p>
          <p className="mt-1 text-sm font-semibold text-ink">3 next steps</p>
          <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">Illustrative preview — not a live scan.</p>
        </div>
      </div>
    </figure>
  );
}
