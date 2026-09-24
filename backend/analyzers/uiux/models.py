from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CheckStatus = Literal["pass", "warning", "fail", "not_applicable"]
Severity = Literal["critical", "high", "medium", "low", "info"]
CheckGroup = Literal[
    "responsive",
    "layout",
    "navigation",
    "interactive",
    "typography",
    "content",
    "forms",
    "images",
]


class CheckResult(BaseModel):
    check_id: str
    category: str = "UI_UX"
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
    viewport: str
    page_url: str
    affected_element: str | None = None


class UiuxSummary(BaseModel):
    passed: int
    warnings: int
    failed: int
    not_applicable: int


class UiuxIssue(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    severity: Severity
    message: str
    recommendation: str | None = None
    why: str | None = None
    viewport: str
    page_url: str
    affected_element: str | None = None
    detected: str | None = None


class ScreenshotMeta(BaseModel):
    viewport: str
    width: int
    height: int
    url: str
    created_at: str


class ViewportResult(BaseModel):
    score: int
    width: int
    height: int
    summary: UiuxSummary
    layout: dict[str, Any] = Field(default_factory=dict)
    navigation: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
    interactive: dict[str, Any] = Field(default_factory=dict)
    cta: dict[str, Any] = Field(default_factory=dict)
    forms: list[dict[str, Any]] = Field(default_factory=list)
    overlays: list[dict[str, Any]] = Field(default_factory=list)
    buttons: list[dict[str, Any]] = Field(default_factory=list)
    links: list[dict[str, Any]] = Field(default_factory=list)
    headings: list[dict[str, Any]] = Field(default_factory=list)


class UiuxPageInfo(BaseModel):
    analyzed_url: str
    final_url: str


class UiuxResult(BaseModel):
    score: int
    summary: UiuxSummary
    narrative: str
    categories: dict[str, int | None]
    viewports: dict[str, ViewportResult]
    screenshots: list[ScreenshotMeta] = Field(default_factory=list)
    checks: list[CheckResult]
    issues: list[UiuxIssue]
    page: UiuxPageInfo


class ViewportSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    viewport: dict[str, Any]
    page: dict[str, Any]
    layout: dict[str, Any] = Field(default_factory=dict)
    navigation: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
    interactive: dict[str, Any] = Field(default_factory=dict)
    typography: dict[str, Any] = Field(default_factory=dict)
    images: list[dict[str, Any]] = Field(default_factory=list)
    forms: list[dict[str, Any]] = Field(default_factory=list)
    overlays: list[dict[str, Any]] = Field(default_factory=list)
    overflowing_elements: list[dict[str, Any]] = Field(default_factory=list)
    fixed_width_elements: list[dict[str, Any]] = Field(default_factory=list)
    overlapping_pairs: list[dict[str, Any]] = Field(default_factory=list)
    clipped_text: list[dict[str, Any]] = Field(default_factory=list)
    small_text: list[dict[str, Any]] = Field(default_factory=list)
    empty_sections: list[dict[str, Any]] = Field(default_factory=list)
    offscreen_critical: list[dict[str, Any]] = Field(default_factory=list)
    cta: dict[str, Any] = Field(default_factory=dict)
    main: dict[str, Any] = Field(default_factory=dict)
    load: dict[str, Any] = Field(default_factory=dict)
    buttons: list[dict[str, Any]] = Field(default_factory=list)
    links: list[dict[str, Any]] = Field(default_factory=list)
    headings: list[dict[str, Any]] = Field(default_factory=list)
    disabled_primary: list[dict[str, Any]] = Field(default_factory=list)


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
    affected_element: str | None = None,
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
        viewport=viewport,
        page_url=page_url,
        affected_element=affected_element,
    )
