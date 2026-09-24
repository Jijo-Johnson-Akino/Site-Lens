from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CheckStatus = Literal["pass", "warning", "fail", "not_applicable"]
Severity = Literal["critical", "high", "medium", "low", "info"]
CheckGroup = Literal[
    "identity",
    "contact",
    "transparency",
    "policies",
    "authorship",
    "social_proof",
    "credentials",
    "business",
    "security",
    "consistency",
]


class CheckResult(BaseModel):
    check_id: str
    category: str = "Trust"
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
    evidence: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)


class TrustSummary(BaseModel):
    passed: int = 0
    warnings: int = 0
    failed: int = 0
    not_applicable: int = 0
    pages_analyzed: int = 0
    identity_signals: int = 0
    contact_signals: int = 0
    policy_signals: int = 0
    authorship_signals: int = 0
    social_proof_signals: int = 0
    open_findings: int = 0


class TrustIssue(BaseModel):
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


class TrustCategoryScore(BaseModel):
    id: str
    name: str
    score: int | None
    finding_count: int = 0
    coverage_label: str = "Observable Signal Coverage"


class TrustPageInfo(BaseModel):
    page_id: str | None = None
    url: str
    page_type: str = "unknown"
    score: int | None = None
    available: bool = True
    identity_status: str | None = None
    contact_status: str | None = None
    authorship_status: str | None = None
    issue_count: int = 0


class TrustSignalRow(BaseModel):
    signal: str
    category: str
    page_url: str
    page_id: str | None = None
    evidence: str
    status: str


class TrustPolicyRow(BaseModel):
    policy: str
    detected: bool
    page_url: str | None = None
    note: str


class TrustAuthorRow(BaseModel):
    page_url: str
    page_id: str | None = None
    title: str | None = None
    author: str | None = None
    publication_date: str | None = None
    modified_date: str | None = None
    author_schema: str | None = None
    available: bool = True


class TrustSocialProofRow(BaseModel):
    kind: str
    page_url: str
    evidence: str
    detected: bool
    potential: bool = False


class TrustConsistencyRow(BaseModel):
    field: str
    visible: str | None = None
    schema_value: str | None = None
    footer: str | None = None
    about: str | None = None
    status: str


class TrustSecurityRow(BaseModel):
    signal: str
    detected: bool
    evidence: str


class TrustResult(BaseModel):
    score: int | None
    summary: TrustSummary
    narrative: str
    categories: dict[str, int | None] = Field(default_factory=dict)
    category_cards: list[TrustCategoryScore] = Field(default_factory=list)
    checks: list[CheckResult] = Field(default_factory=list)
    findings: list[CheckResult] = Field(default_factory=list)
    issues: list[TrustIssue] = Field(default_factory=list)
    pages: list[TrustPageInfo] = Field(default_factory=list)
    signals: list[TrustSignalRow] = Field(default_factory=list)
    gaps: list[TrustSignalRow] = Field(default_factory=list)
    policies: list[TrustPolicyRow] = Field(default_factory=list)
    authors: list[TrustAuthorRow] = Field(default_factory=list)
    social_proof: list[TrustSocialProofRow] = Field(default_factory=list)
    consistency: list[TrustConsistencyRow] = Field(default_factory=list)
    security: list[TrustSecurityRow] = Field(default_factory=list)
    methodology: str
    limitations: list[str] = Field(default_factory=list)
    score_note: str
    crawl_note: str


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
        evidence=evidence or {},
        details=details or {},
    )
