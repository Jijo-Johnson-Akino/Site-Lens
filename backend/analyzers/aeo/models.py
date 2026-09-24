from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

CheckStatus = Literal["pass", "warning", "fail", "not_applicable"]
Severity = Literal["critical", "high", "medium", "low", "info"]
CheckGroup = Literal[
    "entity_understanding",
    "answer_readiness",
    "question_coverage",
    "content_structure",
    "semantic_structure",
    "authorship",
    "organization_information",
    "structured_information",
    "extractability",
    "ai_accessibility",
]


class CheckResult(BaseModel):
    check_id: str
    category: str = "AEO"
    group: CheckGroup
    name: str
    status: CheckStatus
    severity: Severity
    score: float | None
    weight: int = 0
    message: str
    recommendation: str | None = None
    why: str | None = None
    detected: str | None = None
    page_url: str
    language_dependent: bool = False


class AeoSummary(BaseModel):
    passed: int
    warnings: int
    failed: int
    not_applicable: int


class AeoIssue(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    severity: Severity
    message: str
    recommendation: str | None = None
    why: str | None = None


class AeoPageInfo(BaseModel):
    analyzed_url: str
    final_url: str
    status_code: int | None = None
    title: str | None = None
    h1: str | None = None
    language: str | None = None


class AeoResult(BaseModel):
    score: int
    summary: AeoSummary
    narrative: str
    insight: str
    categories: dict[str, int | None]
    checks: list[CheckResult]
    issues: list[AeoIssue]
    page: AeoPageInfo


def make_check(
    *,
    check_id: str,
    name: str,
    group: CheckGroup,
    status: CheckStatus,
    severity: Severity,
    message: str,
    page_url: str,
    recommendation: str | None = None,
    why: str | None = None,
    detected: str | None = None,
    language_dependent: bool = False,
) -> CheckResult:
    if status == "pass":
        earned: float | None = 1.0
    elif status == "warning":
        earned = 0.5
    elif status == "fail":
        earned = 0.0
    else:
        earned = None
    return CheckResult(
        check_id=check_id,
        group=group,
        name=name,
        status=status,
        severity=severity,
        score=earned,
        message=message,
        recommendation=recommendation,
        why=why,
        detected=detected,
        page_url=page_url,
        language_dependent=language_dependent,
    )
