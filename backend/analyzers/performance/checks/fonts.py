from __future__ import annotations

from backend.analyzers.performance.checks._util import format_bytes, perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    font_bytes = int((snapshot.totals or {}).get("font_bytes") or 0)
    font_reqs = [item for item in snapshot.resources if item.get("type") == "font"]
    domains = sorted({item.get("domain") for item in font_reqs if item.get("domain")})
    if not font_reqs and font_bytes <= 0:
        return [perf_check(snapshot, check_id="PERF-FONT-001", name="Font resources", group="fonts", status="not_applicable", severity="low", message="No font resources were recorded.")]
    if font_bytes >= config.font_high_bytes:
        status, severity = "warning", "medium"
        rec = "Font files can delay text rendering. Consider subsetting and font-display."
    elif font_bytes >= config.font_warn_bytes or len(font_reqs) >= 6:
        status, severity = "warning", "low"
        rec = "Review whether every font file is required."
    else:
        status, severity = "pass", "low"
        rec = None
    return [perf_check(
        snapshot,
        check_id="PERF-FONT-001",
        name="Font resources",
        group="fonts",
        status=status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        message=f"{len(font_reqs)} font request(s), {format_bytes(font_bytes)}.{(' Hosts: ' + ', '.join(str(item) for item in domains[:4])) if domains else ''}",
        recommendation=rec,
        detected=format_bytes(font_bytes),
        affected_element_count=len(font_reqs),
        why="Fonts may delay text rendering; this check does not prove they blocked first paint.",
    )]
