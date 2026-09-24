from __future__ import annotations

from backend.analyzers.structured_data.config import DEFAULT_SCORING, SchemaScoringConfig
from backend.analyzers.structured_data.models import CheckResult, SchemaIssue, SchemaSummary

CATEGORY_LABELS = {
    "detection": "Detection",
    "syntax": "Syntax",
    "schema_types": "Schema Types",
    "identity": "Entity Identity",
    "properties": "Properties",
    "relationships": "Relationships",
    "urls": "URLs & IDs",
    "consistency": "Consistency",
    "alignment": "Visible Content Alignment",
    "social": "Social Metadata",
}


def apply_weights(checks: list[CheckResult], config: SchemaScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    return [check.model_copy(update={"weight": config.weight_for(check.check_id)}) for check in checks]


def category_scores(checks: list[CheckResult], config: SchemaScoringConfig = DEFAULT_SCORING) -> dict[str, int | None]:
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


def overall_score(checks: list[CheckResult], config: SchemaScoringConfig = DEFAULT_SCORING) -> int:
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


def summarize(checks: list[CheckResult], **counts) -> SchemaSummary:
    return SchemaSummary(
        passed=sum(1 for check in checks if check.status == "pass"),
        warnings=sum(1 for check in checks if check.status == "warning"),
        failed=sum(1 for check in checks if check.status == "fail"),
        not_applicable=sum(1 for check in checks if check.status == "not_applicable"),
        info=sum(1 for check in checks if check.status == "info"),
        **counts,
    )


def collect_issues(checks: list[CheckResult]) -> list[SchemaIssue]:
    issues = [
        SchemaIssue(
            check_id=check.check_id,
            name=check.name,
            status=check.status,
            severity=check.severity,
            message=check.message,
            recommendation=check.recommendation,
            why=check.why,
            page_url=check.page_url,
            detected=check.detected,
            source=check.source,
            schema_type=check.schema_type,
            affected_entity=check.affected_entity,
        )
        for check in checks
        if check.status in {"fail", "warning"}
    ]
    issues.sort(key=lambda item: ({"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(item.severity, 9), item.name))
    return issues


def severity_counts(checks: list[CheckResult]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for check in checks:
        if check.status in {"fail", "warning"}:
            counts[check.severity] = counts.get(check.severity, 0) + 1
    return counts


def narrative_summary(score: int, checks: list[CheckResult]) -> str:
    if score >= 90:
        band = "Strong measurable structured-data signals"
    elif score >= 75:
        band = "Generally healthy structured-data signals with opportunities"
    elif score >= 50:
        band = "Several structured-data improvements identified"
    else:
        band = "Significant structured-data issues detected"
    lines = [f"Structured Data Score: {score}/100", "", band + "."]
    notable = next((check for check in checks if check.status in {"fail", "warning"}), None)
    if notable:
        lines.append(notable.message)
    lines.append("These results describe markup that is present. They do not prove rich results, rankings, or AI citations.")
    return "\n".join(lines).strip()
