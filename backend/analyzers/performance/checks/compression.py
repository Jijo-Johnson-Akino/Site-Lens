from __future__ import annotations

from backend.analyzers.performance.checks._util import format_bytes, perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot

TEXT_TYPES = {"document", "stylesheet", "script", "xhr", "fetch"}
TEXT_CT = ("text/", "javascript", "json", "xml", "svg")
COMPRESSED = ("gzip", "br", "deflate", "zstd")


def _is_text(item: dict) -> bool:
    if item.get("type") in TEXT_TYPES:
        return True
    ctype = str(item.get("content_type") or "").lower()
    return any(token in ctype for token in TEXT_CT)


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    candidates = []
    for item in snapshot.resources:
        if not _is_text(item):
            continue
        size = int(item.get("transfer_bytes") or item.get("encoded_bytes") or 0)
        if size < config.compress_min_bytes:
            continue
        candidates.append(item)
    if not candidates:
        return [perf_check(snapshot, check_id="PERF-COMP-001", name="Text compression", group="compression", status="not_applicable", severity="low", message="No text resources large enough to evaluate compression were recorded. Images and video are not expected to use gzip.")]
    uncompressed = []
    for item in candidates:
        encoding = str(item.get("content_encoding") or "").lower()
        if not any(token in encoding for token in COMPRESSED):
            uncompressed.append(item)
    if uncompressed:
        return [perf_check(
            snapshot,
            check_id="PERF-COMP-001",
            name="Text compression",
            group="compression",
            status="warning",
            severity="medium",
            message=f"{len(uncompressed)} text resource(s) do not advertise gzip/br/deflate/zstd.",
            recommendation="Enable compression for HTML, CSS, JavaScript, and JSON responses.",
            affected_element_count=len(uncompressed),
            resource_url=uncompressed[0].get("url"),
            detected=format_bytes(int(uncompressed[0].get("transfer_bytes") or 0)),
        )]
    return [perf_check(snapshot, check_id="PERF-COMP-001", name="Text compression", group="compression", status="pass", severity="low", message="Text resources advertise a supported content-encoding.")]
