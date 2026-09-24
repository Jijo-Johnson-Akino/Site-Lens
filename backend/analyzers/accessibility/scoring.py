from __future__ import annotations

from backend.analyzers.accessibility.config import DEFAULT_SCORING, A11yScoringConfig
from backend.analyzers.accessibility.models import A11yIssue, A11ySummary, CheckResult

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

CATEGORY_LABELS = {
    "document": "Document",
    "landmarks": "Landmarks",
    "headings": "Headings",
    "images": "Images",
    "links": "Links",
    "controls": "Controls",
    "forms": "Forms",
    "aria": "ARIA",
    "keyboard": "Keyboard",
    "tables": "Tables",
    "media": "Media",
    "contrast": "Color Contrast",
    "other": "Other",
}


def apply_weights(checks: list[CheckResult], config: A11yScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    return [check.model_copy(update={"weight": config.weight_for(check.check_id)}) for check in checks]


def category_scores(checks: list[CheckResult], config: A11yScoringConfig = DEFAULT_SCORING) -> dict[str, int | None]:
    scores: dict[str, int | None] = {}
    for group in config.category_weights:
        group_checks = [check for check in checks if check.group == group]
        applicable = [check for check in group_checks if check.status != "not_applicable" and check.score is not None]
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


def overall_score(checks: list[CheckResult], config: A11yScoringConfig = DEFAULT_SCORING) -> int:
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


def summarize(checks: list[CheckResult]) -> A11ySummary:
    return A11ySummary(
        passed=sum(1 for check in checks if check.status == "pass"),
        warnings=sum(1 for check in checks if check.status == "warning"),
        failed=sum(1 for check in checks if check.status == "fail"),
        not_applicable=sum(1 for check in checks if check.status == "not_applicable"),
        manual_review=sum(1 for check in checks if check.manual_review or check.source == "manual-review"),
    )


def collect_issues(checks: list[CheckResult]) -> list[A11yIssue]:
    issues = [
        A11yIssue(
            check_id=check.check_id,
            name=check.name,
            status=check.status,
            severity=check.severity,
            message=check.message,
            recommendation=check.recommendation,
            why=check.why,
            page_url=check.page_url,
            selector=check.selector,
            affected_element=check.affected_element,
            affected_element_count=check.affected_element_count,
            wcag_reference=check.wcag_reference,
            source=check.source,
            detected=check.detected,
            manual_review=check.manual_review,
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
    failed = [check for check in checks if check.status == "fail"]
    lines = [f"Accessibility Score: {score}/100", ""]
    if failed:
        lines.append(failed[0].message)
    else:
        lines.append("No blocking automated accessibility failures were detected on this page.")
    lines.append("This is an automated audit only. It does not guarantee WCAG or legal compliance.")
    return "\n".join(lines).strip()


def merge_findings(dom_checks: list[CheckResult], axe_checks: list[CheckResult]) -> list[CheckResult]:
    by_id = {check.check_id: check for check in dom_checks}
    extras: list[CheckResult] = []
    for axe in axe_checks:
        current = by_id.get(axe.check_id)
        if current is None:
            extras.append(axe)
            continue
        if axe.status == "fail" or (axe.status == "warning" and current.status == "pass"):
            by_id[axe.check_id] = axe.model_copy(
                update={
                    "weight": current.weight,
                    "affected_element_count": max(axe.affected_element_count, current.affected_element_count),
                }
            )
        elif axe.status == "fail" and current.status == "fail":
            by_id[axe.check_id] = axe.model_copy(update={"weight": current.weight})
    return list(by_id.values()) + extras
