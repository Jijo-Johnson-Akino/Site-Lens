from __future__ import annotations

from backend.analyzers.cro.config import CATEGORY_LABELS, CATEGORY_WEIGHTS
from backend.analyzers.cro.models import CheckResult, CroCategoryScore, CroIssue, CroSummary

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def apply_weights(checks: list[CheckResult]) -> list[CheckResult]:
    weighted = []
    for check in checks:
        weight = CATEGORY_WEIGHTS.get(check.group, 0)
        weighted.append(check.model_copy(update={"weight": weight}))
    return weighted


def category_scores(checks: list[CheckResult]) -> dict[str, int | None]:
    scores: dict[str, int | None] = {}
    for group in CATEGORY_WEIGHTS:
        group_checks = [item for item in checks if item.group == group]
        applicable = [item for item in group_checks if item.status != "not_applicable" and item.score is not None]
        if not applicable:
            scores[group] = None
            continue
        earned = sum(float(item.score) * (item.weight or CATEGORY_WEIGHTS[group]) for item in applicable)
        possible = sum((item.weight or CATEGORY_WEIGHTS[group]) for item in applicable)
        scores[group] = int(max(0, min(100, round(100 * earned / possible)))) if possible else None
    return scores


def overall_score(checks: list[CheckResult]) -> int | None:
    categories = category_scores(checks)
    weighted = 0.0
    total = 0.0
    for group, weight in CATEGORY_WEIGHTS.items():
        value = categories.get(group)
        if value is None or weight <= 0:
            continue
        weighted += value * weight
        total += weight
    if total <= 0:
        return None
    return int(max(0, min(100, round(weighted / total))))


def category_cards(checks: list[CheckResult]) -> list[CroCategoryScore]:
    scores = category_scores(checks)
    cards: list[CroCategoryScore] = []
    for group, label in CATEGORY_LABELS.items():
        group_checks = [item for item in checks if item.group == group and item.status in {"fail", "warning"}]
        cards.append(
            CroCategoryScore(
                id=group,
                name=label,
                score=scores.get(group),
                finding_count=len(group_checks),
            )
        )
    return cards


def summarize(checks: list[CheckResult], *, pages_analyzed: int) -> CroSummary:
    actionable = [item for item in checks if item.status in {"fail", "warning"}]
    return CroSummary(
        passed=sum(1 for item in checks if item.status == "pass"),
        warnings=sum(1 for item in checks if item.status == "warning"),
        failed=sum(1 for item in checks if item.status == "fail"),
        not_applicable=sum(1 for item in checks if item.status == "not_applicable"),
        pages_analyzed=pages_analyzed,
        cta_issues=sum(1 for item in actionable if item.group in {"primary_cta", "cta_clarity"}),
        form_issues=sum(1 for item in actionable if item.group == "forms"),
        conversion_path_issues=sum(1 for item in actionable if item.group == "conversion_path"),
        mobile_issues=sum(1 for item in actionable if item.group == "mobile"),
        open_findings=len(actionable),
    )


def collect_issues(checks: list[CheckResult]) -> list[CroIssue]:
    issues = [
        CroIssue(
            check_id=check.check_id,
            name=check.name,
            status=check.status,
            severity=check.severity,
            message=check.message,
            recommendation=check.recommendation,
            why=check.why,
            page_url=check.page_url,
            selector=check.selector,
            detected=check.detected,
        )
        for check in checks
        if check.status in {"fail", "warning"}
    ]
    issues.sort(key=lambda item: (SEVERITY_ORDER.get(item.severity, 9), item.check_id, item.page_url))
    return issues


def narrative_summary(score: int | None, summary: CroSummary) -> str:
    if score is None:
        return "CRO analysis unavailable."
    return (
        f"Observed conversion-readiness score {score}/100 across {summary.pages_analyzed} analyzed page"
        f"{'' if summary.pages_analyzed == 1 else 's'}. "
        f"{summary.open_findings} conversion-related finding{'' if summary.open_findings == 1 else 's'} "
        "were recorded from SiteLens measurements."
    )
