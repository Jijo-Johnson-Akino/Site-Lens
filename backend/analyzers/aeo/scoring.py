from __future__ import annotations

from dataclasses import dataclass, field

from backend.analyzers.aeo.models import AeoIssue, AeoSummary, CheckResult

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

DEFAULT_CHECK_WEIGHTS: dict[str, int] = {
    "AEO-ENTITY-001": 10,
    "AEO-ENTITY-002": 6,
    "AEO-ENTITY-003": 8,
    "AEO-ENTITY-004": 5,
    "AEO-ANSWER-001": 10,
    "AEO-ANSWER-002": 6,
    "AEO-ANSWER-003": 7,
    "AEO-ANSWER-004": 6,
    "AEO-QUESTION-001": 8,
    "AEO-QUESTION-002": 6,
    "AEO-QUESTION-003": 8,
    "AEO-STRUCT-001": 8,
    "AEO-STRUCT-002": 7,
    "AEO-STRUCT-003": 5,
    "AEO-STRUCT-004": 3,
    "AEO-SEM-001": 5,
    "AEO-SEM-002": 8,
    "AEO-SEM-003": 4,
    "AEO-AUTHOR-001": 7,
    "AEO-AUTHOR-002": 5,
    "AEO-AUTHOR-003": 4,
    "AEO-ORG-001": 7,
    "AEO-ORG-002": 6,
    "AEO-ORG-003": 6,
    "AEO-SCHEMA-001": 8,
    "AEO-SCHEMA-002": 6,
    "AEO-SCHEMA-003": 5,
    "AEO-EXTRACT-001": 5,
    "AEO-EXTRACT-002": 10,
    "AEO-EXTRACT-003": 4,
    "AEO-EXTRACT-004": 3,
    "AEO-AI-001": 4,
    "AEO-AI-002": 3,
    "AEO-AI-003": 8,
}

DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "entity_understanding": 0.15,
    "answer_readiness": 0.20,
    "question_coverage": 0.10,
    "content_structure": 0.15,
    "semantic_structure": 0.10,
    "authorship": 0.10,
    "organization_information": 0.10,
    "structured_information": 0.05,
    "extractability": 0.05,
}


@dataclass(frozen=True)
class AEOScoringConfig:
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    check_weights: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CHECK_WEIGHTS))

    def weight_for(self, check_id: str) -> int:
        return self.check_weights.get(check_id, 1)


DEFAULT_SCORING = AEOScoringConfig()


def apply_weights(checks: list[CheckResult], config: AEOScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    return [check.model_copy(update={"weight": config.weight_for(check.check_id)}) for check in checks]


def category_scores(checks: list[CheckResult], config: AEOScoringConfig = DEFAULT_SCORING) -> dict[str, int | None]:
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


def overall_score(categories: dict[str, int | None], config: AEOScoringConfig = DEFAULT_SCORING) -> int:
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


def summarize(checks: list[CheckResult]) -> AeoSummary:
    return AeoSummary(
        passed=sum(1 for check in checks if check.status == "pass"),
        warnings=sum(1 for check in checks if check.status == "warning"),
        failed=sum(1 for check in checks if check.status == "fail"),
        not_applicable=sum(1 for check in checks if check.status == "not_applicable"),
    )


def collect_issues(checks: list[CheckResult]) -> list[AeoIssue]:
    issues = [
        AeoIssue(
            check_id=check.check_id,
            name=check.name,
            status=check.status,
            severity=check.severity,
            message=check.message,
            recommendation=check.recommendation,
            why=check.why,
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
    if by_id.get("AEO-ENTITY-001") and by_id["AEO-ENTITY-001"].status == "pass":
        positives.append("a clear organization identity")
    if by_id.get("AEO-SCHEMA-001") and by_id["AEO-SCHEMA-001"].status == "pass":
        positives.append("structured data")
    if by_id.get("AEO-SEM-002") and by_id["AEO-SEM-002"].status == "pass":
        positives.append("a main content landmark")
    lines = [f"AEO Score: {score}/100", ""]
    if positives:
        lines.append(f"The page exposes {_join_and(positives)}.")
    concerns: list[str] = []
    for check in checks:
        if check.status == "fail":
            concerns.append(check.message.rstrip("."))
        elif check.status == "warning" and check.severity in {"high", "medium"}:
            concerns.append(check.message.rstrip("."))
        if len(concerns) >= 2:
            break
    if concerns:
        if len(concerns) == 1:
            lines.append(f"{concerns[0]}.")
        else:
            second = concerns[1][0].lower() + concerns[1][1:] if concerns[1] else concerns[1]
            lines.append(f"{concerns[0]}, and {second}.")
    lines.append("This is a measure of observable extractability, not a prediction of AI search rankings or citations.")
    return "\n".join(lines).strip()


OPPORTUNITY_IDS = (
    "AEO-ANSWER-001",
    "AEO-ANSWER-002",
    "AEO-QUESTION-001",
    "AEO-QUESTION-002",
    "AEO-AUTHOR-001",
    "AEO-EXTRACT-003",
    "AEO-ENTITY-003",
    "AEO-ORG-001",
    "AEO-SCHEMA-001",
)

STRENGTH_IDS = (
    "AEO-ENTITY-001",
    "AEO-ENTITY-003",
    "AEO-SEM-002",
    "AEO-ENTITY-002",
    "AEO-SCHEMA-001",
    "AEO-EXTRACT-002",
    "AEO-ORG-003",
)


def insight_summary(checks: list[CheckResult]) -> str:
    by_id = {check.check_id: check for check in checks}
    strengths = [by_id[check_id].message.rstrip(".") for check_id in STRENGTH_IDS if by_id.get(check_id) and by_id[check_id].status == "pass"]
    gaps: list[str] = []
    labels = {
        "AEO-ANSWER-001": "clearer direct answers",
        "AEO-ANSWER-002": "more definition-style statements",
        "AEO-QUESTION-001": "stronger question coverage",
        "AEO-QUESTION-002": "an FAQ or question section",
        "AEO-AUTHOR-001": "clearer authorship",
        "AEO-EXTRACT-003": "improved content extraction structure",
        "AEO-ENTITY-003": "a clearer description of what the site does",
        "AEO-ORG-001": "clearer About information",
        "AEO-SCHEMA-001": "valid structured data",
    }
    for check_id in OPPORTUNITY_IDS:
        check = by_id.get(check_id)
        if check and check.status in {"fail", "warning"}:
            gaps.append(labels[check_id])
        if len(gaps) >= 4:
            break
    lines = ["AI READINESS SUMMARY", ""]
    if strengths:
        lines.append(strengths[0] + ".")
        if len(strengths) > 1:
            lines.append(strengths[1] + ".")
    else:
        lines.append("The page exposes limited identity and structure signals for machine interpretation.")
    if gaps:
        lines.append("")
        lines.append("The main opportunities are:")
        for gap in gaps:
            lines.append(f"• {gap}")
    else:
        lines.append("")
        lines.append("No high-priority extractability gaps were detected on this page.")
    lines.append("")
    lines.append("This does not predict whether an AI system will cite or rank the page.")
    return "\n".join(lines)
