from __future__ import annotations

from backend.analyzers.performance.checks._util import format_ms, perf_check, rate_ms
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    lcp = snapshot.vitals.get("lcp") if isinstance(snapshot.vitals, dict) else None
    lcp_ms = lcp.get("value") if isinstance(lcp, dict) else None
    if lcp_ms == 0:
        lcp_ms = None
    cls = snapshot.vitals.get("cls")
    checks: list[CheckResult] = []

    lcp_status = rate_ms(lcp_ms, config.lcp_good_ms, config.lcp_poor_ms)
    if lcp_status == "not_applicable":
        checks.append(perf_check(snapshot, check_id="PERF-VITAL-001", name="Largest Contentful Paint", group="vitals", status="not_applicable", severity="high", message="LCP could not be reliably measured in this automated run.", why="LCP is a Core Web Vital for perceived load speed."))
    else:
        severity = "high" if lcp_status == "fail" else "medium"
        checks.append(perf_check(
            snapshot,
            check_id="PERF-VITAL-001",
            name="Largest Contentful Paint",
            group="vitals",
            status=lcp_status,  # type: ignore[arg-type]
            severity=severity,  # type: ignore[arg-type]
            message=f"LCP was {format_ms(lcp_ms)} in this Chromium run.",
            recommendation="Improve server response, reduce render-blocking resources, and keep the LCP image discoverable without lazy-loading it." if lcp_status != "pass" else None,
            why="LCP estimates when the main content became visible. This is one automated lab measurement, not field data.",
            detected=format_ms(lcp_ms),
            resource_url=(lcp or {}).get("url") if isinstance(lcp, dict) else None,
            details={"lcp_ms": lcp_ms, "good_ms": config.lcp_good_ms, "poor_ms": config.lcp_poor_ms},
        ))

    if cls is None:
        checks.append(perf_check(snapshot, check_id="PERF-VITAL-002", name="Cumulative Layout Shift", group="vitals", status="not_applicable", severity="medium", message="CLS could not be reliably measured in this automated run."))
    else:
        cls_status = "pass" if cls <= config.cls_good else "warning" if cls <= config.cls_poor else "fail"
        sources = snapshot.vitals.get("cls_sources") if isinstance(snapshot.vitals, dict) else []
        first_source = sources[0] if isinstance(sources, list) and sources else {}
        checks.append(perf_check(
            snapshot,
            check_id="PERF-VITAL-002",
            name="Cumulative Layout Shift",
            group="vitals",
            status=cls_status,  # type: ignore[arg-type]
            severity="high" if cls_status == "fail" else "medium",
            message=f"CLS was {cls:.3f} during this automated run.",
            recommendation="Reserve space for images and embeds, and avoid inserting content above existing content." if cls_status != "pass" else None,
            why="Layout shifts make pages feel unstable. Lab CLS can differ from real-user CLS.",
            detected=f"{cls:.3f}",
            details={"cls": cls, "cls_sources": sources or []},
            selector=first_source.get("selector") if isinstance(first_source, dict) else None,
        ))

    checks.append(perf_check(
        snapshot,
        check_id="PERF-VITAL-003",
        name="Interaction to Next Paint",
        group="vitals",
        status="not_applicable",
        severity="medium",
        message="INP was not measured. No representative interaction was available during the automated run.",
        why="INP requires real user input. SiteLens does not click purchase, form, or other state-changing controls.",
        detected="unavailable",
    ))
    return checks
