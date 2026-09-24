from __future__ import annotations

from backend.analyzers.performance.checks._util import format_bytes, perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    totals = snapshot.totals or {}
    third_bytes = int(totals.get("third_party_bytes") or 0)
    third_req = int(totals.get("third_party_requests") or 0)
    transfer = int(totals.get("transfer_bytes") or 0)
    ratio = (third_bytes / transfer) if transfer else 0.0
    domains = snapshot.third_party_domains or []
    names = ", ".join(str(item.get("domain")) for item in domains[:4] if item.get("domain"))
    if third_req == 0:
        return [perf_check(snapshot, check_id="PERF-TP-001", name="Third-party resources", group="third_party", status="pass", severity="medium", message="No third-party resources were classified. Third-party means a different registrable domain, not malicious.")]
    if ratio >= config.tp_ratio_warn or third_req >= config.tp_req_warn:
        return [perf_check(
            snapshot,
            check_id="PERF-TP-001",
            name="Third-party resources",
            group="third_party",
            status="warning",
            severity="medium",
            message=f"{third_req} third-party request(s) account for {format_bytes(third_bytes)} ({ratio:.0%}).",
            recommendation="Audit tags and embeds. Third-party only means externally hosted.",
            detected=names or format_bytes(third_bytes),
            affected_element_count=third_req,
            details={"domains": domains[:8], "ratio": round(ratio, 3)},
        )]
    return [perf_check(
        snapshot,
        check_id="PERF-TP-001",
        name="Third-party resources",
        group="third_party",
        status="pass",
        severity="low",
        message=f"{third_req} third-party request(s), {format_bytes(third_bytes)}.",
        detected=names or None,
        details={"domains": domains[:8]},
    )]
