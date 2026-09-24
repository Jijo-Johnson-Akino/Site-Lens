from __future__ import annotations

from backend.analyzers.mobile.config import CATEGORY_LABELS, DEFAULT_SCORING, MobileScoringConfig
from backend.analyzers.mobile.models import CheckResult, MobileCategoryScore, MobileIssue, MobileSummary

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def apply_weights(checks: list[CheckResult], config: MobileScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    return [check.model_copy(update={"weight": config.weight_for(check.check_id)}) for check in checks]


def _bucket_checks(checks: list[CheckResult], config: MobileScoringConfig) -> dict[str, list[CheckResult]]:
    grouped: dict[str, list[CheckResult]] = {bucket: [] for bucket in config.category_weights}
    for check in checks:
        bucket = config.bucket_for(check.group)
        grouped.setdefault(bucket, []).append(check)
    return grouped


def category_scores(checks: list[CheckResult], config: MobileScoringConfig = DEFAULT_SCORING) -> dict[str, int | None]:
    grouped = _bucket_checks(checks, config)
    scores: dict[str, int | None] = {}
    for bucket, weight in config.category_weights.items():
        del weight
        applicable = [check for check in grouped.get(bucket, []) if check.status != "not_applicable" and check.score is not None]
        if not applicable:
            scores[bucket] = None
            continue
        earned = 0.0
        possible = 0.0
        for check in applicable:
            item_weight = check.weight or config.weight_for(check.check_id)
            earned += float(check.score) * item_weight
            possible += item_weight
        scores[bucket] = int(max(0, min(100, round(100 * earned / possible)))) if possible else None
    return scores


def overall_score(checks: list[CheckResult], config: MobileScoringConfig = DEFAULT_SCORING) -> int:
    categories = category_scores(checks, config)
    weighted = 0.0
    total = 0.0
    for bucket, weight in config.category_weights.items():
        value = categories.get(bucket)
        if value is None or weight <= 0:
            continue
        weighted += value * weight
        total += weight
    if total <= 0:
        return 0
    return int(max(0, min(100, round(weighted / total))))


def summarize(checks: list[CheckResult]) -> MobileSummary:
    return MobileSummary(
        passed=sum(1 for check in checks if check.status == "pass"),
        warnings=sum(1 for check in checks if check.status == "warning"),
        failed=sum(1 for check in checks if check.status == "fail"),
        not_applicable=sum(1 for check in checks if check.status == "not_applicable"),
    )


def collect_issues(checks: list[CheckResult]) -> list[MobileIssue]:
    issues = [
        MobileIssue(
            check_id=check.check_id,
            name=check.name,
            status=check.status,
            severity=check.severity,
            message=check.message,
            recommendation=check.recommendation,
            why=check.why,
            page_url=check.page_url,
            selector=check.selector,
            affected_element_count=check.affected_element_count,
            viewport=check.viewport,
            measured_value=check.measured_value,
            expected_value=check.expected_value,
            detected=check.detected,
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


def group_status(checks: list[CheckResult], group: str) -> str:
    items = [check for check in checks if check.group == group]
    if not items:
        return "not_applicable"
    if all(check.status == "not_applicable" for check in items):
        return "not_applicable"
    if any(check.status == "fail" for check in items):
        return "fail"
    if any(check.status == "warning" for check in items):
        return "warning"
    return "pass"


def category_cards(checks: list[CheckResult], config: MobileScoringConfig = DEFAULT_SCORING) -> list[MobileCategoryScore]:
    group_scores: dict[str, int | None] = {}
    for group in CATEGORY_LABELS:
        applicable = [check for check in checks if check.group == group and check.status != "not_applicable" and check.score is not None]
        if not applicable:
            group_scores[group] = None
            continue
        earned = 0.0
        possible = 0.0
        for check in applicable:
            weight = check.weight or config.weight_for(check.check_id)
            earned += float(check.score) * weight
            possible += weight
        group_scores[group] = int(max(0, min(100, round(100 * earned / possible)))) if possible else None
    cards: list[MobileCategoryScore] = []
    for group, label in CATEGORY_LABELS.items():
        items = [check for check in checks if check.group == group]
        cards.append(
            MobileCategoryScore(
                id=group,
                name=label,
                score=group_scores.get(group),
                finding_count=sum(1 for check in items if check.status in {"fail", "warning"}),
                status=group_status(checks, group),
            )
        )
    return cards


def narrative_summary(score: int, checks: list[CheckResult]) -> str:
    if score >= 90:
        band = "Strong mobile layout signals"
    elif score >= 75:
        band = "Some mobile improvements identified"
    elif score >= 50:
        band = "Several mobile usability issues detected"
    else:
        band = "Significant mobile issues detected"
    lines = [f"Mobile Score: {score}/100", "", band + "."]
    warning = next((check for check in checks if check.status in {"fail", "warning"}), None)
    if warning:
        lines.append(warning.message)
    lines.append("These descriptions refer only to the automated mobile scan.")
    return "\n".join(lines).strip()


def overview_cards(checks: list[CheckResult]) -> dict[str, dict[str, int | str]]:
    keys = ("overflow", "navigation", "touch", "viewport", "visibility")
    cards: dict[str, dict[str, int | str]] = {}
    for key in keys:
        items = [check for check in checks if check.group == key]
        cards[key] = {
            "status": group_status(checks, key),
            "warnings": sum(1 for check in items if check.status == "warning"),
            "failed": sum(1 for check in items if check.status == "fail"),
            "passed": sum(1 for check in items if check.status == "pass"),
        }
    return cards


__all__ = [
    "GROUP_TO_BUCKET",
    "apply_weights",
    "category_cards",
    "category_scores",
    "collect_issues",
    "group_status",
    "narrative_summary",
    "overall_score",
    "overview_cards",
    "severity_counts",
    "summarize",
]
