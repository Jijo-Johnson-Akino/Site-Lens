from __future__ import annotations

from dataclasses import dataclass, field

from backend.analyzers.seo.models import CheckResult, SeoIssue, SeoSummary

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

DEFAULT_CHECK_WEIGHTS: dict[str, int] = {
    "SEO-TITLE-001": 10,
    "SEO-TITLE-002": 4,
    "SEO-TITLE-003": 2,
    "SEO-TITLE-004": 5,
    "SEO-META-001": 8,
    "SEO-META-002": 6,
    "SEO-META-003": 4,
    "SEO-META-004": 2,
    "SEO-H1-001": 10,
    "SEO-H1-002": 4,
    "SEO-H1-003": 6,
    "SEO-H2-001": 2,
    "SEO-HEAD-001": 3,
    "SEO-CAN-001": 8,
    "SEO-CAN-002": 6,
    "SEO-CAN-003": 5,
    "SEO-INDEX-001": 8,
    "SEO-INDEX-002": 6,
    "SEO-INDEX-003": 10,
    "SEO-ROBOTS-001": 6,
    "SEO-ROBOTS-002": 4,
    "SEO-ROBOTS-003": 3,
    "SEO-SITEMAP-001": 5,
    "SEO-SITEMAP-002": 3,
    "SEO-SITEMAP-003": 3,
    "SEO-URL-001": 10,
    "SEO-URL-002": 3,
    "SEO-URL-003": 2,
    "SEO-IMG-001": 8,
    "SEO-IMG-002": 3,
    "SEO-IMG-003": 3,
    "SEO-IMG-004": 2,
    "SEO-LINK-001": 4,
    "SEO-LINK-002": 2,
    "SEO-LINK-003": 5,
    "SEO-LINK-004": 2,
    "SEO-LINK-005": 3,
    "SEO-SOCIAL-001": 4,
    "SEO-SOCIAL-002": 3,
    "SEO-SOCIAL-003": 4,
    "SEO-SOCIAL-004": 3,
    "SEO-HTML-001": 5,
    "SEO-HTML-002": 4,
    "SEO-HTML-003": 3,
}

DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "metadata": 0.20,
    "indexability": 0.20,
    "headings": 0.10,
    "canonical": 0.10,
    "images": 0.10,
    "links": 0.10,
    "technical": 0.10,
    "social": 0.05,
    "robots_sitemap": 0.05,
}


@dataclass(frozen=True)
class SEOScoringConfig:
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    check_weights: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CHECK_WEIGHTS))

    def weight_for(self, check_id: str) -> int:
        return self.check_weights.get(check_id, 1)


DEFAULT_SCORING = SEOScoringConfig()


def apply_weights(checks: list[CheckResult], config: SEOScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    weighted: list[CheckResult] = []
    for check in checks:
        weighted.append(check.model_copy(update={"weight": config.weight_for(check.check_id)}))
    return weighted


def category_scores(checks: list[CheckResult], config: SEOScoringConfig = DEFAULT_SCORING) -> dict[str, int | None]:
    earned: dict[str, float] = {}
    possible: dict[str, float] = {}
    for check in checks:
        if check.status == "not_applicable" or check.score is None:
            continue
        weight = check.weight or config.weight_for(check.check_id)
        earned[check.group] = earned.get(check.group, 0.0) + check.score * weight
        possible[check.group] = possible.get(check.group, 0.0) + weight

    scores: dict[str, int | None] = {}
    for group in config.category_weights:
        total = possible.get(group)
        if not total:
            scores[group] = None
        else:
            scores[group] = int(round(100 * earned[group] / total))
    return scores


def overall_score(categories: dict[str, int | None], config: SEOScoringConfig = DEFAULT_SCORING) -> int:
    weighted = 0.0
    total = 0.0
    for group, weight in config.category_weights.items():
        value = categories.get(group)
        if value is None:
            continue
        weighted += value * weight
        total += weight
    if total <= 0:
        return 0
    return int(max(0, min(100, round(weighted / total))))


def summarize(checks: list[CheckResult]) -> SeoSummary:
    return SeoSummary(
        passed=sum(1 for check in checks if check.status == "pass"),
        warnings=sum(1 for check in checks if check.status == "warning"),
        failed=sum(1 for check in checks if check.status == "fail"),
        not_applicable=sum(1 for check in checks if check.status == "not_applicable"),
    )


def collect_issues(checks: list[CheckResult]) -> list[SeoIssue]:
    issues = [
        SeoIssue(
            check_id=check.check_id,
            name=check.name,
            status=check.status,
            severity=check.severity,
            message=check.message,
            recommendation=check.recommendation,
        )
        for check in checks
        if check.status in {"fail", "warning"}
    ]
    issues.sort(key=lambda item: (SEVERITY_ORDER.get(item.severity, 9), item.name))
    return issues


def _join_and(parts: list[str]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def narrative_summary(score: int, checks: list[CheckResult]) -> str:
    by_id = {check.check_id: check for check in checks}
    positives: list[str] = []
    if by_id.get("SEO-TITLE-001") and by_id["SEO-TITLE-001"].status == "pass":
        positives.append("a page title")
    if by_id.get("SEO-CAN-001") and by_id["SEO-CAN-001"].status == "pass":
        positives.append("a canonical URL")
    if by_id.get("SEO-URL-001") and by_id["SEO-URL-001"].status == "pass":
        positives.append("HTTPS")

    lines = [f"SEO Score: {score}/100", ""]
    if positives:
        lines.append(f"The page has {_join_and(positives)}.")

    concerns: list[str] = []
    for check in checks:
        if check.status == "fail":
            concerns.append(check.message.rstrip("."))
        elif check.status == "warning" and check.severity in {"critical", "high", "medium"}:
            concerns.append(check.message.rstrip("."))
        if len(concerns) >= 2:
            break
    if concerns:
        if len(concerns) == 1:
            lines.append(f"{concerns[0]}.")
        else:
            lines.append(f"{concerns[0]}, and {concerns[1][0].lower() + concerns[1][1:]}.")
    elif score >= 90:
        lines.append("No high-priority SEO issues were detected on this page.")
    return "\n".join(lines).strip()
