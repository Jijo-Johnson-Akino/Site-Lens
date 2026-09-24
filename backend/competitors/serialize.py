"""API shapes for competitor lists, detail, and page comparison."""

from __future__ import annotations

from typing import Any

from backend.competitors.config import MAX_COMPETITORS, limit_note
from backend.competitors.matching import suggest_matches
from backend.competitors.models import CompetitorBenchmark
from backend.competitors.snapshot import snapshot_from_record
from backend.pages.engine import payload_from_result as pages_from_result
from backend.pages.models import PageRecord
from backend.schemas.scan import ScanRecord


def competitor_to_card(item: CompetitorBenchmark, scan: ScanRecord | None) -> dict[str, Any]:
    pages = pages_from_result(scan.result if scan else None)
    issues = (scan.result or {}).get("issues") if scan and isinstance(scan.result, dict) else None
    issue_total = None
    if isinstance(issues, dict) and isinstance(issues.get("summary"), dict):
        issue_total = issues["summary"].get("total")
    status = item.status
    if scan is not None:
        if scan.status == "running":
            status = "scanning"
        elif scan.status in {"queued", "completed", "failed", "cancelled"}:
            status = scan.status
    error = None
    if scan is not None and scan.status == "failed":
        raw = scan.error if isinstance(scan.error, dict) else {}
        error = {
            "code": raw.get("code") or "COMPETITOR_FAILED",
            "message": raw.get("message") or "Unable to retrieve the website.",
        }
    return {
        "id": item.id,
        "scan_id": item.scan_id,
        "name": item.name,
        "url": item.url,
        "normalized_url": item.normalized_url,
        "competitor_scan_id": item.competitor_scan_id,
        "status": status,
        "progress": scan.progress if scan is not None and status in {"queued", "scanning"} else None,
        "current_step": scan.current_step if scan is not None and status == "scanning" else None,
        "pages_crawled": pages.summary.crawled if scan is not None and scan.status == "completed" else None,
        "pages_discovered": pages.summary.discovered if scan is not None and scan.status == "completed" else None,
        "issue_count": issue_total if scan is not None and scan.status == "completed" else None,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "completed_at": scan.completed_at.isoformat() if scan and scan.completed_at else None,
        "error": error,
    }


def competitor_detail(item: CompetitorBenchmark, primary: ScanRecord, scan: ScanRecord | None) -> dict[str, Any]:
    card = competitor_to_card(item, scan)
    snapshot = snapshot_from_record(scan, column_id=item.id, label=item.name, role="competitor") if scan else None
    return {
        "competitor": card,
        "primary_scan_id": primary.id,
        "snapshot": snapshot,
        "max_competitors": MAX_COMPETITORS,
        "limit_note": limit_note(),
    }


def _page_lookup(pages: list[PageRecord], page_id: str) -> PageRecord | None:
    return next((page for page in pages if page.id == page_id), None)


def _page_metrics(page: PageRecord) -> dict[str, Any]:
    scores = page.analyzer_scores or {}
    return {
        "page_id": page.id,
        "url": page.url,
        "normalized_url": page.normalized_url,
        "title": page.title,
        "meta_description": page.meta_description,
        "h1": page.h1,
        "word_count": page.word_count,
        "page_type": page.page_type,
        "page_type_label": page.page_type_label,
        "http_status": page.http_status,
        "indexable": page.indexable,
        "canonical": page.canonical_url,
        "response_time_ms": page.response_time_ms,
        "html_size_bytes": page.response_size_bytes,
        "issue_count": page.issue_count,
        "crawl_status": page.crawl_status,
        "scores": {
            "seo": scores.get("seo"),
            "aeo": scores.get("aeo"),
            "uiux": scores.get("uiux"),
            "accessibility": scores.get("accessibility"),
            "performance": scores.get("performance"),
            "content": scores.get("content"),
            "structured_data": scores.get("structured_data"),
            "mobile": scores.get("mobile"),
            "cro": scores.get("cro"),
            "trust": scores.get("trust"),
        },
    }


def page_comparison_payload(
    *,
    primary: ScanRecord,
    competitor: ScanRecord,
    primary_page_id: str,
    competitor_page_id: str,
) -> dict[str, Any]:
    primary_pages = pages_from_result(primary.result)
    competitor_pages = pages_from_result(competitor.result)
    left = _page_lookup(primary_pages.items, primary_page_id)
    right = _page_lookup(competitor_pages.items, competitor_page_id)
    if left is None or left.scan_id != primary.id:
        raise KeyError("primary")
    if right is None or right.scan_id != competitor.id:
        raise KeyError("competitor")
    suggestions = suggest_matches(left, competitor_pages.items)
    metrics = []
    left_m = _page_metrics(left)
    right_m = _page_metrics(right)
    fields = [
        ("title", "Title"),
        ("meta_description", "Meta description"),
        ("h1", "H1"),
        ("word_count", "Word count"),
        ("page_type", "Page type"),
        ("http_status", "HTTP status"),
        ("indexable", "Indexability"),
        ("canonical", "Canonical"),
        ("response_time_ms", "Response time (ms)"),
        ("html_size_bytes", "HTML size (bytes)"),
        ("issue_count", "Issue count"),
        ("crawl_status", "Crawl status"),
    ]
    for key, label in fields:
        metrics.append(
            {
                "id": key,
                "label": label,
                "primary": left_m.get(key),
                "competitor": right_m.get(key),
            }
        )
    for key, label in (
        ("seo", "SEO score"),
        ("aeo", "AEO score"),
        ("uiux", "UI/UX score"),
        ("accessibility", "Accessibility score"),
        ("performance", "Performance score"),
        ("content", "Content score"),
        ("structured_data", "Structured Data score"),
        ("mobile", "Mobile score"),
        ("cro", "CRO score"),
        ("trust", "Trust Signals score"),
    ):
        left_score = left_m["scores"].get(key)
        right_score = right_m["scores"].get(key)
        if left_score is None and right_score is None:
            continue
        metrics.append(
            {
                "id": f"score_{key}",
                "label": label,
                "primary": left_score,
                "competitor": right_score,
                "primary_available": left_score is not None,
                "competitor_available": right_score is not None,
            }
        )
    return {
        "primary_page": left_m,
        "competitor_page": right_m,
        "metrics": metrics,
        "suggestions": suggestions,
    }
