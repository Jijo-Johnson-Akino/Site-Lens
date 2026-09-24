from __future__ import annotations

from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot, make_check


def page_url(snapshot: PerformanceSnapshot) -> str:
    return str(snapshot.page.get("final_url") or snapshot.page.get("url") or "")


def perf_check(snapshot: PerformanceSnapshot, **kwargs) -> CheckResult:
    return make_check(page_url=page_url(snapshot), **kwargs)


def rate_ms(value: float | None, good: float, poor: float) -> str:
    if value is None:
        return "not_applicable"
    if value <= good:
        return "pass"
    if value <= poor:
        return "warning"
    return "fail"


def rate_max(value: float | None, good: float, poor: float) -> str:
    if value is None:
        return "not_applicable"
    if value <= good:
        return "pass"
    if value <= poor:
        return "warning"
    return "fail"


def format_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


def format_ms(value: float | None) -> str:
    if value is None:
        return "unavailable"
    if value >= 1000:
        return f"{value / 1000:.2f}s"
    return f"{value:.0f}ms"


def scoring(snapshot: PerformanceSnapshot) -> PerfScoringConfig:
    return DEFAULT_SCORING
