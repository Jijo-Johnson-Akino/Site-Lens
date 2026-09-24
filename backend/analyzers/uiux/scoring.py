from __future__ import annotations

from backend.analyzers.uiux.models import CheckResult, UiuxIssue, UiuxSummary
from backend.analyzers.uiux.config import DEFAULT_SCORING, UIUXScoringConfig

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def apply_weights(checks: list[CheckResult], config: UIUXScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    return [check.model_copy(update={"weight": config.weight_for(check.check_id)}) for check in checks]


def _weighted_ratio(checks: list[CheckResult], config: UIUXScoringConfig, *, use_viewport: bool) -> int:
    earned = 0.0
    possible = 0.0
    for check in checks:
        if check.status == "not_applicable" or check.score is None:
            continue
        viewport_weight = config.viewport_weight(check.viewport) if use_viewport else 1.0
        if viewport_weight <= 0:
            continue
        weight = check.weight or config.weight_for(check.check_id)
        earned += float(check.score) * weight * viewport_weight
        possible += weight * viewport_weight
    if possible <= 0:
        return 0
    return int(max(0, min(100, round(100 * earned / possible))))


def category_scores(checks: list[CheckResult], config: UIUXScoringConfig = DEFAULT_SCORING) -> dict[str, int | None]:
    scores: dict[str, int | None] = {}
    for group in config.category_weights:
        group_checks = [check for check in checks if check.group == group]
        applicable = [check for check in group_checks if check.status != "not_applicable" and check.score is not None]
        if not applicable:
            scores[group] = None
        else:
            scores[group] = _weighted_ratio(group_checks, config, use_viewport=True)
    return scores


def overall_score(checks: list[CheckResult], config: UIUXScoringConfig = DEFAULT_SCORING) -> int:
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


def viewport_score(checks: list[CheckResult], config: UIUXScoringConfig = DEFAULT_SCORING) -> int:
    return _weighted_ratio(checks, config, use_viewport=False)


def summarize(checks: list[CheckResult]) -> UiuxSummary:
    return UiuxSummary(
        passed=sum(1 for check in checks if check.status == "pass"),
        warnings=sum(1 for check in checks if check.status == "warning"),
        failed=sum(1 for check in checks if check.status == "fail"),
        not_applicable=sum(1 for check in checks if check.status == "not_applicable"),
    )


def collect_issues(checks: list[CheckResult]) -> list[UiuxIssue]:
    issues = [
        UiuxIssue(
            check_id=check.check_id,
            name=check.name,
            status=check.status,
            severity=check.severity,
            message=check.message,
            recommendation=check.recommendation,
            why=check.why,
            viewport=check.viewport,
            page_url=check.page_url,
            affected_element=check.affected_element,
            detected=check.detected,
        )
        for check in checks
        if check.status in {"fail", "warning"}
    ]
    issues.sort(key=lambda item: (SEVERITY_ORDER.get(item.severity, 9), item.viewport, item.name))
    return issues


def narrative_summary(score: int, checks: list[CheckResult]) -> str:
    failed = [check for check in checks if check.status == "fail"]
    overflow = next((check for check in failed if check.check_id == "UX-RESP-001"), None)
    lines = [f"UI/UX Score: {score}/100", ""]
    if overflow:
        lines.append(overflow.message)
    elif failed:
        lines.append(failed[0].message)
    else:
        lines.append("Observable layout, navigation, and interactive measurements were collected across tested viewports.")
    lines.append("This score is based on rendered layout measurements, not subjective design opinions.")
    return "\n".join(lines).strip()
