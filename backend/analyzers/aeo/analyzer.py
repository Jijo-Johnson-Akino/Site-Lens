from __future__ import annotations

from backend.analyzers.aeo.checks import CHECK_RUNNERS
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import AeoPageInfo, AeoResult, CheckResult
from backend.analyzers.aeo.scoring import (
    DEFAULT_SCORING,
    AEOScoringConfig,
    apply_weights,
    category_scores,
    collect_issues,
    insight_summary,
    narrative_summary,
    overall_score,
    summarize,
)


def collect_checks(ctx: AeoContext) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for runner in CHECK_RUNNERS:
        checks.extend(runner(ctx))
    return checks


def analyze_aeo(ctx: AeoContext, config: AEOScoringConfig | None = None) -> AeoResult:
    scoring = config or DEFAULT_SCORING
    checks = apply_weights(collect_checks(ctx), scoring)
    categories = category_scores(checks, scoring)
    score = overall_score(categories, scoring)
    h1s = ctx.html.get("h1s") or []
    first_h1 = next((item.get("text") for item in h1s if item.get("text")), None)
    return AeoResult(
        score=score,
        summary=summarize(checks),
        narrative=narrative_summary(score, checks),
        insight=insight_summary(checks),
        categories=categories,
        checks=checks,
        issues=collect_issues(checks),
        page=AeoPageInfo(
            analyzed_url=ctx.page_url,
            final_url=ctx.final_url,
            status_code=ctx.status_code,
            title=ctx.html.get("title"),
            h1=first_h1,
            language=ctx.html.get("language"),
        ),
    )
