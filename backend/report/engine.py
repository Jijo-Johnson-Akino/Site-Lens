"""Assemble the professional report from persisted scan results. No new analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from backend.architecture.config import ORPHAN_NOTE
from backend.architecture.engine import (
    build_architecture,
    depth_distribution,
    insights_from_graph,
    notes_from_graph,
    page_type_distribution,
    summary_from_graph,
)
from backend.issues.engine import issue_to_list_item, payload_from_result as issues_from_result
from backend.issues.query import query_issues
from backend.pages.engine import payload_from_result as pages_from_result
from backend.pages.reasons import FAIL_CODES, SKIP_CODES
from backend.recommendations.engine import payload_from_result as recommendations_from_result
from backend.recommendations.query import query_recommendations
from backend.report.config import (
    A11Y_LIMITATION,
    AEO_NOTE,
    ANALYZER_SECTIONS,
    COMPETITORS_EMPTY,
    CRO_NOTE,
    MAX_AFFECTED_PAGES,
    MAX_ANALYZER_ISSUES,
    MAX_COMPETITOR_METRICS,
    MAX_INSIGHTS,
    MAX_KEY_FINDINGS,
    MAX_PRIORITY_ISSUES,
    MAX_RECOMMENDATIONS,
    MAX_SCREENSHOTS,
    METHODOLOGY_PARAGRAPHS,
    NO_ARCHITECTURE,
    NO_ISSUES,
    NO_RECOMMENDATIONS,
    NO_SCREENSHOTS,
    ORPHAN_WORDING,
    REPORT_VERSION,
    SAFE_SCREENSHOT_PREFIX,
    STRUCTURED_DATA_NOTE,
    TRUST_NOTE,
)
from backend.report.limitations import collect_limitations
from backend.schemas.scan import ScanRecord
from backend.scoring.models import HealthResult
from backend.scoring.repository import health_from_result
from backend.scoring.serializers import methodology_response, score_response
from backend.scoring.weights import CATEGORY_HREFS, CATEGORY_LABELS, CATEGORY_WEIGHTS, ERROR_KEYS, PAYLOAD_KEYS
from backend.services.url_identity import url_path

SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")
PRIORITY_ORDER = ("critical", "high", "medium", "low", "info")
PAGE_DISTRIBUTION_KEYS = ("healthy", "have_issues", "broken", "redirects", "blocked")
REDIRECT_REASONS = {SKIP_CODES["EXTERNAL_REDIRECT"], FAIL_CODES["REDIRECT_ERROR"]}
BLOCKED_REASONS = {SKIP_CODES["BLOCKED_URL"]}


def assemble_report(
    record: ScanRecord,
    competitor_comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = record.result if isinstance(record.result, dict) else {}
    generated_at = datetime.now(timezone.utc).isoformat()
    health = health_from_result(result)
    pages = pages_from_result(result)
    issues_payload = issues_from_result(record.id, result, _iso(record.created_at))
    recs_payload = recommendations_from_result(record.id, result, _iso(record.created_at))
    recs_error = bool(result.get("recommendations_error")) and not recs_payload.recommendations

    architecture = _architecture_block(record.id, result, pages)
    score = _score_block(record.id, health)
    categories = _category_rows(health)
    issues = _issues_block(record.id, issues_payload)
    recommendations = _recommendations_block(record.id, recs_payload, recs_error)
    pages_block = _pages_block(record.id, pages, health)
    analyzers = _analyzer_sections(record.id, result, health)
    screenshots = _screenshots(result)
    competitors = _competitors_block(competitor_comparison)
    limitations = collect_limitations(
        result,
        health=health,
        pages=pages,
        issues_truncated=bool(issues_payload.truncated),
        recommendations_error=recs_error,
        competitors_included=bool(competitors.get("included")),
        architecture_available=bool(architecture.get("available")),
        links_recorded=bool((architecture.get("summary") or {}).get("links_recorded")),
    )

    overview = _overview(
        health=health,
        categories=categories,
        issues=issues,
        recommendations=recommendations,
        pages_block=pages_block,
    )
    report_status = _report_status(health, analyzers, result)

    return {
        "report_version": REPORT_VERSION,
        "report_status": report_status,
        "generated_at": generated_at,
        "scan": _scan_meta(record, result, generated_at),
        "overview": overview,
        "score": score,
        "categories": categories,
        "architecture_note": (
            health.architecture.model_dump(mode="json")
            if health
            else {
                "name": "Website Architecture",
                "status": "informational",
                "included_in_score": False,
                "href": "architecture",
                "note": "Website Architecture is a structural crawl visualization and is not included in the weighted Health Score.",
            }
        ),
        "issues": issues,
        "priority_issues": issues["priority_issues"],
        "key_findings": issues["key_findings"],
        "recommendations": recommendations,
        "pages": pages_block,
        "architecture": architecture,
        "seo": analyzers["seo"],
        "aeo": analyzers["aeo"],
        "uiux": analyzers["uiux"],
        "accessibility": analyzers["accessibility"],
        "performance": analyzers["performance"],
        "content": analyzers["content"],
        "structured_data": analyzers["structured_data"],
        "mobile": analyzers["mobile"],
        "cro": analyzers["cro"],
        "trust": analyzers["trust"],
        "screenshots": screenshots,
        "competitors": competitors,
        "limitations": limitations,
        "methodology": _methodology(record.id, health),
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _scan_meta(record: ScanRecord, result: dict[str, Any], generated_at: str) -> dict[str, Any]:
    seo = result.get("seo") if isinstance(result.get("seo"), dict) else {}
    page = seo.get("page") if isinstance(seo.get("page"), dict) else {}
    final_url = page.get("final_url") or None
    website = record.normalized_url or record.url
    final_differs = bool(final_url) and _normalize_compare(final_url) != _normalize_compare(website)
    return {
        "scan_id": record.id,
        "website": website,
        "url": record.url,
        "normalized_url": record.normalized_url,
        "final_url": final_url if final_differs else None,
        "status": record.status,
        "created_at": _iso(record.created_at),
        "started_at": _iso(record.started_at),
        "completed_at": _iso(record.completed_at),
        "generated_at": generated_at,
        "analyzed_at": _iso(record.completed_at) or _iso(record.started_at) or _iso(record.created_at),
        "viewport": _viewport_label(result),
    }


def _normalize_compare(value: str) -> str:
    return value.strip().rstrip("/").lower()


def _score_block(scan_id: str, health: HealthResult | None) -> dict[str, Any] | None:
    if health is None:
        return None
    return score_response(scan_id, health)


def _category_rows(health: HealthResult | None) -> list[dict[str, Any]]:
    if health is not None:
        rows = []
        for item in health.categories:
            rows.append(
                {
                    "category": item.category,
                    "name": item.name,
                    "score": item.score,
                    "weight": item.weight,
                    "status": item.status,
                    "available": item.available,
                    "issue_count": item.issue_count,
                    "href": item.href,
                    "reason": item.reason,
                }
            )
        return rows
    return [
        {
            "category": key,
            "name": CATEGORY_LABELS[key],
            "score": None,
            "weight": CATEGORY_WEIGHTS[key],
            "status": "unavailable",
            "available": False,
            "issue_count": None,
            "href": CATEGORY_HREFS[key],
            "reason": "Category score was not available from stored results.",
        }
        for key in CATEGORY_WEIGHTS
    ]


def _overview(
    *,
    health: HealthResult | None,
    categories: list[dict[str, Any]],
    issues: dict[str, Any],
    recommendations: dict[str, Any],
    pages_block: dict[str, Any],
) -> dict[str, Any]:
    available = sum(1 for row in categories if row.get("status") in {"available", "partial"})
    configured = len(categories)
    overall = health.overall if health else None
    coverage = health.coverage if health else None
    pages_summary = pages_block.get("summary") or {}
    return {
        "overall_score": overall.score if overall else None,
        "score_status": overall.status if overall else None,
        "score_band": overall.band if overall else None,
        "score_coverage": coverage.coverage_percent if coverage else None,
        "coverage_status": coverage.status if coverage else "unavailable",
        "categories_analyzed": available,
        "categories_configured": configured,
        "pages_analyzed": pages_summary.get("crawled") if pages_block.get("available") else None,
        "pages_discovered": pages_summary.get("discovered") if pages_block.get("available") else None,
        "issues_detected": issues.get("total"),
        "recommendations": recommendations.get("total"),
    }


def _report_status(health: HealthResult | None, analyzers: dict[str, Any], result: dict[str, Any]) -> str:
    if not result:
        return "unavailable"
    statuses = [block.get("status") for block in analyzers.values()]
    has_payload = any(status in {"available", "partial"} for status in statuses)
    if health is None and not has_payload:
        return "unavailable"
    missing = any(status in {"unavailable", "failed"} for status in statuses)
    coverage = health.coverage.status if health else "unavailable"
    if health and coverage == "complete" and not missing:
        return "ready"
    return "partial"


def _finding_item(scan_id: str, issue: Any) -> dict[str, Any]:
    item = issue_to_list_item(issue)
    item["href"] = f"/scan/{scan_id}/issues/{issue.issue_id}"
    return item


def _issues_block(scan_id: str, payload: Any) -> dict[str, Any]:
    summary = payload.summary
    by_severity = {key: int(summary.by_severity.get(key, 0) or 0) for key in SEVERITY_ORDER}
    priority_items, _meta = query_issues(payload.issues, {"sort": "priority", "order": "desc", "page": 1, "page_size": MAX_PRIORITY_ISSUES})
    finding_items, _ = query_issues(payload.issues, {"sort": "priority", "order": "desc", "page": 1, "page_size": MAX_KEY_FINDINGS})
    grouped: dict[str, list[dict[str, Any]]] = {key: [] for key in SEVERITY_ORDER}
    for issue in finding_items:
        severity = issue.severity if issue.severity in grouped else "info"
        grouped[severity].append(_finding_item(scan_id, issue))
    total = int(summary.total)
    return {
        "total": total,
        "by_severity": by_severity,
        "by_priority": dict(summary.by_priority),
        "truncated": bool(payload.truncated),
        "empty_message": NO_ISSUES if total == 0 else None,
        "href": f"/scan/{scan_id}/issues",
        "priority_issues": [_finding_item(scan_id, item) for item in priority_items],
        "priority_note": "Highest-priority findings from the current scan.",
        "key_findings": [{"severity": key, "items": grouped[key]} for key in SEVERITY_ORDER if grouped[key]],
        "screenshot_capture": payload.screenshot_capture.model_dump(mode="json") if getattr(payload, "screenshot_capture", None) else None,
    }


def _recommendations_block(scan_id: str, payload: Any, recs_error: bool) -> dict[str, Any]:
    summary = payload.summary
    items, _meta = query_recommendations(
        payload.recommendations,
        {"sort": "priority", "order": "desc", "page": 1, "page_size": MAX_RECOMMENDATIONS},
    )
    by_priority = {key: int(summary.by_priority.get(key, 0) or 0) for key in PRIORITY_ORDER}
    preview = [{"priority": key, "count": by_priority[key]} for key in PRIORITY_ORDER if by_priority[key]]
    compact = []
    for item in items:
        first_step = item.action_steps[0] if item.action_steps else None
        compact.append(
            {
                "id": item.id,
                "title": item.title,
                "summary": item.summary,
                "action_summary": item.summary or first_step,
                "category": item.category,
                "priority": item.priority,
                "effort": item.effort,
                "impact": item.impact,
                "affected_page_count": item.affected_page_count,
                "issue_count": item.issue_count,
                "href": f"/scan/{scan_id}/recommendations/{item.id}",
            }
        )
    total = int(summary.total)
    empty = NO_RECOMMENDATIONS
    if recs_error:
        empty = "Recommendations could not be generated from the stored findings."
    by_category = {
        key: int(count)
        for key, count in dict(getattr(summary, "by_category", None) or {}).items()
        if int(count or 0) > 0
    }
    if not by_category:
        counts: dict[str, int] = defaultdict(int)
        for item in payload.recommendations:
            label = (item.category or "").strip()
            if label:
                counts[label] += 1
        by_category = {key: value for key, value in counts.items() if value > 0}
    return {
        "total": total,
        "by_priority": by_priority,
        "by_category": by_category,
        "action_plan_preview": preview,
        "items": compact,
        "empty_message": empty if total == 0 else None,
        "href": f"/scan/{scan_id}/recommendations",
        "action_plan_href": f"/scan/{scan_id}/action-plan",
        "preview_note": "Priority grouping of stored recommendations. Open the Action Plan to track status.",
    }


def _pages_block(scan_id: str, pages: Any, health: HealthResult | None) -> dict[str, Any]:
    if not pages.items and not pages.summary.discovered:
        return {
            "available": False,
            "summary": None,
            "indexability": None,
            "page_types": [],
            "top_affected_pages": [],
            "empty_message": "Page records are unavailable for this scan.",
            "href": f"/scan/{scan_id}/pages",
        }
    summary = pages.summary.model_dump(mode="json")
    with_issues = sum(1 for page in pages.items if page.issue_count > 0)
    without_issues = sum(1 for page in pages.items if page.issue_count == 0)
    if health and health.page_summary.pages_with_issues is not None:
        with_issues = health.page_summary.pages_with_issues
    if health and health.page_summary.pages_without_issues is not None:
        without_issues = health.page_summary.pages_without_issues
    types: dict[str, int] = defaultdict(int)
    for page in pages.items:
        types[(page.page_type_label or page.page_type or "unknown")] += 1
    known_index = [page for page in pages.items if page.indexable is not None]
    indexability = None
    if known_index:
        indexability = {
            "pages_with_indexability": len(known_index),
            "indexable": sum(1 for page in known_index if page.indexable),
            "not_indexable": sum(1 for page in known_index if page.indexable is False),
            "unknown": len(pages.items) - len(known_index),
        }
    ranked = sorted(pages.items, key=lambda page: (-page.issue_count, page.url or ""))
    top = [
        {
            "page_id": page.id,
            "url": page.url,
            "path": url_path(page.normalized_url or page.url),
            "title": page.title,
            "issue_count": page.issue_count,
            "page_type": page.page_type_label or page.page_type,
            "href": f"/scan/{scan_id}/pages/{page.id}",
        }
        for page in ranked
        if page.issue_count > 0
    ][:MAX_AFFECTED_PAGES]
    return {
        "available": True,
        "summary": summary,
        "pages_with_issues": with_issues,
        "pages_without_issues": without_issues,
        "indexability": indexability,
        "page_types": [{"label": label, "count": count} for label, count in sorted(types.items(), key=lambda item: (-item[1], item[0]))],
        "top_affected_pages": top,
        "top_affected_note": "Pages with the highest number of detected issues.",
        "distribution": _page_distribution(pages.items),
        "href": f"/scan/{scan_id}/pages",
    }


def _viewport_label(result: dict[str, Any]) -> str | None:
    perf = result.get("performance") if isinstance(result.get("performance"), dict) else {}
    env = perf.get("environment") if isinstance(perf.get("environment"), dict) else {}
    name = env.get("viewport_name")
    if isinstance(name, str) and name.strip():
        return name.replace("_", " ").strip().title()
    uiux = result.get("uiux") if isinstance(result.get("uiux"), dict) else {}
    viewports = uiux.get("viewports")
    if isinstance(viewports, dict) and viewports:
        labels = [str(key).replace("_", " ").strip().title() for key in viewports if str(key).strip()]
        return ", ".join(labels) if labels else None
    return None


def _classify_page(page: Any) -> str | None:
    reason = page.skip_reason or page.failure_reason or ""
    status = page.crawl_status
    http = page.http_status
    if reason in REDIRECT_REASONS:
        return "redirects"
    if reason in BLOCKED_REASONS:
        return "blocked"
    if status == "failed":
        return "broken"
    if status == "skipped":
        return None
    if status != "crawled":
        return None
    if isinstance(http, int) and 300 <= http < 400:
        return "redirects"
    if isinstance(http, int) and http >= 400:
        return "broken"
    if page.issue_count > 0:
        return "have_issues"
    return "healthy"


def _page_distribution(items: list[Any]) -> dict[str, int]:
    buckets = {key: 0 for key in PAGE_DISTRIBUTION_KEYS}
    for page in items:
        key = _classify_page(page)
        if key in buckets:
            buckets[key] += 1
    return buckets


def _architecture_block(scan_id: str, result: dict[str, Any], pages: Any) -> dict[str, Any]:
    href = f"/scan/{scan_id}/architecture"
    if not pages.items:
        return {
            "available": False,
            "summary": None,
            "empty_message": NO_ARCHITECTURE,
            "href": href,
            "orphan_note": ORPHAN_WORDING,
        }
    graph = build_architecture(result)
    summary = summary_from_graph(graph)
    return {
        "available": True,
        "summary": summary,
        "depth_distribution": depth_distribution(graph),
        "page_type_distribution": page_type_distribution(graph),
        "insights": insights_from_graph(graph)[:MAX_INSIGHTS],
        "notes": notes_from_graph(graph),
        "orphan_note": ORPHAN_NOTE,
        "orphan_wording": ORPHAN_WORDING,
        "href": href,
    }


def _analyzer_sections(scan_id: str, result: dict[str, Any], health: HealthResult | None) -> dict[str, Any]:
    health_by_key = {item.category: item for item in health.categories} if health else {}
    blocks: dict[str, Any] = {}
    for key, name, href in ANALYZER_SECTIONS:
        payload = result.get(PAYLOAD_KEYS[key])
        error = result.get(ERROR_KEYS[key])
        health_row = health_by_key.get(key)
        score = health_row.score if health_row else (payload.get("score") if isinstance(payload, dict) else None)
        if isinstance(payload, dict):
            status = health_row.status if health_row else "available"
            if score is None and key in {"cro", "trust"}:
                status = health_row.status if health_row else "partial"
            block = {
                "available": True,
                "status": status,
                "name": name,
                "score": score if isinstance(score, (int, float)) else None,
                "summary": _summary_counts(payload.get("summary")),
                "narrative": payload.get("narrative"),
                "categories": payload.get("categories") if isinstance(payload.get("categories"), dict) else {},
                "issues": _analyzer_issues(payload.get("issues")),
                "href": f"/scan/{scan_id}/{href}",
                "detail_label": f"View detailed {name} analysis",
            }
            block.update(_analyzer_extras(key, payload))
            blocks[key] = block
            continue
        message = None
        if isinstance(error, dict):
            message = error.get("message")
            status = "failed"
        else:
            status = "unavailable"
            message = f"{name} results are not available for this scan."
        blocks[key] = {
            "available": False,
            "status": status,
            "name": name,
            "score": None,
            "summary": None,
            "narrative": None,
            "categories": {},
            "issues": [],
            "message": message,
            "href": f"/scan/{scan_id}/{href}",
            "detail_label": f"View detailed {name} analysis",
        }
    return blocks


def _summary_counts(summary: Any) -> dict[str, Any] | None:
    if not isinstance(summary, dict):
        return None
    keys = (
        "passed",
        "warnings",
        "failed",
        "not_applicable",
        "info",
        "jsonld_blocks",
        "microdata_items",
        "rdfa_items",
        "entities",
        "schema_types",
        "manual_review",
    )
    return {key: summary[key] for key in keys if key in summary}


def _analyzer_issues(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    items = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        items.append(
            {
                "title": row.get("name") or row.get("title"),
                "severity": row.get("severity"),
                "status": row.get("status"),
                "message": row.get("message"),
                "recommendation": row.get("recommendation"),
                "page_url": row.get("page_url"),
            }
        )
        if len(items) >= MAX_ANALYZER_ISSUES:
            break
    return items


def _analyzer_extras(key: str, payload: dict[str, Any]) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if key == "seo":
        extra["indexable"] = payload.get("indexable") if isinstance(payload.get("indexable"), dict) else None
        extra["page"] = _pick(payload.get("page"), ("analyzed_url", "final_url", "status_code", "title", "h1"))
    elif key == "aeo":
        extra["insight"] = payload.get("insight")
        extra["note"] = AEO_NOTE
        extra["page"] = _pick(payload.get("page"), ("analyzed_url", "final_url", "title", "h1", "language"))
    elif key == "uiux":
        extra["viewports"] = _viewport_scores(payload.get("viewports"))
        extra["screenshots"] = _safe_shots(payload.get("screenshots"))
    elif key == "accessibility":
        extra["tool"] = _pick(payload.get("tool"), ("name", "version", "axe_violations", "axe_incomplete", "axe_passes", "standard", "automated_only"))
        extra["standard"] = payload.get("standard") if isinstance(payload.get("standard"), dict) else None
        extra["severity_counts"] = payload.get("severity_counts") if isinstance(payload.get("severity_counts"), dict) else None
        extra["limitation"] = A11Y_LIMITATION
        extra["limitations"] = [item for item in (payload.get("limitations") or []) if isinstance(item, str)]
    elif key == "performance":
        extra["environment"] = payload.get("environment") if isinstance(payload.get("environment"), dict) else None
        extra["timing"] = _pick(
            payload.get("timing"),
            ("ttfb_ms", "load_event_ms", "dom_content_loaded_ms", "response_end_ms", "redirect_count"),
        )
        extra["vitals"] = payload.get("vitals") if isinstance(payload.get("vitals"), dict) else None
        extra["resources"] = _pick(
            payload.get("resources"),
            (
                "total_requests",
                "transfer_bytes",
                "js_bytes",
                "css_bytes",
                "image_bytes",
                "third_party_bytes",
                "third_party_requests",
            ),
        )
        extra["long_tasks"] = len(payload["long_tasks"]) if isinstance(payload.get("long_tasks"), list) else None
        extra["limitations"] = [item for item in (payload.get("limitations") or []) if isinstance(item, str)]
    elif key == "content":
        extra["page_type"] = payload.get("page_type") if isinstance(payload.get("page_type"), dict) else None
        extra["metrics"] = _pick(
            payload.get("metrics"),
            ("word_count", "main_word_count", "heading_count", "paragraph_count", "h1_count", "h2_count", "h3_count"),
        )
        extra["readability"] = payload.get("readability") if isinstance(payload.get("readability"), dict) else None
        extra["signals"] = payload.get("signals") if isinstance(payload.get("signals"), dict) else None
        extra["note"] = "Detected content signals. This is not a claim of factual accuracy or originality."
        extra["limitations"] = [item for item in (payload.get("limitations") or []) if isinstance(item, str)]
    elif key == "structured_data":
        extra["note"] = STRUCTURED_DATA_NOTE
        extra["open_graph"] = _social_keys(payload.get("open_graph"))
        extra["twitter"] = _social_keys(payload.get("twitter"))
        extra["schema_types"] = _schema_types(payload)
        extra["relationship_count"] = len(payload["relationships"]) if isinstance(payload.get("relationships"), list) else None
        extra["limitations"] = [item for item in (payload.get("limitations") or []) if isinstance(item, str)]
    elif key == "mobile":
        extra["environment"] = payload.get("environment") if isinstance(payload.get("environment"), dict) else None
        extra["overview"] = payload.get("overview") if isinstance(payload.get("overview"), dict) else None
        extra["viewport"] = payload.get("viewport") if isinstance(payload.get("viewport"), dict) else None
        extra["screenshots"] = _safe_shots(payload.get("screenshots"))
        extra["limitations"] = [item for item in (payload.get("limitations") or []) if isinstance(item, str)]
    elif key == "cro":
        extra["score_note"] = payload.get("score_note")
        extra["crawl_note"] = payload.get("crawl_note")
        extra["methodology"] = payload.get("methodology")
        extra["cta_count"] = len(payload["ctas"]) if isinstance(payload.get("ctas"), list) else None
        extra["form_count"] = len(payload["forms"]) if isinstance(payload.get("forms"), list) else None
        extra["conversion_paths"] = _path_messages(payload.get("conversion_paths"))
        extra["note"] = CRO_NOTE
        extra["limitations"] = [item for item in (payload.get("limitations") or []) if isinstance(item, str)]
    elif key == "trust":
        extra["score_note"] = payload.get("score_note")
        extra["crawl_note"] = payload.get("crawl_note")
        extra["methodology"] = payload.get("methodology")
        extra["policies"] = _policy_rows(payload.get("policies"))
        extra["signal_counts"] = {
            "detected": len(payload["signals"]) if isinstance(payload.get("signals"), list) else None,
            "gaps": len(payload["gaps"]) if isinstance(payload.get("gaps"), list) else None,
        }
        extra["security"] = _security_rows(payload.get("security"))
        extra["note"] = TRUST_NOTE
        extra["limitations"] = [item for item in (payload.get("limitations") or []) if isinstance(item, str)]
    return extra


def _pick(raw: Any, keys: tuple[str, ...]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    return {key: raw.get(key) for key in keys if key in raw}


def _viewport_scores(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    rows = []
    for name, value in raw.items():
        if not isinstance(value, dict):
            continue
        rows.append(
            {
                "viewport": name,
                "score": value.get("score") if isinstance(value.get("score"), (int, float)) else None,
                "width": value.get("width"),
                "height": value.get("height"),
                "summary": _summary_counts(value.get("summary")),
            }
        )
    return rows


def _social_keys(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    properties = raw.get("properties") if isinstance(raw.get("properties"), dict) else {}
    return {
        "property_count": len(properties),
        "properties": sorted(str(key) for key in properties.keys())[:20],
        "duplicates": raw.get("duplicates") if isinstance(raw.get("duplicates"), list) else [],
        "empty": raw.get("empty") if isinstance(raw.get("empty"), list) else [],
    }


def _schema_types(payload: dict[str, Any]) -> list[str]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    types = summary.get("schema_types") if isinstance(summary, dict) else None
    if isinstance(types, list):
        return [str(item) for item in types[:20]]
    found: list[str] = []
    for entity in payload.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        for item in entity.get("types") or []:
            text = str(item)
            if text not in found:
                found.append(text)
            if len(found) >= 20:
                return found
    return found


def _path_messages(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    messages = []
    for row in raw:
        if isinstance(row, dict) and row.get("message"):
            messages.append(str(row["message"]))
        if len(messages) >= 5:
            break
    return messages


def _policy_rows(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    rows = []
    for item in raw[:12]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "policy": item.get("policy"),
                "detected": bool(item.get("detected")),
                "page_url": item.get("page_url"),
                "note": item.get("note"),
            }
        )
    return rows


def _security_rows(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    rows = []
    for item in raw[:12]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "signal": item.get("signal"),
                "detected": bool(item.get("detected")),
                "evidence": item.get("evidence"),
            }
        )
    return rows


def _safe_shots(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    shots = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        if not url.startswith(SAFE_SCREENSHOT_PREFIX):
            continue
        viewport = str(item.get("viewport") or item.get("kind") or "capture")
        shots.append(
            {
                "viewport": viewport,
                "width": item.get("width"),
                "height": item.get("height"),
                "url": url,
                "alt": f"{viewport.replace('_', ' ').title()} capture of the analyzed page",
            }
        )
        if len(shots) >= MAX_SCREENSHOTS:
            break
    return shots


def _screenshots(result: dict[str, Any]) -> dict[str, Any]:
    uiux = result.get("uiux") if isinstance(result.get("uiux"), dict) else {}
    shots = _safe_shots(uiux.get("screenshots") if isinstance(uiux, dict) else None)
    if not shots:
        mobile = result.get("mobile") if isinstance(result.get("mobile"), dict) else {}
        shots = _safe_shots(mobile.get("screenshots") if isinstance(mobile, dict) else None)
    return {
        "available": bool(shots),
        "items": shots,
        "empty_message": None if shots else NO_SCREENSHOTS,
    }


def _competitors_block(comparison: dict[str, Any] | None) -> dict[str, Any]:
    if not comparison or not comparison.get("competitors"):
        return {
            "included": False,
            "competitor_count": 0,
            "empty_message": COMPETITORS_EMPTY,
            "columns": [],
            "categories": [],
            "metrics": [],
            "warnings": [],
        }
    metrics = comparison.get("metrics") or []
    if isinstance(metrics, list):
        metrics = metrics[:MAX_COMPETITOR_METRICS]
    return {
        "included": True,
        "competitor_count": len(comparison.get("competitors") or []),
        "primary": comparison.get("primary"),
        "competitors": comparison.get("competitors") or [],
        "columns": comparison.get("columns") or [],
        "categories": comparison.get("categories") or [],
        "metrics": metrics,
        "severity": comparison.get("severity") or [],
        "warnings": comparison.get("warnings") or [],
        "methodology": comparison.get("methodology"),
        "note": "Factual comparison of measured values. SiteLens does not order competitors.",
    }


def _methodology(scan_id: str, health: HealthResult | None) -> dict[str, Any]:
    score_method = methodology_response(scan_id, health)
    return {
        "report_version": REPORT_VERSION,
        "calculation_version": score_method.get("calculation_version"),
        "paragraphs": list(METHODOLOGY_PARAGRAPHS),
        "score": score_method,
    }
