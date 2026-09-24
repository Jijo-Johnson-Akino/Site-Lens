from __future__ import annotations

from backend.analyzers.performance.checks._util import format_bytes, perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    js_bytes = int((snapshot.totals or {}).get("js_bytes") or 0)
    scripts = snapshot.scripts or []
    blocking = [item for item in scripts if item.get("src") and item.get("in_head") and not item.get("async") and not item.get("defer")]
    checks: list[CheckResult] = []

    if blocking:
        checks.append(perf_check(
            snapshot,
            check_id="PERF-JS-001",
            name="Parser-blocking JavaScript",
            group="javascript",
            status="warning" if len(blocking) < 3 else "fail",
            severity="medium" if len(blocking) < 3 else "high",
            message=f"{len(blocking)} synchronous script(s) in the document head may delay HTML parsing.",
            recommendation="Consider async/defer or moving non-critical scripts. Not every head script is harmful.",
            why="Synchronous scripts in the head block HTML parsing until they download and execute.",
            affected_element_count=len(blocking),
            resource_url=blocking[0].get("src"),
            selector="script",
        ))
    elif scripts:
        checks.append(perf_check(snapshot, check_id="PERF-JS-001", name="Parser-blocking JavaScript", group="javascript", status="pass", severity="medium", message="No synchronous head scripts without async/defer were detected."))
    else:
        checks.append(perf_check(snapshot, check_id="PERF-JS-001", name="Parser-blocking JavaScript", group="javascript", status="not_applicable", severity="low", message="No script elements were present."))

    if js_bytes >= config.js_high_bytes:
        checks.append(perf_check(snapshot, check_id="PERF-JS-002", name="JavaScript payload", group="javascript", status="warning", severity="high", message=f"JavaScript transfer is {format_bytes(js_bytes)}.", recommendation="Split bundles, remove unused code, and defer non-critical scripts. Size alone is not a failure.", detected=format_bytes(js_bytes)))
    elif js_bytes >= config.js_warn_bytes:
        checks.append(perf_check(snapshot, check_id="PERF-JS-002", name="JavaScript payload", group="javascript", status="warning", severity="medium", message=f"JavaScript transfer is {format_bytes(js_bytes)}.", detected=format_bytes(js_bytes)))
    else:
        checks.append(perf_check(snapshot, check_id="PERF-JS-002", name="JavaScript payload", group="javascript", status="pass", severity="medium", message=f"JavaScript transfer is {format_bytes(js_bytes)}.", detected=format_bytes(js_bytes)))
    return checks
