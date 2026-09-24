from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CheckStatus = Literal["pass", "warning", "fail", "not_applicable"]
Severity = Literal["critical", "high", "medium", "low", "info"]
CheckGroup = Literal[
    "structure",
    "depth",
    "readability",
    "headings",
    "paragraphs",
    "duplication",
    "freshness",
    "authorship",
    "completeness",
    "relationships",
    "language",
]
PageTypeName = Literal[
    "homepage",
    "article",
    "blog",
    "product",
    "service",
    "contact",
    "about",
    "login",
    "signup",
    "listing",
    "search",
    "application",
    "unknown",
]


class CheckResult(BaseModel):
    check_id: str
    category: str = "Content"
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
    details: dict[str, Any] = Field(default_factory=dict)


class ContentSummary(BaseModel):
    passed: int
    warnings: int
    failed: int
    not_applicable: int


class ContentIssue(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    severity: Severity
    message: str
    recommendation: str | None = None
    why: str | None = None
    page_url: str
    detected: str | None = None
    affected_element_count: int = 0


class ContentPageInfo(BaseModel):
    analyzed_url: str
    final_url: str
    title: str | None = None
    language: str | None = None


class ContentPageType(BaseModel):
    type: PageTypeName = "unknown"
    confidence: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class ContentMetrics(BaseModel):
    word_count: int = 0
    main_word_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0
    heading_count: int = 0
    section_count: int = 0
    list_count: int = 0
    table_count: int = 0
    average_paragraph_length: float = 0.0
    average_section_length: float = 0.0
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    internal_content_links: int = 0


class ContentReadability(BaseModel):
    language: str | None = None
    supported: bool = False
    flesch_reading_ease: float | None = None
    flesch_kincaid_grade: float | None = None
    label: str | None = None
    reason: str | None = None


class ContentSignals(BaseModel):
    main_content_detected: bool = False
    thin_content: bool = False
    repeated_content: bool = False
    duplicate_content: bool = False
    author_detected: bool = False
    publication_date_detected: bool = False
    cta_detected: bool = False
    boilerplate_ratio: float = 0.0
    repeated_content_ratio: float = 0.0


class ContentCategoryScore(BaseModel):
    id: str
    name: str
    score: int | None
    finding_count: int = 0


class DuplicatePair(BaseModel):
    url: str
    similarity: float
    kind: Literal["exact", "near"]


class ContentResult(BaseModel):
    score: int
    summary: ContentSummary
    narrative: str
    categories: dict[str, int | None]
    category_cards: list[ContentCategoryScore] = Field(default_factory=list)
    checks: list[CheckResult]
    findings: list[CheckResult] = Field(default_factory=list)
    issues: list[ContentIssue]
    page: ContentPageInfo
    page_type: ContentPageType
    metrics: ContentMetrics
    readability: ContentReadability
    signals: ContentSignals
    structure: dict[str, Any] = Field(default_factory=dict)
    duplicates: list[DuplicatePair] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    truncated: bool = False


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
        selector=selector,
        affected_element=selector,
        affected_element_count=affected_element_count,
        details=details or {},
    )
