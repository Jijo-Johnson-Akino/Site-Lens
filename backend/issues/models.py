"""Pydantic models for the unified issues aggregation layer."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AnalyzerRunStatus = Literal["completed", "failed", "missing"]
IssueLifecycle = Literal["open", "resolved", "ignored"]
NormalizedSeverity = Literal["critical", "high", "medium", "low", "info"]
NormalizedPriority = Literal["critical", "high", "medium", "low"]
NormalizedCheckStatus = Literal["pass", "warning", "fail", "not_applicable", "info"]
NormalizedSource = Literal[
    "seo",
    "aeo",
    "uiux",
    "accessibility",
    "performance",
    "content",
    "structured_data",
    "mobile",
    "unknown",
]
ViewportType = Literal["desktop", "mobile"]
ScreenshotCaptureStatus = Literal["pending", "running", "completed", "skipped"]


class AffectedElement(BaseModel):
    selector: str | None = None
    resource_url: str | None = None
    schema_entity_id: str | None = None
    viewport: str | None = None
    snippet: str | None = None
    width: float | int | None = None


class IssueOccurrence(BaseModel):
    occurrence_id: str
    finding_ids: list[str] = Field(default_factory=list)
    page_url: str = ""
    selector: str | None = None
    resource_url: str | None = None
    schema_entity_id: str | None = None
    viewport: str | None = None
    affected_element_count: int = 0
    evidence: dict[str, Any] = Field(default_factory=dict)
    check_status: NormalizedCheckStatus = "fail"
    severity: NormalizedSeverity = "medium"
    message: str = ""
    recommendation: str | None = None
    wcag_reference: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    affected_elements: list[AffectedElement] = Field(default_factory=list)


class UnifiedIssue(BaseModel):
    issue_id: str
    issue_key: str
    source: str
    analyzer: str
    category: str
    subcategory: str | None = None
    check_id: str
    title: str
    description: str
    recommendation: str | None = None
    status: IssueLifecycle = "open"
    check_status: NormalizedCheckStatus = "fail"
    severity: NormalizedSeverity = "medium"
    source_severity: str | None = None
    priority: NormalizedPriority = "medium"
    priority_score: int = 0
    score: float | int | None = None
    page_url: str | None = None
    selector: str | None = None
    resource_url: str | None = None
    schema_entity_id: str | None = None
    viewport: str | None = None
    affected_page_count: int = 0
    affected_element_count: int = 0
    pages: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    wcag_reference: str | None = None
    related_issue_ids: list[str] = Field(default_factory=list)
    occurrences: list[IssueOccurrence] = Field(default_factory=list)
    source_href: str | None = None
    first_seen_scan_id: str | None = None
    last_seen_scan_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    screenshot_url: str | None = None
    screenshot_caption: str | None = None
    highlighted_selector: str | None = None
    viewport_type: ViewportType | None = None
    snippet: str | None = None
    snippet_language: str | None = None
    snippet_highlight_line: int | None = None
    screenshot_unavailable: bool = False
    screenshot_unavailable_reason: str | None = None


class IssueSummary(BaseModel):
    total: int = 0
    occurrences: int = 0
    issue_types: int = 0
    failures: int = 0
    warnings: int = 0
    info: int = 0
    passed: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_source: dict[str, int] = Field(default_factory=dict)
    by_page: dict[str, int] = Field(default_factory=dict)


class ScreenshotCaptureSummary(BaseModel):
    status: ScreenshotCaptureStatus = "pending"
    captured: int = 0
    visual: int = 0
    note: str | None = None


class IssuesPayload(BaseModel):
    version: int = 1
    truncated: bool = False
    analyzer_status: dict[str, AnalyzerRunStatus] = Field(default_factory=dict)
    summary: IssueSummary = Field(default_factory=IssueSummary)
    issues: list[UnifiedIssue] = Field(default_factory=list)
    groups: dict[str, dict[str, list[str]]] = Field(default_factory=dict)
    screenshot_capture: ScreenshotCaptureSummary = Field(default_factory=ScreenshotCaptureSummary)
