from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CheckStatus = Literal["pass", "warning", "fail", "not_applicable"]
Severity = Literal["critical", "high", "medium", "low", "info"]
CheckGroup = Literal[
    "document",
    "landmarks",
    "headings",
    "images",
    "links",
    "controls",
    "forms",
    "aria",
    "keyboard",
    "tables",
    "media",
    "contrast",
    "other",
]
FindingSource = Literal["axe", "sitebench", "manual-review"]


class CheckResult(BaseModel):
    check_id: str
    category: str = "Accessibility"
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
    selector: str | None = None
    affected_element: str | None = None
    affected_element_count: int = 0
    wcag_reference: str | None = None
    source: FindingSource = "sitebench"
    details: dict[str, Any] = Field(default_factory=dict)
    help_url: str | None = None
    axe_rule_id: str | None = None
    manual_review: bool = False


class A11ySummary(BaseModel):
    passed: int
    warnings: int
    failed: int
    not_applicable: int
    manual_review: int = 0


class A11yIssue(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    severity: Severity
    message: str
    recommendation: str | None = None
    why: str | None = None
    viewport: str | None = None
    page_url: str
    selector: str | None = None
    affected_element: str | None = None
    affected_element_count: int = 0
    wcag_reference: str | None = None
    source: FindingSource = "sitebench"
    detected: str | None = None
    manual_review: bool = False


class A11yTool(BaseModel):
    name: str = "axe-core"
    version: str | None = None
    automated: bool = True
    tags: list[str] = Field(default_factory=list)
    standard: str = "WCAG-oriented automated checks"
    automated_only: bool = True
    axe_violations: int = 0
    axe_incomplete: int = 0
    axe_passes: int = 0
    axe_inapplicable: int = 0


class A11yStandard(BaseModel):
    name: str = "WCAG-oriented automated audit"
    version: str = "2.2"
    automated_only: bool = True


class A11yPageInfo(BaseModel):
    analyzed_url: str
    final_url: str


class A11yCategoryScore(BaseModel):
    id: str
    name: str
    score: int | None
    finding_count: int = 0


class A11yResult(BaseModel):
    score: int
    summary: A11ySummary
    narrative: str
    categories: dict[str, int | None]
    category_cards: list[A11yCategoryScore] = Field(default_factory=list)
    checks: list[CheckResult]
    findings: list[CheckResult] = Field(default_factory=list)
    issues: list[A11yIssue]
    page: A11yPageInfo
    tool: A11yTool
    standard: A11yStandard
    limitations: list[str] = Field(default_factory=list)
    screenshots: list[dict[str, Any]] = Field(default_factory=list)
    severity_counts: dict[str, int] = Field(default_factory=dict)


class AccessibleSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page: dict[str, Any] = Field(default_factory=dict)
    document: dict[str, Any] = Field(default_factory=dict)
    landmarks: dict[str, Any] = Field(default_factory=dict)
    headings: list[dict[str, Any]] = Field(default_factory=list)
    images: list[dict[str, Any]] = Field(default_factory=list)
    image_inputs: list[dict[str, Any]] = Field(default_factory=list)
    links: list[dict[str, Any]] = Field(default_factory=list)
    controls: list[dict[str, Any]] = Field(default_factory=list)
    fields: list[dict[str, Any]] = Field(default_factory=list)
    forms: list[dict[str, Any]] = Field(default_factory=list)
    radio_groups: int = 0
    radio_groups_without_fieldset: int = 0
    aria: dict[str, Any] = Field(default_factory=dict)
    ids: dict[str, Any] = Field(default_factory=dict)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    iframes: list[dict[str, Any]] = Field(default_factory=list)
    dialogs: list[dict[str, Any]] = Field(default_factory=list)
    media: list[dict[str, Any]] = Field(default_factory=list)
    focus: dict[str, Any] = Field(default_factory=dict)
    viewport_meta: dict[str, Any] = Field(default_factory=dict)
    skip: dict[str, Any] = Field(default_factory=dict)
    live: list[dict[str, Any]] = Field(default_factory=list)


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
    selector: str | None = None,
    affected_element_count: int = 0,
    wcag_reference: str | None = None,
    source: FindingSource = "sitebench",
    details: dict[str, Any] | None = None,
    help_url: str | None = None,
    axe_rule_id: str | None = None,
    manual_review: bool = False,
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
        selector=selector,
        affected_element=selector,
        affected_element_count=affected_element_count,
        wcag_reference=wcag_reference,
        source=source,
        details=details or {},
        help_url=help_url,
        axe_rule_id=axe_rule_id,
        manual_review=manual_review,
    )
