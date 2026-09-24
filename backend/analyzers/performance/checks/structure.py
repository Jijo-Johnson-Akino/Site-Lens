from __future__ import annotations

from backend.analyzers.performance.checks._util import format_ms, perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    nodes = int((snapshot.document or {}).get("node_count") or 0)
    depth = int((snapshot.document or {}).get("depth") or 0)
    tasks = snapshot.long_tasks or []
    long_tasks = [item for item in tasks if float(item.get("duration") or 0) >= config.long_task_ms]
    total = sum(float(item.get("duration") or 0) for item in long_tasks)
    longest = max((float(item.get("duration") or 0) for item in long_tasks), default=0.0)
    checks: list[CheckResult] = []

    if nodes <= 0:
        checks.append(perf_check(snapshot, check_id="PERF-DOM-001", name="DOM size", group="dom", status="not_applicable", severity="low", message="DOM node count was not available."))
    elif nodes > config.dom_high:
        checks.append(perf_check(snapshot, check_id="PERF-DOM-001", name="DOM size", group="dom", status="warning", severity="medium", message=f"The document has {nodes} elements (depth {depth}).", recommendation="A large DOM can increase style and layout cost. This is a signal, not proof the page is unusable.", detected=str(nodes)))
    elif nodes > config.dom_warn:
        checks.append(perf_check(snapshot, check_id="PERF-DOM-001", name="DOM size", group="dom", status="warning", severity="low", message=f"The document has {nodes} elements (depth {depth}).", detected=str(nodes)))
    else:
        checks.append(perf_check(snapshot, check_id="PERF-DOM-001", name="DOM size", group="dom", status="pass", severity="low", message=f"The document has {nodes} elements (depth {depth}).", detected=str(nodes)))

    if not tasks and longest == 0:
        checks.append(perf_check(snapshot, check_id="PERF-LONG-001", name="Long tasks", group="dom", status="not_applicable", severity="low", message="Long-task timing was not available in this browser run."))
    elif total >= config.long_task_total_warn_ms or len(long_tasks) >= 8:
        checks.append(perf_check(snapshot, check_id="PERF-LONG-001", name="Long tasks", group="dom", status="warning", severity="medium", message=f"{len(long_tasks)} long task(s) totaling {format_ms(total)} (longest {format_ms(longest)}).", recommendation="Not every task over 50ms is a problem. Investigate repeated main-thread work if users report jank.", detected=f"count={len(long_tasks)} total_ms={total:.0f}"))
    else:
        checks.append(perf_check(snapshot, check_id="PERF-LONG-001", name="Long tasks", group="dom", status="pass", severity="low", message=f"{len(long_tasks)} long task(s) totaling {format_ms(total)} were observed.", detected=f"count={len(long_tasks)}"))
    return checks
