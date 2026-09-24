from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CheckStatus = Literal["pass", "warning", "fail", "not_applicable"]
Severity = Literal["critical", "high", "medium", "low", "info"]
CheckGroup = Literal[
    "primary_cta",
    "cta_clarity",
    "value_proposition",
    "forms",
    "conversion_path",
    "navigation",
    "pricing",
    "contact",
    "mobile",
    "interaction",
]


class CheckResult(BaseModel):
    check_id: str
    category: str = "CRO"
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
    page_id: str | None = None
    selector: str | None = None
    affected_element: str | None = None
    affected_element_count: int = 0
    viewport: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)


class CroSummary(BaseModel):
    passed: int = 0
    warnings: int = 0
    failed: int = 0
    not_applicable: int = 0
    pages_analyzed: int = 0
    cta_issues: int = 0
    form_issues: int = 0
    conversion_path_issues: int = 0
    mobile_issues: int = 0
    open_findings: int = 0


class CroIssue(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    severity: Severity
    message: str
    recommendation: str | None = None
    why: str | None = None
    page_url: str
    selector: str | None = None
    detected: str | None = None


class CroCategoryScore(BaseModel):
    id: str
    name: str
    score: int | None
    finding_count: int = 0


class CroPageInfo(BaseModel):
    page_id: str | None = None
    url: str
    page_type: str = "unknown"
    score: int | None = None
    available: bool = True
    cta_status: str | None = None
    forms_status: str | None = None
    conversion_path_status: str | None = None
    issue_count: int = 0


class CroCtaRow(BaseModel):
    text: str
    page_url: str
    page_id: str | None = None
    kind: str
    visibility: str
    destination: str
    status: str
    primary: bool = False
    selector: str | None = None


class CroFormRow(BaseModel):
    page_url: str
    page_id: str | None = None
    purpose: str
    fields: int
    submit_text: str | None = None
    mobile_status: str | None = None
    issue_count: int = 0
    selector: str | None = None


class CroPathNode(BaseModel):
    url: str
    title: str | None = None
    page_type: str | None = None


class CroPath(BaseModel):
    nodes: list[CroPathNode] = Field(default_factory=list)
    message: str | None = None


class CroResult(BaseModel):
    score: int | None
    summary: CroSummary
    narrative: str
    categories: dict[str, int | None] = Field(default_factory=dict)
    category_cards: list[CroCategoryScore] = Field(default_factory=list)
    checks: list[CheckResult] = Field(default_factory=list)
    findings: list[CheckResult] = Field(default_factory=list)
    issues: list[CroIssue] = Field(default_factory=list)
    pages: list[CroPageInfo] = Field(default_factory=list)
    ctas: list[CroCtaRow] = Field(default_factory=list)
    forms: list[CroFormRow] = Field(default_factory=list)
    conversion_paths: list[CroPath] = Field(default_factory=list)
    methodology: str
    limitations: list[str] = Field(default_factory=list)
    screenshots: list[dict[str, Any]] = Field(default_factory=list)
    score_note: str
    crawl_note: str
    viewports: dict[str, dict[str, int]] = Field(default_factory=dict)


def make_check(
    *,
    check_id: str,
    name: str,
    group: CheckGroup,
    status: CheckStatus,
    severity: Severity,
    message: str,
    page_url: str,
    page_id: str | None = None,
    recommendation: str | None = None,
    why: str | None = None,
    detected: str | None = None,
    selector: str | None = None,
    viewport: str | None = None,
    affected_element_count: int = 0,
    evidence: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
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
        page_id=page_id,
        selector=selector,
        affected_element=selector,
        affected_element_count=affected_element_count,
        viewport=viewport,
        evidence=evidence or {},
        details=details or {},
    )
