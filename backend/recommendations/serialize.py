"""API shapes for recommendations."""

from __future__ import annotations

from typing import Any

from backend.pages.engine import payload_from_result as pages_from_result
from backend.recommendations.models import Recommendation, RecommendationsPayload
from backend.services.url_identity import normalize_page_url


def recommendation_to_list_item(item: Recommendation) -> dict[str, Any]:
    return {
        "id": item.id,
        "recommendation_key": item.recommendation_key,
        "title": item.title,
        "summary": item.summary,
        "category": item.category,
        "priority": item.priority,
        "impact": item.impact,
        "effort": item.effort,
        "status": item.status,
        "affected_page_count": item.affected_page_count,
        "affected_element_count": item.affected_element_count,
        "issue_count": item.issue_count,
        "issue_keys": item.issue_keys,
        "issue_ids": item.issue_ids,
        "page_ids": item.page_ids,
        "action_steps": item.action_steps,
        "source_kind": item.source_kind,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _related(item: Recommendation, siblings: list[Recommendation]) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []
    seen: set[str] = set()
    wanted = set(item.depends_on_recommendation_ids)
    for other in siblings:
        if other.id == item.id:
            continue
        if item.id in other.depends_on_recommendation_ids:
            wanted.add(other.id)
        if other.recommendation_key in item.depends_on_recommendation_keys:
            wanted.add(other.id)
        if other.category == item.category and other.priority in {"critical", "high"} and item.priority in {"critical", "high"}:
            wanted.add(other.id)
    for other in siblings:
        if other.id in wanted and other.id not in seen:
            seen.add(other.id)
            related.append(
                {
                    "id": other.id,
                    "recommendation_key": other.recommendation_key,
                    "title": other.title,
                    "category": other.category,
                    "priority": other.priority,
                    "status": other.status,
                }
            )
        if len(related) >= 8:
            break
    return related


def _affected_pages(item: Recommendation, result: dict[str, Any] | None) -> list[dict[str, Any]]:
    pages = pages_from_result(result)
    by_id = {page.id: page for page in pages.items}
    by_url: dict[str, Any] = {}
    for page in pages.items:
        for raw in (page.normalized_url, page.url, page.final_url):
            url = normalize_page_url(raw)
            if url and url not in by_url:
                by_url[url] = page
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page_id in item.page_ids:
        page = by_id.get(page_id)
        if page is None or page.id in seen:
            continue
        seen.add(page.id)
        rows.append(
            {
                "page_id": page.id,
                "url": page.normalized_url or page.url,
                "title": page.title,
                "page_type": page.page_type,
                "page_type_label": page.page_type_label,
                "issue_count": page.issue_count,
                "crawl_status": page.crawl_status,
            }
        )
    for url in item.page_urls:
        page = by_url.get(normalize_page_url(url))
        if page is None:
            rows.append(
                {
                    "page_id": None,
                    "url": url,
                    "title": None,
                    "page_type": None,
                    "page_type_label": None,
                    "issue_count": None,
                    "crawl_status": None,
                }
            )
            continue
        if page.id in seen:
            continue
        seen.add(page.id)
        rows.append(
            {
                "page_id": page.id,
                "url": page.normalized_url or page.url,
                "title": page.title,
                "page_type": page.page_type,
                "page_type_label": page.page_type_label,
                "issue_count": page.issue_count,
                "crawl_status": page.crawl_status,
            }
        )
    return rows


def recommendation_to_detail(
    item: Recommendation,
    payload: RecommendationsPayload,
    scan_id: str,
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "scan_id": scan_id,
        "recommendation": {
            **item.model_dump(mode="json"),
            "related_recommendations": _related(item, payload.recommendations),
            "affected_pages": _affected_pages(item, result),
        },
        "methodology": payload.methodology,
        "analyzer_status": payload.analyzer_status,
    }
