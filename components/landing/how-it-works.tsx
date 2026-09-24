import { Fragment } from "react";
import { ArrowUpRight } from "lucide-react";

import styles from "@/components/landing/how-it-works.module.css";

const BULLETS = [
  "Scores based only on observable checks",
  "SEO, AEO, UI/UX, accessibility, performance, and content in one scan",
  "Missing data is skipped, never scored as zero",
  "Issues, recommendations, and an Action Plan",
] as const;

const STEPS = [
  {
    n: "01",
    title: "Enter a URL",
    tagline: "Start with a public website.",
    description: "Paste a URL. SiteLens validates it and benchmarks that property — one site per scan, no account required.",
    chips: ["One site per scan", "Public URLs only", "URL validation", "No account needed"],
    icon: LinkIcon,
  },
  {
    n: "02",
    title: "Crawl & analyze",
    tagline: "Analyze the pages we can reach.",
    description:
      "SiteLens crawls reachable internal pages within scan limits, then runs SEO, AEO, UI/UX, accessibility, performance, content, and more.",
    chips: ["SEO & AEO", "UI/UX & accessibility", "Performance & mobile", "Content & structured data", "CRO & trust", "Architecture & competitors"],
    icon: RadarIcon,
  },
  {
    n: "03",
    title: "Score what's real",
    tagline: "Every score has evidence.",
    description: "The Website Health Score uses completed categories. Unavailable analyzers are skipped, not scored as zero.",
    chips: ["Website Health Score", "Per-category scores", "Unavailable ≠ 0", "Observable checks"],
    icon: ChartIcon,
  },
  {
    n: "04",
    title: "Fix what matters",
    tagline: "Know what to investigate next.",
    description: "Unified issues and recommendations feed an Action Plan, plus a compact Website Analysis Report.",
    chips: ["Unified issues", "Recommendations", "Action Plan", "Analysis report"],
    icon: ChecklistIcon,
  },
] as const;

export function HowItWorks() {
  return (
    <section id="how" className={styles.section}>
      <div className={styles.inner}>
        <div className={styles.grid}>
          <div className={styles.intro}>
            <p className={styles.eyebrow}>
              <span className={styles.dash} aria-hidden="true" />
              How it works
            </p>
            <h2 className={styles.title}>From one URL to an Action Plan.</h2>
            <p className={styles.lead}>
              Paste a public URL. SiteLens crawls reachable pages, scores completed categories, and returns issues, recommendations, and an Action Plan.
            </p>
            <ul className={styles.bullets}>
              {BULLETS.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <a className={styles.cta} href="#benchmark">
              Start Free Analysis
              <ArrowUpRight size={14} strokeWidth={2.25} aria-hidden="true" />
            </a>
          </div>

          <div className={styles.stack}>
            {STEPS.map((step) => (
              <Fragment key={step.n}>
                <div className={styles.cardWrap}>
                  <div className={styles.tab} aria-hidden="true">
                    {step.n}
                  </div>
                  <article className={styles.card} aria-labelledby={`how-step-${step.n}`}>
                    <div className={styles.cardHead}>
                      <step.icon />
                      <h3 id={`how-step-${step.n}`} className={styles.cardTitle}>
                        {step.title}
                      </h3>
                    </div>
                    <p className={styles.tagline}>{step.tagline}</p>
                    <p className={styles.description}>{step.description}</p>
                    <hr className={styles.rule} />
                    <div className={styles.chips}>
                      {step.chips.map((chip) => (
                        <span key={chip}>{chip}</span>
                      ))}
                    </div>
                  </article>
                </div>
                <span className={styles.gap} aria-hidden="true" />
              </Fragment>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function LinkIcon() {
  return (
    <svg className={styles.icon} viewBox="0 0 36 36" fill="none" aria-hidden="true">
      <path d="M14.2 16.2a5 5 0 0 1 0-7.1l2.5-2.5a5 5 0 0 1 7.1 7.1l-1.6 1.6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M21.8 19.8a5 5 0 0 1 0 7.1l-2.5 2.5a5 5 0 0 1-7.1-7.1l1.6-1.6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path className={styles.iconAccent} d="M15.5 20.5 20.5 15.5" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    </svg>
  );
}

function RadarIcon() {
  return (
    <svg className={styles.icon} viewBox="0 0 36 36" fill="none" aria-hidden="true">
      <circle cx="18" cy="18" r="12" stroke="currentColor" strokeWidth="1.7" />
      <circle cx="18" cy="18" r="7" stroke="currentColor" strokeWidth="1.7" />
      <path className={styles.iconAccent} d="M18 18 27.5 11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle className={styles.iconAccent} cx="18" cy="18" r="2.2" fill="currentColor" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg className={styles.icon} viewBox="0 0 36 36" fill="none" aria-hidden="true">
      <path d="M7 28h22" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <rect x="9" y="18" width="5" height="10" rx="1" stroke="currentColor" strokeWidth="1.7" />
      <rect className={styles.iconAccent} x="15.5" y="9" width="5" height="19" rx="1" fill="currentColor" />
      <rect x="22" y="14" width="5" height="14" rx="1" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  );
}

function ChecklistIcon() {
  return (
    <svg className={styles.icon} viewBox="0 0 36 36" fill="none" aria-hidden="true">
      <path d="M14 12h14M14 18h14M14 24h9" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path className={styles.iconAccent} d="M7.5 12.2 9.3 14l3.4-3.6" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M7.5 18.2 9.3 20l3.4-3.6M7.5 24.2 9.3 26l3.4-3.6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
