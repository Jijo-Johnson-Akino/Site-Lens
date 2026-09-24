from __future__ import annotations

from backend.analyzers.content.config import DEFAULT_SCORING, ContentScoringConfig
from backend.analyzers.content.models import CheckResult, ContentIssue, ContentSummary

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

CATEGORY_LABELS = {
    "structure": "Content Structure",
    "depth": "Content Depth",
    "readability": "Readability",
    "headings": "Headings",
    "paragraphs": "Paragraphs",
    "duplication": "Content Duplication",
    "freshness": "Freshness",
    "authorship": "Authorship",
    "completeness": "Completeness",
    "relationships": "Internal Relationships",
    "language": "Language",
}


def apply_weights(checks: list[CheckResult], config: ContentScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    return [check.model_copy(update={"weight": config.weight_for(check.check_id)}) for check in checks]


def category_scores(checks: list[CheckResult], config: ContentScoringConfig = DEFAULT_SCORING) -> dict[str, int | None]:
    scores: dict[str, int | None] = {}
    for group in config.category_weights:
        applicable = [check for check in checks if check.group == group and check.status != "not_applicable" and check.score is not None]
        if not applicable:
            scores[group] = None
            continue
        earned = 0.0
        possible = 0.0
        for check in applicable:
            weight = check.weight or config.weight_for(check.check_id)
            earned += float(check.score) * weight
            possible += weight
        scores[group] = int(max(0, min(100, round(100 * earned / possible)))) if possible else None
    return scores


def overall_score(checks: list[CheckResult], config: ContentScoringConfig = DEFAULT_SCORING) -> int:
    categories = category_scores(checks, config)
    weighted = 0.0
    total = 0.0
    for group, weight in config.category_weights.items():
        value = categories.get(group)
        if value is None or weight <= 0:
            continue
        weighted += value * weight
        total += weight
    if total <= 0:
        return 0
    return int(max(0, min(100, round(weighted / total))))


def summarize(checks: list[CheckResult]) -> ContentSummary:
    return ContentSummary(
        passed=sum(1 for check in checks if check.status == "pass"),
        warnings=sum(1 for check in checks if check.status == "warning"),
        failed=sum(1 for check in checks if check.status == "fail"),
        not_applicable=sum(1 for check in checks if check.status == "not_applicable"),
    )


def collect_issues(checks: list[CheckResult]) -> list[ContentIssue]:
    issues = [
        ContentIssue(
            check_id=check.check_id,
            name=check.name,
            status=check.status,
            severity=check.severity,
            message=check.message,
            recommendation=check.recommendation,
            why=check.why,
            page_url=check.page_url,
            detected=check.detected,
            affected_element_count=check.affected_element_count,
        )
        for check in checks
        if check.status in {"fail", "warning"}
    ]
    issues.sort(key=lambda item: (SEVERITY_ORDER.get(item.severity, 9), item.name))
    return issues


def severity_counts(checks: list[CheckResult]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for check in checks:
        if check.status in {"fail", "warning"}:
            counts[check.severity] = counts.get(check.severity, 0) + 1
    return counts


def narrative_summary(score: int, checks: list[CheckResult]) -> str:
    if score >= 90:
        band = "Strong measurable content signals"
    elif score >= 75:
        band = "Generally healthy content signals with opportunities"
    elif score >= 50:
        band = "Several content improvements identified"
    else:
        band = "Significant content issues detected"
    lines = [f"Content Score: {score}/100", "", band + "."]
    warning = next((check for check in checks if check.status in {"fail", "warning"}), None)
    if warning:
        lines.append(warning.message)
    lines.append("These descriptions refer only to automated measurable signals, not editorial quality.")
    return "\n".join(lines).strip()
