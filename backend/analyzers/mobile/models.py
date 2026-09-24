from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CheckStatus = Literal["pass", "warning", "fail", "not_applicable"]
Severity = Literal["critical", "high", "medium", "low", "info"]
CheckGroup = Literal[
    "viewport",
    "layout",
    "overflow",
    "navigation",
    "typography",
    "touch",
    "forms",
    "images",
    "tables",
    "media",
    "sticky",
    "overlays",
    "visibility",
    "cta",
    "spacing",
]


class CheckResult(BaseModel):
    check_id: str
    category: str = "Mobile"
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
    viewport: str
    measured_value: str | float | int | None = None
    expected_value: str | float | int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class MobileSummary(BaseModel):
    passed: int
    warnings: int
    failed: int
    not_applicable: int


class MobileIssue(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    severity: Severity
    message: str
    recommendation: str | None = None
    why: str | None = None
    page_url: str
    selector: str | None = None
    affected_element_count: int = 0
    viewport: str | None = None
    measured_value: str | float | int | None = None
    expected_value: str | float | int | None = None
    detected: str | None = None


class MobileCategoryScore(BaseModel):
    id: str
    name: str
    score: int | None
    finding_count: int = 0
    status: str | None = None


class ScreenshotMeta(BaseModel):
    viewport: str
    width: int
    height: int
    url: str
    created_at: str
    kind: str = "viewport"


class MobilePageInfo(BaseModel):
    analyzed_url: str
    final_url: str


class MobileEnvironment(BaseModel):
    browser: str = "chromium"
    browser_version: str | None = None
    device_profile: str = "mobile"
    viewport: dict[str, int] = Field(default_factory=dict)
    touch_enabled: bool | None = None
    device_scale_factor: float | None = None
    user_agent_category: str = "mobile"
    is_mobile_emulation: bool = True


class MobileResult(BaseModel):
    score: int
    summary: MobileSummary
    narrative: str
    categories: dict[str, int | None]
    category_cards: list[MobileCategoryScore] = Field(default_factory=list)
    checks: list[CheckResult]
    findings: list[CheckResult] = Field(default_factory=list)
    issues: list[MobileIssue]
    page: MobilePageInfo
    environment: MobileEnvironment = Field(default_factory=MobileEnvironment)
    viewport: dict[str, Any] = Field(default_factory=dict)
    navigation: dict[str, Any] = Field(default_factory=dict)
    layout: dict[str, Any] = Field(default_factory=dict)
    typography: dict[str, Any] = Field(default_factory=dict)
    touch_targets: dict[str, Any] = Field(default_factory=dict)
    forms: dict[str, Any] = Field(default_factory=dict)
    images: dict[str, Any] = Field(default_factory=dict)
    tables: dict[str, Any] = Field(default_factory=dict)
    media: dict[str, Any] = Field(default_factory=dict)
    overlays: dict[str, Any] = Field(default_factory=dict)
    sticky_elements: dict[str, Any] = Field(default_factory=dict)
    screenshots: list[ScreenshotMeta] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    comparison: dict[str, Any] | None = None
    overview: dict[str, Any] = Field(default_factory=dict)
    cta: dict[str, Any] = Field(default_factory=dict)


class MobileSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    viewport: dict[str, Any] = Field(default_factory=dict)
    page: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)
    layout: dict[str, Any] = Field(default_factory=dict)
    navigation: dict[str, Any] = Field(default_factory=dict)
    typography: dict[str, Any] = Field(default_factory=dict)
    touch_targets: dict[str, Any] = Field(default_factory=dict)
    forms: list[dict[str, Any]] = Field(default_factory=list)
    images: list[dict[str, Any]] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    media: list[dict[str, Any]] = Field(default_factory=list)
    overlays: list[dict[str, Any]] = Field(default_factory=list)
    sticky_elements: list[dict[str, Any]] = Field(default_factory=list)
    overflowing_elements: list[dict[str, Any]] = Field(default_factory=list)
    min_width_elements: list[dict[str, Any]] = Field(default_factory=list)
    clipped_containers: list[dict[str, Any]] = Field(default_factory=list)
    overflowing_headings: list[dict[str, Any]] = Field(default_factory=list)
    offscreen_critical: list[dict[str, Any]] = Field(default_factory=list)
    clipped_text: list[dict[str, Any]] = Field(default_factory=list)
    small_text: list[dict[str, Any]] = Field(default_factory=list)
    headings: list[dict[str, Any]] = Field(default_factory=list)
    cta: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
    spacing: dict[str, Any] = Field(default_factory=dict)
    scroll: dict[str, Any] = Field(default_factory=dict)
    viewport_meta: dict[str, Any] = Field(default_factory=dict)
    comparison: dict[str, Any] | None = None

    @field_validator(
        "forms",
        "images",
        "tables",
        "media",
        "overlays",
        "sticky_elements",
        "overflowing_elements",
        "min_width_elements",
        "clipped_containers",
        "overflowing_headings",
        "offscreen_critical",
        "clipped_text",
        "small_text",
        "headings",
        mode="before",
    )
    @classmethod
    def _list(cls, value: Any) -> list:
        return value if isinstance(value, list) else []


def make_check(
    *,
    check_id: str,
    name: str,
    group: CheckGroup,
    status: CheckStatus,
    severity: Severity,
    message: str,
    page_url: str,
    viewport: str,
    recommendation: str | None = None,
    why: str | None = None,
    detected: str | None = None,
    selector: str | None = None,
    affected_element: str | None = None,
    affected_element_count: int = 0,
    measured_value: str | float | int | None = None,
    expected_value: str | float | int | None = None,
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
        affected_element=affected_element or selector,
        affected_element_count=affected_element_count,
        viewport=viewport,
        measured_value=measured_value,
        expected_value=expected_value,
        details=details or {},
    )
