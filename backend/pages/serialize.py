"""API shapes for Pages Explorer list and detail responses."""

from __future__ import annotations

from typing import Any

from backend.issues.models import IssuesPayload
from backend.pages.engine import analyzer_cards, related_issue_items
from backend.pages.models import PageRecord


def page_to_list_item(page: PageRecord) -> dict[str, Any]:
    scores = page.analyzer_scores or {}
    return {
        "id": page.id,
        "url": page.url,
        "normalized_url": page.normalized_url,
        "final_url": page.final_url,
        "page_type": page.page_type,
        "page_type_label": page.page_type_label,
        "crawl_status": page.crawl_status,
        "http_status": page.http_status,
        "title": page.title,
        "meta_description": page.meta_description,
        "h1": page.h1,
        "canonical_url": page.canonical_url,
        "indexable": page.indexable,
        "word_count": page.word_count,
        "depth": page.depth,
        "response_time_ms": page.response_time_ms,
        "issue_count": page.issue_count,
        "severity_counts": page.severity_counts,
        "available_analyzers": page.available_analyzers,
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
        "skip_reason": page.skip_reason,
        "failure_reason": page.failure_reason,
        "is_seed": page.is_seed,
    }


def page_to_detail(
    page: PageRecord,
    *,
    scan_id: str,
    issues_payload: IssuesPayload | None = None,
) -> dict[str, Any]:
    item = page_to_list_item(page)
    item.update(
        {
            "discovered_from": page.discovered_from,
            "discovery_method": page.discovery_method,
            "content_type": page.content_type,
            "response_size_bytes": page.response_size_bytes,
            "h1_count": page.h1_count,
            "h2_count": page.h2_count,
            "robots_directive": page.robots_directive,
            "language": page.language,
            "internal_link_count": page.internal_link_count,
            "external_link_count": page.external_link_count,
            "image_count": page.image_count,
            "paragraph_count": page.paragraph_count,
            "list_count": page.list_count,
            "schema_types": page.schema_types,
            "headings": page.headings,
            "analyzers": analyzer_cards(page, scan_id),
            "issues": related_issue_items(page, issues_payload),
            "created_at": page.created_at,
            "updated_at": page.updated_at,
        }
    )
    return item
