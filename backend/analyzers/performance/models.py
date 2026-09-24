from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CheckStatus = Literal["pass", "warning", "fail", "not_applicable"]
Severity = Literal["critical", "high", "medium", "low", "info"]
CheckGroup = Literal[
    "vitals",
    "loading",
    "server",
    "javascript",
    "css",
    "images",
    "fonts",
    "third_party",
    "caching",
    "compression",
    "blocking",
    "dom",
    "network",
    "redirects",
]


class CheckResult(BaseModel):
    check_id: str
    category: str = "Performance"
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
    resource_url: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class PerfSummary(BaseModel):
    passed: int
    warnings: int
    failed: int
    not_applicable: int


class PerfIssue(BaseModel):
    check_id: str
    name: str
    status: CheckStatus
    severity: Severity
    message: str
    recommendation: str | None = None
    why: str | None = None
    page_url: str
    detected: str | None = None
    resource_url: str | None = None
    affected_element_count: int = 0


class PerfEnvironment(BaseModel):
    browser: str = "chromium"
    browser_version: str | None = None
    viewport: dict[str, int] = Field(default_factory=dict)
    viewport_name: str = "desktop"
    network_profile: str = "default"
    cpu_throttling: bool = False
    cache_enabled: bool = False
    cache_mode: str = "cold"


class PerfTiming(BaseModel):
    navigation_start_ms: float | None = None
    fetch_start_ms: float | None = None
    dns_ms: float | None = None
    connection_ms: float | None = None
    tls_ms: float | None = None
    ttfb_ms: float | None = None
    response_end_ms: float | None = None
    dom_interactive_ms: float | None = None
    dom_content_loaded_ms: float | None = None
    load_event_ms: float | None = None
    redirect_ms: float | None = None
    redirect_count: int | None = None


class PerfVitalMetric(BaseModel):
    value: float | None = None
    status: Literal["good", "needs_improvement", "poor", "unavailable"] = "unavailable"
    unit: str | None = None
    reason: str | None = None


class PerfVitals(BaseModel):
    lcp: PerfVitalMetric = Field(default_factory=PerfVitalMetric)
    cls: PerfVitalMetric = Field(default_factory=PerfVitalMetric)
    inp: PerfVitalMetric = Field(default_factory=lambda: PerfVitalMetric(reason="No representative interaction was available during the automated run."))


class PerfResources(BaseModel):
    total_requests: int = 0
    transfer_bytes: int = 0
    resource_bytes: int = 0
    html_bytes: int = 0
    css_bytes: int = 0
    js_bytes: int = 0
    image_bytes: int = 0
    font_bytes: int = 0
    media_bytes: int = 0
    other_bytes: int = 0
    third_party_bytes: int = 0
    third_party_requests: int = 0
    percentages: dict[str, float] = Field(default_factory=dict)


class PerfPageInfo(BaseModel):
    analyzed_url: str
    final_url: str


class PerfCategoryScore(BaseModel):
    id: str
    name: str
    score: int | None
    finding_count: int = 0


class ResourceRecord(BaseModel):
    url: str
    domain: str | None = None
    type: str = "other"
    initiator: str | None = None
    transfer_bytes: int | None = None
    encoded_bytes: int | None = None
    decoded_bytes: int | None = None
    duration_ms: float | None = None
    status: int | None = None
    content_type: str | None = None
    first_party: bool = True
    cache_control: str | None = None
    content_encoding: str | None = None
    etag: bool = False
    last_modified: bool = False
    expires: str | None = None


class PerformanceSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)
    timing: dict[str, Any] = Field(default_factory=dict)
    vitals: dict[str, Any] = Field(default_factory=dict)
    resources: list[dict[str, Any]] = Field(default_factory=list)
    totals: dict[str, Any] = Field(default_factory=dict)
    document: dict[str, Any] = Field(default_factory=dict)
    scripts: list[dict[str, Any]] = Field(default_factory=list)
    stylesheets: list[dict[str, Any]] = Field(default_factory=list)
    images: list[dict[str, Any]] = Field(default_factory=list)
    hints: list[dict[str, Any]] = Field(default_factory=list)
    long_tasks: list[dict[str, Any]] = Field(default_factory=list)
    redirects: dict[str, Any] = Field(default_factory=dict)
    third_party_domains: list[dict[str, Any]] = Field(default_factory=list)


class PerfResult(BaseModel):
    score: int
    summary: PerfSummary
    narrative: str
    categories: dict[str, int | None]
    category_cards: list[PerfCategoryScore] = Field(default_factory=list)
    checks: list[CheckResult]
    findings: list[CheckResult] = Field(default_factory=list)
    issues: list[PerfIssue]
    page: PerfPageInfo
    environment: PerfEnvironment
    timing: PerfTiming
    vitals: PerfVitals
    resources: PerfResources
    resource_table: list[ResourceRecord] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    severity_counts: dict[str, int] = Field(default_factory=dict)


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
    resource_url: str | None = None,
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
        affected_element=selector or resource_url,
        affected_element_count=affected_element_count,
        resource_url=resource_url,
        details=details or {},
    )
