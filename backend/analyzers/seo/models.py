from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

CheckStatus = Literal["pass", "warning", "fail", "not_applicable"]
Severity = Literal["critical", "high", "medium", "low", "info"]
CheckGroup = Literal[
    "metadata",
    "indexability",
    "headings",
    "canonical",
    "images",
    "links",
    "technical",
    "social",
    "robots_sitemap",
]


class CheckResult(BaseModel):
    check_id: str
    category: str = "SEO"
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


class Indexability(BaseModel):
    indexable: bool
    reason: str | None = None


class SeoSummary(BaseModel):
    passed: int
    warnings: int
    failed: int
    not_applicable: int


class SeoPageInfo(BaseModel):
    analyzed_url: str
    final_url: str
    status_code: int | None = None
    title: str | None = None
    h1: str | None = None


class SeoIssue(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    severity: Severity
    message: str
    recommendation: str | None = None


class SeoResult(BaseModel):
    score: int
    summary: SeoSummary
    narrative: str
    categories: dict[str, int | None]
    checks: list[CheckResult]
    issues: list[SeoIssue]
    page: SeoPageInfo
    indexable: Indexability


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
    )
