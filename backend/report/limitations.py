"""Collect scan-specific limitations from persisted results. Do not invent rows."""

from __future__ import annotations

from typing import Any

from backend.pages.models import PagesPayload
from backend.scoring.models import HealthResult
from backend.scoring.weights import ERROR_KEYS, PAYLOAD_KEYS


def collect_limitations(
    result: dict[str, Any],
    *,
    health: HealthResult | None,
    pages: PagesPayload,
    issues_truncated: bool = False,
    recommendations_error: bool = False,
    competitors_included: bool = False,
    architecture_available: bool = False,
    links_recorded: bool = False,
) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()

    def add(text: str | None) -> None:
        value = (text or "").strip()
        if not value or value in seen:
            return
        seen.add(value)
        items.append(value)

    summary = pages.summary
    if summary.page_limit_reached:
        add("The crawl reached the configured page limit. Additional pages may exist beyond this scan.")
    if summary.depth_limit_reached:
        add("Pages beyond the configured crawl depth were not analyzed.")
    if summary.failed:
        add(f"{summary.failed} page{'s' if summary.failed != 1 else ''} failed to crawl.")
    if summary.skipped:
        add(f"{summary.skipped} page{'s' if summary.skipped != 1 else ''} {'were' if summary.skipped != 1 else 'was'} skipped.")
    if not architecture_available:
        add("Architecture data is unavailable for this scan.")
    elif not links_recorded:
        add("Internal-link relationships were not recorded for this scan.")

    if health is None:
        add("Overall health score was not available from stored results.")
    else:
        if health.partial_notice:
            add(health.partial_notice)
        if health.coverage.status in {"partial", "limited", "unavailable"}:
            add(health.coverage.explanation)

    for category, error_key in ERROR_KEYS.items():
        error = result.get(error_key)
        payload = result.get(PAYLOAD_KEYS[category])
        if payload:
            continue
        if isinstance(error, dict):
            add(str(error.get("message") or f"{category} analysis was unavailable."))
        elif error:
            add(str(error))

    if issues_truncated:
        add("The stored issue list was truncated for this scan.")
    if recommendations_error:
        add("Recommendations could not be generated from the stored findings.")
    if not competitors_included:
        add("Competitor benchmarking was not included in this scan.")

    robots = result.get("robots") if isinstance(result.get("robots"), dict) else None
    if isinstance(robots, dict) and robots.get("restricted"):
        add("Robots restrictions limited which resources were retrieved.")

    perf = result.get("performance")
    if isinstance(perf, dict):
        vitals = perf.get("vitals") if isinstance(perf.get("vitals"), dict) else {}
        for metric in ("lcp", "cls", "inp"):
            row = vitals.get(metric) if isinstance(vitals, dict) else None
            if isinstance(row, dict) and row.get("value") is None:
                add(f"{metric.upper()} was unavailable for this measurement.")
        timing = perf.get("timing") if isinstance(perf.get("timing"), dict) else {}
        if isinstance(timing, dict) and timing.get("ttfb_ms") is None:
            add("TTFB was unavailable for this measurement.")

    return items
