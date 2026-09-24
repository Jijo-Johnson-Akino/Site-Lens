"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ScanShell } from "@/components/scan/ScanShell";
import { ScoreRing } from "@/components/scan/ScoreRing";
import { buttonVariants } from "@/components/ui/button";
import { getHealthScore, ScanApiError, type HealthCategoryScore, type HealthScoreResponse } from "@/lib/scan/api";
import {
  categoryStatusLabel,
  coverageLabel,
  emptyHealthCopy,
  HEALTH_COVERAGE_NOTE,
  HEALTH_SCORE_NOTE,
  scoreOutOf100,
  weightPercent,
} from "@/lib/scan/score-ui";
import { useScanStatus } from "@/lib/scan/use-scan-status";
import { cn } from "@/lib/utils";

export function ScoreDashboard({ scanId }: { scanId: string }) {
  const { scan, error } = useScanStatus(scanId);
  const [health, setHealth] = useState<HealthScoreResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);
  const [methodologyOpen, setMethodologyOpen] = useState(false);

  useEffect(() => {
    if (scan?.status !== "completed") return;
    let cancelled = false;
    getHealthScore(scanId)
      .then((result) => {
        if (!cancelled) {
          setHealth(result);
          setHealthError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setHealth(null);
          setHealthError(caught instanceof ScanApiError ? caught.message : emptyHealthCopy("unavailable").body);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scan?.status, scanId, retryToken]);

  const failed = scan?.status === "failed" || Boolean(error);
  const running = !failed && scan?.status !== "completed";
  const empty = emptyHealthCopy(running || !scan ? "incomplete" : healthError ? "unavailable" : "loading");

  return (
    <ScanShell scanId={scanId} current="score">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        {failed ? (
          <StateCard title="Health score unavailable" body={scan?.error?.message ?? error ?? "This scan did not complete."} />
        ) : running || !scan ? (
          <ScoreSkeleton title={empty.title} body={scan?.current_step ?? empty.body} />
        ) : healthError ? (
          <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">{emptyHealthCopy("unavailable").title}</h1>
            <p className="mt-2 text-sm text-muted-foreground">{healthError}</p>
            <button type="button" className={cn(buttonVariants(), "mt-4 h-10 px-4")} onClick={() => setRetryToken((value) => value + 1)}>
              Retry
            </button>
          </section>
        ) : !health ? (
          <ScoreSkeleton title={emptyHealthCopy("loading").title} body={emptyHealthCopy("loading").body} />
        ) : (
          <ScoreBody scanId={scanId} health={health} methodologyOpen={methodologyOpen} onToggleMethodology={() => setMethodologyOpen((open) => !open)} />
        )}
      </div>
    </ScanShell>
  );
}

function ScoreBody({
  scanId,
  health,
  methodologyOpen,
  onToggleMethodology,
}: {
  scanId: string;
  health: HealthScoreResponse;
  methodologyOpen: boolean;
  onToggleMethodology: () => void;
}) {
  const score = health.overall.score;
  const band = health.overall.band || health.overall.status;
  return (
    <>
      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
        <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Website Health</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Website Health</h1>
        <p className="mt-2 text-sm text-muted-foreground">{health.score_note || HEALTH_SCORE_NOTE}</p>
        <div className="mt-6 grid gap-6 lg:grid-cols-[auto_1fr]">
          <ScoreRing score={score} band={typeof score === "number" ? band : "Unavailable"} />
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat label="Score Coverage" value={typeof health.coverage.coverage_percent === "number" ? `${Math.round(health.coverage.coverage_percent)}%` : "Unavailable"} hint={`${coverageLabel(health.coverage.status)}. ${HEALTH_COVERAGE_NOTE}`} />
            <Stat
              label="Analyzed"
              value={`${health.overall.available_categories} of ${health.overall.configured_categories}`}
              hint="categories with usable scores"
            />
            <Stat label="Calculation" value={health.calculation_version} hint="methodology version" />
          </div>
        </div>
        {health.partial_notice ? <p className="mt-4 text-sm text-muted-foreground">{health.partial_notice}</p> : null}
        <p className="mt-3 text-sm text-muted-foreground">{health.coverage_note || HEALTH_COVERAGE_NOTE}</p>
        <Link href={`/scan/${scanId}/report`} className={cn(buttonVariants({ variant: "outline" }), "mt-4 h-10 px-4")}>
          View report
        </Link>
      </section>

      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Category scores</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {health.categories.map((category) => (
            <CategoryCard key={category.category} scanId={scanId} category={category} />
          ))}
        </div>
        {health.architecture ? (
          <p className="mt-4 text-sm text-muted-foreground">
            {health.architecture.name} is informational and is not included in the weighted score.{" "}
            <Link href={`/scan/${scanId}/${health.architecture.href}`} className="underline-offset-2 hover:underline">
              View architecture
            </Link>
          </p>
        ) : null}
      </section>

      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Score breakdown</h2>
        <p className="mt-1 text-sm text-muted-foreground">Measured category scores and configured weights.</p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="py-2 pr-3 font-medium">Category</th>
                <th className="py-2 pr-3 font-medium">Score</th>
                <th className="py-2 pr-3 font-medium">Weight</th>
                <th className="py-2 pr-3 font-medium">Status</th>
                <th className="py-2 font-medium">Contribution</th>
              </tr>
            </thead>
            <tbody>
              {health.categories.map((category) => (
                <tr key={category.category} className="border-b border-border/70">
                  <td className="py-2 pr-3">{category.name}</td>
                  <td className="py-2 pr-3">{typeof category.score === "number" ? category.score : "Unavailable"}</td>
                  <td className="py-2 pr-3">{weightPercent(category.weight)}</td>
                  <td className="py-2 pr-3">{categoryStatusLabel(category.status)}</td>
                  <td className="py-2">{typeof category.weighted_contribution === "number" ? category.weighted_contribution.toFixed(2) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-6 space-y-3">
          {health.categories.map((category) => (
            <ScoreBar key={`${category.category}-bar`} category={category} />
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Score coverage</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {typeof health.coverage.coverage_percent === "number" ? `${Math.round(health.coverage.coverage_percent)}%` : "Unavailable"} ·{" "}
          {health.coverage.available_categories} / {health.coverage.configured_categories} categories available
        </p>
        <ul className="mt-4 grid gap-2 sm:grid-cols-2">
          {health.categories.map((category) => (
            <li key={`${category.category}-cov`} className="rounded-xl border border-border bg-muted/40 p-3 text-sm">
              <p className="font-medium">{category.name}</p>
              <p className="mt-1 text-muted-foreground">
                {categoryStatusLabel(category.status)}
                {category.reason ? ` · ${category.reason}` : ""}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">Issues detected</h2>
        <p className="mt-1 text-sm text-muted-foreground">Issue counts are supporting context and are not subtracted from analyzer scores.</p>
        <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <Count label="Critical" value={health.issue_summary.critical} />
          <Count label="High" value={health.issue_summary.high} />
          <Count label="Medium" value={health.issue_summary.medium} />
          <Count label="Low" value={health.issue_summary.low} />
          <Count label="Info" value={health.issue_summary.info} />
          <Count label="Total" value={health.issue_summary.total} />
        </dl>
        <Link href={`/scan/${scanId}/issues`} className={cn(buttonVariants(), "mt-4 h-10 px-4")}>
          View all issues
        </Link>
      </section>

      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground">How SiteLens calculates this score</h2>
        <button
          type="button"
          className="mt-2 text-sm underline-offset-2 hover:underline"
          onClick={onToggleMethodology}
          aria-expanded={methodologyOpen}
          aria-controls="score-methodology"
        >
          {methodologyOpen ? "Hide methodology" : "Show methodology"}
        </button>
        {methodologyOpen ? (
          <div id="score-methodology" className="mt-4 space-y-3 text-sm text-muted-foreground">
            <ol className="list-decimal space-y-2 pl-5">
              <li>Each analyzer calculates its own category score.</li>
              <li>Category scores are normalized to 0–100.</li>
              <li>Configured category weights determine contribution.</li>
              <li>Unavailable categories are excluded rather than scored as zero.</li>
              <li>Available weights are renormalized.</li>
              <li>Issue counts are shown as supporting context and are not subtracted again.</li>
              <li>Score coverage shows how much of the scoring model was available.</li>
              <li>The score is an analysis metric, not a prediction of business success.</li>
            </ol>
            <p>{health.methodology.formula}</p>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[320px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs">
                    <th className="py-2 pr-3 font-medium">Category</th>
                    <th className="py-2 font-medium">Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {health.categories.map((category) => (
                    <tr key={`${category.category}-w`} className="border-b border-border/70">
                      <td className="py-2 pr-3">{category.name}</td>
                      <td className="py-2">{weightPercent(category.weight)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </section>
    </>
  );
}

function CategoryCard({ scanId, category }: { scanId: string; category: HealthCategoryScore }) {
  return (
    <Link
      href={`/scan/${scanId}/${category.href}`}
      className="rounded-xl border border-border bg-muted/40 p-4 transition-colors hover:bg-muted/70"
      aria-label={`${category.name} ${scoreOutOf100(category.score)} — ${categoryStatusLabel(category.status)}`}
    >
      <p className="text-xs text-muted-foreground">{category.name}</p>
      <p className="mt-1 text-2xl font-semibold">{typeof category.score === "number" ? `${category.score} / 100` : "Unavailable"}</p>
      <p className="mt-2 text-xs text-muted-foreground">
        {categoryStatusLabel(category.status)} · {category.issue_count} {category.issue_count === 1 ? "issue" : "issues"} · {weightPercent(category.weight)}
      </p>
    </Link>
  );
}

function ScoreBar({ category }: { category: HealthCategoryScore }) {
  const width = typeof category.score === "number" ? Math.max(0, Math.min(100, category.score)) : 0;
  return (
    <div aria-label={`${category.name} ${scoreOutOf100(category.score)}, weight ${weightPercent(category.weight)}`}>
      <div className="flex items-center justify-between gap-3 text-sm">
        <p>{category.name}</p>
        <p className="text-muted-foreground">
          {typeof category.score === "number" ? category.score : "Unavailable"} · {weightPercent(category.weight)}
        </p>
      </div>
      <div className="mt-1 h-2 rounded-full bg-muted" aria-hidden="true">
        <div className="h-2 rounded-full bg-primary" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-border bg-muted/40 p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

function Count({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-muted/40 p-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-xl font-semibold">{value}</dd>
    </div>
  );
}

function StateCard({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
    </section>
  );
}

function ScoreSkeleton({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8" aria-busy="true">
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
      <div className="mt-6 h-40 animate-pulse rounded-2xl bg-muted" aria-hidden="true" />
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="h-24 animate-pulse rounded-xl bg-muted" aria-hidden="true" />
        <div className="h-24 animate-pulse rounded-xl bg-muted" aria-hidden="true" />
        <div className="h-24 animate-pulse rounded-xl bg-muted" aria-hidden="true" />
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div className="h-28 animate-pulse rounded-xl bg-muted" aria-hidden="true" />
        <div className="h-28 animate-pulse rounded-xl bg-muted" aria-hidden="true" />
        <div className="h-28 animate-pulse rounded-xl bg-muted" aria-hidden="true" />
        <div className="h-28 animate-pulse rounded-xl bg-muted" aria-hidden="true" />
        <div className="h-28 animate-pulse rounded-xl bg-muted" aria-hidden="true" />
        <div className="h-28 animate-pulse rounded-xl bg-muted" aria-hidden="true" />
      </div>
      <div className="mt-6 h-48 animate-pulse rounded-xl bg-muted" aria-hidden="true" />
    </section>
  );
}
