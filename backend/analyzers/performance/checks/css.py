from __future__ import annotations

from backend.analyzers.performance.checks._util import format_bytes, perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    css_bytes = int((snapshot.totals or {}).get("css_bytes") or 0)
    sheets = snapshot.stylesheets or []
    blocking = [item for item in sheets if item.get("in_head") and "print" not in str(item.get("media") or "").lower()]
    if css_bytes >= config.css_high_bytes:
        status, severity = "warning", "high"
        message = f"CSS transfer is {format_bytes(css_bytes)}."
        rec = "Large CSS can delay first paint. Unused-CSS percentage is not estimated."
    elif css_bytes >= config.css_warn_bytes:
        status, severity = "warning", "medium"
        message = f"CSS transfer is {format_bytes(css_bytes)}."
        rec = "Consider splitting or deferring non-critical CSS."
    else:
        status, severity = "pass", "low"
        message = f"CSS transfer is {format_bytes(css_bytes)}."
        rec = None
    extra = f" {len(blocking)} stylesheet(s) in the head may be render-blocking." if blocking else ""
    return [perf_check(
        snapshot,
        check_id="PERF-CSS-001",
        name="CSS payload",
        group="css",
        status=status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        message=message + extra,
        recommendation=rec,
        detected=format_bytes(css_bytes),
        affected_element_count=len(blocking),
        resource_url=(blocking[0].get("href") if blocking else None),
    )]
