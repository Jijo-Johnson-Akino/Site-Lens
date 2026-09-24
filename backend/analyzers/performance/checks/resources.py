from __future__ import annotations

from backend.analyzers.performance.checks._util import format_bytes, perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    requests = int((snapshot.totals or {}).get("total_requests") or len(snapshot.resources))
    transfer = int((snapshot.totals or {}).get("transfer_bytes") or 0)
    if requests <= 0:
        return [perf_check(snapshot, check_id="PERF-NET-001", name="Network requests", group="network", status="not_applicable", severity="low", message="No resource timing entries were recorded.")]
    if requests >= config.req_high:
        status, severity = "warning", "medium"
        rec = "A high request count can add connection and parsing overhead. This lab total is not a crawl of the whole site."
    elif requests >= config.req_warn:
        status, severity = "warning", "low"
        rec = "Consider combining or deferring non-critical requests."
    else:
        status, severity = "pass", "low"
        rec = None
    return [perf_check(
        snapshot,
        check_id="PERF-NET-001",
        name="Network requests",
        group="network",
        status=status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        message=f"{requests} request(s) transferred {format_bytes(transfer)} in this run.",
        recommendation=rec,
        detected=f"{requests} requests",
        affected_element_count=requests,
        details={"transfer_bytes": transfer},
    )]
