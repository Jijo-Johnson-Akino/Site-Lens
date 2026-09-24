from __future__ import annotations

from backend.analyzers.performance.checks._util import format_bytes, format_ms, perf_check, rate_ms
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    timing = snapshot.timing or {}
    ttfb = timing.get("ttfb_ms")
    dcl = timing.get("dom_content_loaded_ms")
    load = timing.get("load_event_ms")
    html_bytes = int((snapshot.totals or {}).get("html_bytes") or 0)
    checks: list[CheckResult] = []

    ttfb_status = rate_ms(ttfb, config.ttfb_good_ms, config.ttfb_poor_ms)
    if ttfb_status == "not_applicable":
        checks.append(perf_check(snapshot, check_id="PERF-TTFB-001", name="Time to First Byte", group="server", status="not_applicable", severity="high", message="TTFB could not be measured from Navigation Timing."))
    else:
        checks.append(perf_check(
            snapshot,
            check_id="PERF-TTFB-001",
            name="Time to First Byte",
            group="server",
            status=ttfb_status,  # type: ignore[arg-type]
            severity="high" if ttfb_status == "fail" else "medium",
            message=f"TTFB was {format_ms(ttfb)}. This is server/network response start, not full page load.",
            recommendation="Improve origin response time (application, TTFB, CDN) if this value is consistently high." if ttfb_status != "pass" else None,
            why="Slow TTFB delays every subsequent rendering step.",
            detected=format_ms(ttfb),
            details={"ttfb_ms": ttfb, "good_ms": config.ttfb_good_ms, "poor_ms": config.ttfb_poor_ms},
        ))

    dcl_status = rate_ms(dcl, config.dcl_good_ms, config.dcl_poor_ms)
    if dcl_status == "not_applicable":
        checks.append(perf_check(snapshot, check_id="PERF-LOAD-001", name="DOM Content Loaded", group="loading", status="not_applicable", severity="medium", message="DOM Content Loaded could not be measured."))
    else:
        checks.append(perf_check(
            snapshot,
            check_id="PERF-LOAD-001",
            name="DOM Content Loaded",
            group="loading",
            status=dcl_status,  # type: ignore[arg-type]
            severity="medium",
            message=f"DOM Content Loaded occurred at {format_ms(dcl)}.",
            recommendation="Reduce parser-blocking scripts and large CSS in the document head." if dcl_status != "pass" else None,
            detected=format_ms(dcl),
            details={"dom_content_loaded_ms": dcl},
        ))

    load_status = rate_ms(load, config.load_good_ms, config.load_poor_ms)
    if load_status == "not_applicable":
        checks.append(perf_check(snapshot, check_id="PERF-LOAD-002", name="Load event", group="loading", status="not_applicable", severity="medium", message="Load event timing could not be measured."))
    else:
        checks.append(perf_check(
            snapshot,
            check_id="PERF-LOAD-002",
            name="Load event",
            group="loading",
            status=load_status,  # type: ignore[arg-type]
            severity="low" if load_status == "warning" else "medium",
            message=f"The load event fired at {format_ms(load)}.",
            recommendation="Defer non-critical images, media, and third-party scripts that keep the load event open." if load_status != "pass" else None,
            detected=format_ms(load),
            details={"load_event_ms": load},
        ))

    if html_bytes <= 0:
        checks.append(perf_check(snapshot, check_id="PERF-HTML-001", name="HTML document size", group="loading", status="not_applicable", severity="low", message="HTML transfer size was not available."))
    elif html_bytes >= config.html_high_bytes:
        checks.append(perf_check(snapshot, check_id="PERF-HTML-001", name="HTML document size", group="loading", status="warning", severity="medium", message=f"HTML transfer size is {format_bytes(html_bytes)}.", recommendation="Large HTML is not automatically a failure, but consider reducing inlined assets.", detected=format_bytes(html_bytes)))
    elif html_bytes >= config.html_warn_bytes:
        checks.append(perf_check(snapshot, check_id="PERF-HTML-001", name="HTML document size", group="loading", status="warning", severity="low", message=f"HTML transfer size is {format_bytes(html_bytes)}.", detected=format_bytes(html_bytes)))
    else:
        checks.append(perf_check(snapshot, check_id="PERF-HTML-001", name="HTML document size", group="loading", status="pass", severity="low", message=f"HTML transfer size is {format_bytes(html_bytes)}.", detected=format_bytes(html_bytes)))
    return checks
