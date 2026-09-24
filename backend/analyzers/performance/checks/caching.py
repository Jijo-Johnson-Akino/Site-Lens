from __future__ import annotations

from backend.analyzers.performance.checks._util import perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot

STATIC_TYPES = {"stylesheet", "script", "image", "font", "media"}


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    static = [item for item in snapshot.resources if item.get("type") in STATIC_TYPES]
    if not static:
        return [perf_check(snapshot, check_id="PERF-CACHE-001", name="Static asset caching", group="caching", status="not_applicable", severity="low", message="No static assets were recorded. HTML/personalized responses are not required to be cached.")]
    missing = []
    for item in static:
        cache = str(item.get("cache_control") or "").lower()
        if "no-store" in cache or "private" in cache:
            continue
        has_directive = bool(cache) or item.get("etag") or item.get("last_modified") or bool(item.get("expires"))
        if not has_directive:
            missing.append(item)
    if missing:
        return [perf_check(
            snapshot,
            check_id="PERF-CACHE-001",
            name="Static asset caching",
            group="caching",
            status="warning",
            severity="low",
            message=f"{len(missing)} static resource(s) have no Cache-Control, ETag, Last-Modified, or Expires header.",
            recommendation="Static resources may benefit from explicit browser caching. Ambiguous headers are not treated as proof that caching is absent.",
            affected_element_count=len(missing),
            resource_url=missing[0].get("url"),
        )]
    return [perf_check(snapshot, check_id="PERF-CACHE-001", name="Static asset caching", group="caching", status="pass", severity="low", message="Static resources expose cache-related headers. HTML pages are not required to be cached.")]
