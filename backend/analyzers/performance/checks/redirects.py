from __future__ import annotations

from backend.analyzers.performance.checks._util import format_ms, perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    count = snapshot.redirects.get("count")
    duration = snapshot.redirects.get("duration_ms")
    if count is None:
        return [perf_check(snapshot, check_id="PERF-REDIR-001", name="Redirect chain", group="redirects", status="not_applicable", severity="medium", message="Redirect count was not available from Navigation Timing.")]
    if count >= config.redirect_fail:
        status, severity = "fail", "high"
        message = f"{count} redirects were recorded before the final document."
        rec = "Avoid extra hops. A single HTTP→HTTPS or canonical redirect is usually enough."
    elif count >= config.redirect_warn:
        status, severity = "warning", "medium"
        message = f"{count} redirects were recorded."
        rec = "Review whether every hop is necessary."
    elif count == 1:
        status, severity = "pass", "low"
        message = "One redirect was recorded. A single HTTPS or canonical redirect is not treated as a failure."
        rec = None
    else:
        status, severity = "pass", "low"
        message = "No redirects were recorded for this navigation."
        rec = None
    return [perf_check(
        snapshot,
        check_id="PERF-REDIR-001",
        name="Redirect chain",
        group="redirects",
        status=status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        message=message,
        recommendation=rec,
        detected=f"count={count} duration={format_ms(duration) if duration is not None else 'n/a'}",
        details={"redirect_count": count, "redirect_ms": duration},
    )]
