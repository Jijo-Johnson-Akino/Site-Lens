from __future__ import annotations

from backend.analyzers.seo.checks import CHECK_RUNNERS
from backend.analyzers.seo.checks.indexing import indexability_of
from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, SeoPageInfo, SeoResult
from backend.analyzers.seo.scoring import (
    DEFAULT_SCORING,
    SEOScoringConfig,
    apply_weights,
    category_scores,
    collect_issues,
    narrative_summary,
    overall_score,
    summarize,
)


def collect_checks(ctx: SeoContext) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for runner in CHECK_RUNNERS:
        checks.extend(runner(ctx))
    return checks


def analyze_seo(ctx: SeoContext, config: SEOScoringConfig | None = None) -> SeoResult:
    scoring = config or DEFAULT_SCORING
    checks = apply_weights(collect_checks(ctx), scoring)
    categories = category_scores(checks, scoring)
    score = overall_score(categories, scoring)
    h1s = ctx.html.get("h1s") or []
    first_h1 = next((item.get("text") for item in h1s if item.get("text")), None)
    return SeoResult(
        score=score,
        summary=summarize(checks),
        narrative=narrative_summary(score, checks),
        categories=categories,
        checks=checks,
        issues=collect_issues(checks),
        page=SeoPageInfo(
            analyzed_url=ctx.page_url,
            final_url=ctx.final_url,
            status_code=ctx.status_code,
            title=ctx.html.get("title"),
            h1=first_h1,
        ),
        indexable=indexability_of(ctx),
    )
