from __future__ import annotations

from backend.analyzers.performance.checks._util import perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    blocking_css = [item for item in snapshot.stylesheets if item.get("in_head") and "print" not in str(item.get("media") or "").lower()]
    blocking_js = [item for item in snapshot.scripts if item.get("src") and item.get("in_head") and not item.get("async") and not item.get("defer")]
    count = len(blocking_css) + len(blocking_js)
    if count == 0:
        return [perf_check(snapshot, check_id="PERF-BLOCK-001", name="Render-blocking resources", group="blocking", status="pass", severity="medium", message="No obvious render-blocking head CSS or synchronous scripts were detected.")]
    first = (blocking_js or blocking_css)[0]
    return [perf_check(
        snapshot,
        check_id="PERF-BLOCK-001",
        name="Render-blocking resources",
        group="blocking",
        status="warning" if count < 4 else "fail",
        severity="medium" if count < 4 else "high",
        message=f"{len(blocking_css)} head stylesheet(s) and {len(blocking_js)} synchronous head script(s) may delay rendering.",
        recommendation="This does not measure exact rendering delay. Consider media=print on non-critical CSS and async/defer on non-critical JS.",
        why="Head CSS and synchronous scripts commonly block first paint.",
        affected_element_count=count,
        resource_url=first.get("src") or first.get("href"),
    )]
