from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Body, Query
from fastapi.responses import JSONResponse, Response
from urllib.parse import quote

from backend.analyzers.mobile.screenshots import allowed_screenshot_key
from backend.analyzers.uiux.config import all_known_viewports
from backend.errors import ScanError
from backend.issues.engine import issue_to_detail, issue_to_list_item, payload_from_result
from backend.issues.query import query_issues
from backend.architecture.engine import build_architecture
from backend.architecture.query import query_links, query_nodes
from backend.architecture.serialize import architecture_response, links_response, page_architecture_response
from backend.pages.engine import payload_from_result as pages_from_result
from backend.pages.query import query_pages
from backend.pages.serialize import page_to_detail, page_to_list_item
from backend.competitors.comparison import build_comparison
from backend.competitors.config import MAX_COMPETITORS, limit_note
from backend.competitors.matching import suggest_matches
from backend.competitors.serialize import competitor_detail, competitor_to_card, page_comparison_payload
from backend.competitors.service import CompetitorService
from backend.recommendations.config import METHODOLOGY, STATUSES as RECOMMENDATION_STATUSES
from backend.recommendations.engine import payload_from_result as recommendations_from_result
from backend.recommendations.query import query_recommendations
from backend.recommendations.serialize import recommendation_to_detail, recommendation_to_list_item
from backend.report.engine import assemble_report
from backend.report.config import REPORT_UNAVAILABLE
from backend.report.pdf import render_report_pdf, report_pdf_filename
from backend.scoring.repository import health_from_result
from backend.scoring.serializers import methodology_response, score_response
from backend.schemas.scan import ScanCreateRequest, ScanCreateResponse, ScanStatusResponse
from backend.services.scan_service import ScanService

logger = logging.getLogger("sitebench.api")
router = APIRouter(prefix="/api")
service = ScanService()


def _competitor_service() -> CompetitorService:
    return CompetitorService(service)


def _competitor_error(exc: ScanError) -> JSONResponse:
    status = 400
    if exc.code in {"SCAN_NOT_FOUND", "COMPETITOR_NOT_FOUND"}:
        status = 404
    elif exc.code in {"SCAN_NOT_READY", "SCAN_FAILED"}:
        status = 409
    elif exc.code == "SCAN_LIMIT":
        status = 429
    return JSONResponse(status_code=status, content={"error": {"code": exc.code, "message": exc.message}})


def _status_payload(record) -> ScanStatusResponse:
    if record.status == "completed":
        result = record.result
    else:
        pages = (record.result or {}).get("pages") if record.result else None
        result = (
            {
                "pages": {
                    "summary": pages.get("summary"),
                    "limits": pages.get("limits"),
                    "in_progress": True,
                }
            }
            if isinstance(pages, dict)
            else None
        )
    return ScanStatusResponse(
        scan_id=record.id,
        url=record.url,
        normalized_url=record.normalized_url,
        status=record.status,
        progress=record.progress,
        current_step=record.current_step,
        created_at=record.created_at.isoformat() if record.created_at else None,
        completed_at=record.completed_at.isoformat() if record.completed_at else None,
        error=record.error,
        result=result,
    )


def _module_payload(record, key: str, label: str, extra: tuple[str, ...] = ()):
    code_name = label.upper().replace("/", "").replace(" ", "_")
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    if record.status == "failed":
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "SCAN_FAILED",
                    "message": (record.error or {}).get("message") or "This scan did not complete.",
                }
            },
        )
    if record.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": f"{label} results are not available yet."}},
        )
    payload = (record.result or {}).get(key)
    if not payload:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": f"{code_name}_NOT_AVAILABLE",
                    "message": f"{label} results are not available for this scan.",
                }
            },
        )
    body = {
        "scan_id": record.id,
        "score": payload.get("score"),
        "summary": payload.get("summary"),
        "narrative": payload.get("narrative"),
        "categories": payload.get("categories") or {},
        "checks": payload.get("checks") or [],
        "issues": payload.get("issues") or [],
        "page": payload.get("page"),
    }
    for field in extra:
        body[field] = payload.get(field)
    return body


def _issues_record_or_error(record):
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    if record.status == "failed":
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "SCAN_FAILED",
                    "message": (record.error or {}).get("message") or "This scan did not complete.",
                }
            },
        )
    if record.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": "Issues are not available yet."}},
        )
    created = record.created_at.isoformat() if record.created_at else None
    return payload_from_result(record.id, record.result, created)


def _pages_record_or_error(record, *, require_completed: bool = False):
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    if record.status == "failed":
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "SCAN_FAILED",
                    "message": "Pages are unavailable because this scan failed.",
                }
            },
        )
    if require_completed and record.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": "Page details are not available yet."}},
        )
    return pages_from_result(record.result)


def _issues_payload_optional(record):
    if record is None or record.status != "completed" or not record.result:
        return None
    created = record.created_at.isoformat() if record.created_at else None
    try:
        return payload_from_result(record.id, record.result, created)
    except Exception:
        return None


def _recommendations_record_or_error(record):
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    if record.status == "failed":
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "SCAN_FAILED",
                    "message": (record.error or {}).get("message") or "This scan did not complete.",
                }
            },
        )
    if record.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": "Recommendations are not available yet."}},
        )
    error = (record.result or {}).get("recommendations_error")
    stored = (record.result or {}).get("recommendations")
    if error and not isinstance(stored, dict):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": error.get("code") or "RECOMMENDATIONS_NOT_AVAILABLE",
                    "message": error.get("message") or "Recommendations are not available for this scan.",
                }
            },
        )
    created = record.created_at.isoformat() if record.created_at else None
    return recommendations_from_result(record.id, record.result, created)


def _find_issue(payload, issue_id: str):
    for issue in payload.issues:
        if issue.issue_id == issue_id:
            return issue
        for occurrence in issue.occurrences:
            if occurrence.occurrence_id == issue_id:
                return issue
            if issue_id in occurrence.finding_ids:
                return issue
    return None


@router.post("/scans", response_model=ScanCreateResponse, status_code=202)
async def create_scan(body: ScanCreateRequest, background_tasks: BackgroundTasks):
    try:
        record = service.create(body.url)
    except ScanError as exc:
        status = 429 if exc.code == "SCAN_LIMIT" else 400
        return JSONResponse(
            status_code=status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
    background_tasks.add_task(service.run, record.id)
    return ScanCreateResponse(scan_id=record.id, status=record.status)


@router.get("/scans/{scan_id}", response_model=ScanStatusResponse)
async def get_scan(scan_id: str):
    record = service.get(scan_id)
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    return _status_payload(record)


@router.get("/scans/{scan_id}/seo")
async def get_scan_seo(scan_id: str):
    return _module_payload(service.get(scan_id), "seo", "SEO", extra=("indexable",))


@router.get("/scans/{scan_id}/aeo")
async def get_scan_aeo(scan_id: str):
    return _module_payload(service.get(scan_id), "aeo", "AEO", extra=("insight",))


@router.get("/scans/{scan_id}/uiux")
async def get_scan_uiux(scan_id: str):
    return _module_payload(service.get(scan_id), "uiux", "UI/UX", extra=("viewports", "screenshots"))


@router.get("/scans/{scan_id}/accessibility")
async def get_scan_accessibility(scan_id: str):
    record = service.get(scan_id)
    if record is not None and record.status == "completed":
        error = (record.result or {}).get("accessibility_error")
        if error and not (record.result or {}).get("accessibility"):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": error.get("code") or "ACCESSIBILITY_NOT_AVAILABLE",
                        "message": error.get("message") or "Accessibility analysis is not available for this scan.",
                    }
                },
            )
    payload = _module_payload(
        record,
        "accessibility",
        "Accessibility",
        extra=("tool", "standard", "limitations", "findings", "severity_counts", "screenshots", "category_cards"),
    )
    if isinstance(payload, dict):
        payload["status"] = record.status
        payload["url"] = record.normalized_url
        if payload.get("findings") is None:
            payload["findings"] = payload.get("checks") or []
    return payload


@router.get("/scans/{scan_id}/performance")
async def get_scan_performance(scan_id: str):
    record = service.get(scan_id)
    if record is not None and record.status == "completed":
        error = (record.result or {}).get("performance_error")
        if error and not (record.result or {}).get("performance"):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": error.get("code") or "PERFORMANCE_NOT_AVAILABLE",
                        "message": error.get("message") or "Performance analysis is not available for this scan.",
                    }
                },
            )
    payload = _module_payload(
        record,
        "performance",
        "Performance",
        extra=(
            "environment",
            "timing",
            "vitals",
            "resources",
            "resource_table",
            "limitations",
            "findings",
            "severity_counts",
            "category_cards",
        ),
    )
    if isinstance(payload, dict):
        payload["status"] = record.status
        payload["url"] = record.normalized_url
        if payload.get("findings") is None:
            payload["findings"] = payload.get("checks") or []
    return payload


@router.get("/scans/{scan_id}/content")
async def get_scan_content(scan_id: str):
    record = service.get(scan_id)
    if record is not None and record.status == "completed":
        error = (record.result or {}).get("content_error")
        if error and not (record.result or {}).get("content"):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": error.get("code") or "CONTENT_NOT_AVAILABLE",
                        "message": error.get("message") or "Content analysis is not available for this scan.",
                    }
                },
            )
    payload = _module_payload(
        record,
        "content",
        "Content",
        extra=(
            "page_type",
            "metrics",
            "readability",
            "signals",
            "structure",
            "duplicates",
            "limitations",
            "findings",
            "severity_counts",
            "category_cards",
            "truncated",
        ),
    )
    if isinstance(payload, dict):
        payload["status"] = record.status
        payload["url"] = record.normalized_url
        if payload.get("findings") is None:
            payload["findings"] = payload.get("checks") or []
    return payload


@router.get("/scans/{scan_id}/structured-data")
async def get_scan_structured_data(scan_id: str):
    record = service.get(scan_id)
    if record is not None and record.status == "completed":
        error = (record.result or {}).get("structured_data_error")
        if error and not (record.result or {}).get("structured_data"):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": error.get("code") or "STRUCTURED_DATA_NOT_AVAILABLE",
                        "message": error.get("message") or "Structured data analysis is not available for this scan.",
                    }
                },
            )
    payload = _module_payload(
        record,
        "structured_data",
        "Structured Data",
        extra=(
            "json_ld",
            "microdata",
            "rdfa",
            "entities",
            "relationships",
            "open_graph",
            "twitter",
            "consistency",
            "limitations",
            "findings",
            "severity_counts",
            "category_cards",
            "truncated",
            "page_type",
        ),
    )
    if isinstance(payload, dict):
        payload["status"] = record.status
        payload["url"] = record.normalized_url
        if payload.get("findings") is None:
            payload["findings"] = payload.get("checks") or []
    return payload


@router.get("/scans/{scan_id}/pages/summary")
async def get_scan_pages_summary(scan_id: str):
    record = service.get(scan_id)
    loaded = _pages_record_or_error(record)
    if isinstance(loaded, JSONResponse):
        return loaded
    return {
        "scan_id": scan_id,
        "status": record.status if record else None,
        "in_progress": bool(loaded.in_progress or (record and record.status not in {"completed", "failed"})),
        "summary": loaded.summary.model_dump(mode="json"),
        "limits": loaded.limits,
    }


@router.get("/scans/{scan_id}/pages")
async def get_scan_pages(
    scan_id: str,
    search: str | None = Query(default=None),
    page: str | None = Query(default=None),
    page_size: str | None = Query(default=None),
    page_type: str | None = Query(default=None),
    crawl_status: str | None = Query(default=None),
    http_status: str | None = Query(default=None),
    indexable: str | None = Query(default=None),
    has_issues: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    order: str | None = Query(default=None),
):
    record = service.get(scan_id)
    loaded = _pages_record_or_error(record)
    if isinstance(loaded, JSONResponse):
        return loaded
    items, pagination = query_pages(
        loaded.items,
        {
            "search": search,
            "page": page,
            "page_size": page_size,
            "page_type": page_type,
            "crawl_status": crawl_status,
            "http_status": http_status,
            "indexable": indexable,
            "has_issues": has_issues,
            "sort": sort,
            "order": order,
        },
    )
    return {
        "scan_id": scan_id,
        "status": record.status if record else None,
        "in_progress": bool(loaded.in_progress or (record and record.status not in {"completed", "failed"})),
        "items": [page_to_list_item(item) for item in items],
        "pagination": pagination,
        "summary": loaded.summary.model_dump(mode="json"),
        "limits": loaded.limits,
    }


@router.get("/scans/{scan_id}/pages/{page_id}")
async def get_scan_page(scan_id: str, page_id: str):
    record = service.get(scan_id)
    loaded = _pages_record_or_error(record)
    if isinstance(loaded, JSONResponse):
        return loaded
    page = next((item for item in loaded.items if item.id == page_id), None)
    if page is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "PAGE_NOT_FOUND", "message": "Page not found."}},
        )
    if page.scan_id != scan_id:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "PAGE_NOT_FOUND", "message": "Page not found."}},
        )
    return {
        "scan_id": scan_id,
        "status": record.status if record else None,
        "summary": loaded.summary.model_dump(mode="json"),
        "limits": loaded.limits,
        "page": page_to_detail(page, scan_id=scan_id, issues_payload=_issues_payload_optional(record)),
    }


@router.get("/scans/{scan_id}/architecture")
async def get_scan_architecture(
    scan_id: str,
    search: str | None = Query(default=None),
    page: str | None = Query(default=None),
    page_size: str | None = Query(default=None),
    page_type: str | None = Query(default=None),
    crawl_status: str | None = Query(default=None),
    depth: str | None = Query(default=None),
    has_issues: str | None = Query(default=None),
    orphan: str | None = Query(default=None),
    terminal: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    order: str | None = Query(default=None),
    graph_limit: str | None = Query(default=None),
    focus: str | None = Query(default=None),
):
    record = service.get(scan_id)
    loaded = _pages_record_or_error(record)
    if isinstance(loaded, JSONResponse):
        return loaded
    params = {
        "search": search,
        "page": page,
        "page_size": page_size,
        "page_type": page_type,
        "crawl_status": crawl_status,
        "depth": depth,
        "has_issues": has_issues,
        "orphan": orphan,
        "terminal": terminal,
        "sort": sort,
        "order": order,
        "graph_limit": graph_limit,
        "focus": focus,
    }
    graph = build_architecture(loaded)
    matching, paged, pagination = query_nodes(graph, params)
    return architecture_response(
        graph,
        scan_id=scan_id,
        status=record.status if record else None,
        params=params,
        matching=matching,
        paged=paged,
        pagination=pagination,
    )


@router.get("/scans/{scan_id}/architecture/links")
async def get_scan_architecture_links(
    scan_id: str,
    search: str | None = Query(default=None),
    page: str | None = Query(default=None),
    page_size: str | None = Query(default=None),
    source: str | None = Query(default=None),
    destination: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    order: str | None = Query(default=None),
):
    record = service.get(scan_id)
    loaded = _pages_record_or_error(record)
    if isinstance(loaded, JSONResponse):
        return loaded
    graph = build_architecture(loaded)
    items, pagination = query_links(
        graph,
        {
            "search": search,
            "page": page,
            "page_size": page_size,
            "source": source,
            "destination": destination,
            "sort": sort,
            "order": order,
        },
    )
    return links_response(
        graph,
        scan_id=scan_id,
        status=record.status if record else None,
        links=items,
        pagination=pagination,
    )


@router.get("/scans/{scan_id}/architecture/pages/{page_id}")
async def get_scan_architecture_page(scan_id: str, page_id: str):
    record = service.get(scan_id)
    loaded = _pages_record_or_error(record)
    if isinstance(loaded, JSONResponse):
        return loaded
    graph = build_architecture(loaded)
    node = graph.nodes.get(page_id)
    if node is None or node.page.scan_id != scan_id:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "PAGE_NOT_FOUND", "message": "Page not found."}},
        )
    return page_architecture_response(
        graph,
        node,
        scan_id=scan_id,
        status=record.status if record else None,
    )


@router.get("/scans/{scan_id}/issues/summary")
async def get_scan_issues_summary(scan_id: str):
    loaded = _issues_record_or_error(service.get(scan_id))
    if isinstance(loaded, JSONResponse):
        return loaded
    return {
        "scan_id": scan_id,
        "truncated": loaded.truncated,
        "analyzer_status": loaded.analyzer_status,
        "summary": loaded.summary.model_dump(mode="json"),
        "groups": {
            "category": {key: len(value) for key, value in (loaded.groups.get("category") or {}).items()},
            "priority": {key: len(value) for key, value in (loaded.groups.get("priority") or {}).items()},
            "source": {key: len(value) for key, value in (loaded.groups.get("source") or {}).items()},
        },
        "screenshot_capture": loaded.screenshot_capture.model_dump(mode="json"),
    }


@router.get("/scans/{scan_id}/issues")
async def get_scan_issues(
    scan_id: str,
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    category: str | None = Query(default=None),
    source: str | None = Query(default=None),
    check_status: str | None = Query(default=None),
    page: str | None = Query(default=None),
    page_size: str | None = Query(default=None),
    page_url: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    order: str | None = Query(default=None),
    include_all: str | None = Query(default=None),
    issue_key: str | None = Query(default=None),
    issue_ids: str | None = Query(default=None),
):
    loaded = _issues_record_or_error(service.get(scan_id))
    if isinstance(loaded, JSONResponse):
        return loaded
    items, pagination = query_issues(
        loaded.issues,
        {
            "status": status,
            "severity": severity,
            "priority": priority,
            "category": category,
            "source": source,
            "check_status": check_status,
            "page": page,
            "page_size": page_size,
            "page_url": page_url,
            "search": search,
            "sort": sort,
            "order": order,
            "include_all": include_all,
            "issue_key": issue_key,
            "issue_ids": issue_ids,
        },
    )
    return {
        "scan_id": scan_id,
        "items": [issue_to_list_item(item) for item in items],
        "pagination": pagination,
        "summary": loaded.summary.model_dump(mode="json"),
        "analyzer_status": loaded.analyzer_status,
        "truncated": loaded.truncated,
        "screenshot_capture": loaded.screenshot_capture.model_dump(mode="json"),
    }


@router.get("/scans/{scan_id}/issues/{issue_id}")
async def get_scan_issue(scan_id: str, issue_id: str):
    loaded = _issues_record_or_error(service.get(scan_id))
    if isinstance(loaded, JSONResponse):
        return loaded
    issue = _find_issue(loaded, issue_id)
    if issue is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "ISSUE_NOT_FOUND", "message": "Issue not found."}},
        )
    return {
        **issue_to_detail(issue, scan_id, loaded.issues),
        "screenshot_capture": loaded.screenshot_capture.model_dump(mode="json"),
    }


@router.get("/scans/{scan_id}/issues/{issue_id}/screenshot")
async def get_issue_screenshot(scan_id: str, issue_id: str):
    record = service.get(scan_id)
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    if record.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": "Issue screenshots are not available yet."}},
        )
    blob = service.issue_screenshots.get(scan_id, issue_id)
    if not blob:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCREENSHOT_NOT_FOUND", "message": "Screenshot not found."}},
        )
    data, content_type = blob
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"})


@router.get("/scans/{scan_id}/recommendations")
async def get_scan_recommendations(
    scan_id: str,
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    impact: str | None = Query(default=None),
    effort: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: str | None = Query(default=None),
    page_size: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    order: str | None = Query(default=None),
):
    loaded = _recommendations_record_or_error(service.get(scan_id))
    if isinstance(loaded, JSONResponse):
        return loaded
    items, pagination = query_recommendations(
        loaded.recommendations,
        {
            "category": category,
            "priority": priority,
            "impact": impact,
            "effort": effort,
            "status": status,
            "search": search,
            "page": page,
            "page_size": page_size,
            "sort": sort,
            "order": order,
        },
    )
    return {
        "scan_id": scan_id,
        "items": [recommendation_to_list_item(item) for item in items],
        "pagination": pagination,
        "summary": loaded.summary.model_dump(mode="json"),
        "analyzer_status": loaded.analyzer_status,
        "methodology": loaded.methodology or METHODOLOGY,
        "truncated": loaded.truncated,
    }


@router.get("/scans/{scan_id}/recommendations/{recommendation_id}")
async def get_scan_recommendation(scan_id: str, recommendation_id: str):
    record = service.get(scan_id)
    loaded = _recommendations_record_or_error(record)
    if isinstance(loaded, JSONResponse):
        return loaded
    item = next((row for row in loaded.recommendations if row.id == recommendation_id), None)
    if item is None or item.scan_id != scan_id:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "RECOMMENDATION_NOT_FOUND", "message": "Recommendation not found."}},
        )
    return recommendation_to_detail(item, loaded, scan_id, record.result if record else None)


@router.patch("/scans/{scan_id}/recommendations/{recommendation_id}")
async def patch_scan_recommendation(scan_id: str, recommendation_id: str, body: dict = Body(default_factory=dict)):
    status = str((body or {}).get("status") or "").strip().lower()
    extra = set((body or {}).keys()) - {"status"}
    if extra:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "INVALID_FIELD", "message": "Only status can be updated."}},
        )
    if status not in RECOMMENDATION_STATUSES:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "INVALID_STATUS", "message": "Status must be open, in_progress, completed, or dismissed."}},
        )
    updated = service.update_recommendation_status(scan_id, recommendation_id, status)
    if updated is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    if updated == "scan_failed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_FAILED", "message": "This scan did not complete."}},
        )
    if updated == "scan_not_ready":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": "Recommendations are not available yet."}},
        )
    if updated == "invalid_status":
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "INVALID_STATUS", "message": "Status must be open, in_progress, completed, or dismissed."}},
        )
    if updated == "not_found":
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "RECOMMENDATION_NOT_FOUND", "message": "Recommendation not found."}},
        )
    record = service.get(scan_id)
    loaded = _recommendations_record_or_error(record)
    if isinstance(loaded, JSONResponse):
        return loaded
    return recommendation_to_detail(updated, loaded, scan_id, record.result if record else None)


@router.get("/scans/{scan_id}/competitors")
async def list_scan_competitors(scan_id: str):
    try:
        record, items = _competitor_service().list(scan_id)
    except ScanError as exc:
        return _competitor_error(exc)
    cards = []
    for item in items:
        if item.scan_id != scan_id:
            continue
        cards.append(competitor_to_card(item, service.get(item.competitor_scan_id)))
    return {
        "scan_id": scan_id,
        "primary": {
            "url": record.normalized_url,
            "status": record.status,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        },
        "competitors": cards,
        "max_competitors": MAX_COMPETITORS,
        "limit_note": limit_note(),
        "remaining": max(0, MAX_COMPETITORS - len(cards)),
    }


@router.post("/scans/{scan_id}/competitors")
async def create_scan_competitor(scan_id: str, background_tasks: BackgroundTasks, body: dict = Body(default_factory=dict)):
    extra = set((body or {}).keys()) - {"name", "url"}
    if extra:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "INVALID_FIELD", "message": "Only name and URL can be submitted."}},
        )
    try:
        item, created = _competitor_service().add(scan_id, str((body or {}).get("name") or ""), str((body or {}).get("url") or ""))
    except ScanError as exc:
        return _competitor_error(exc)
    background_tasks.add_task(service.run, created.id)
    return JSONResponse(
        status_code=202,
        content={"competitor": competitor_to_card(item, created), "max_competitors": MAX_COMPETITORS},
    )


@router.get("/scans/{scan_id}/competitors/comparison")
async def get_scan_competitor_comparison(scan_id: str):
    try:
        record, items = _competitor_service().list(scan_id)
    except ScanError as exc:
        return _competitor_error(exc)
    pairs = []
    for item in items:
        if item.scan_id != scan_id:
            continue
        competitor_scan = service.get(item.competitor_scan_id)
        if competitor_scan is None:
            continue
        pairs.append((item, competitor_scan))
    return build_comparison(record, pairs)


@router.get("/scans/{scan_id}/competitors/page-comparison")
async def get_scan_page_comparison(
    scan_id: str,
    primary_page_id: str | None = Query(default=None),
    competitor_id: str | None = Query(default=None),
    competitor_page_id: str | None = Query(default=None),
):
    if not primary_page_id or not competitor_id:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "INVALID_PAGE", "message": "Select a primary page and a competitor page that were crawled."}},
        )
    try:
        record, _benchmark, competitor_scan = _competitor_service().get(scan_id, competitor_id)
    except ScanError as exc:
        return _competitor_error(exc)
    if competitor_scan is None or competitor_scan.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": "Comparison will update when the competitor scan completes."}},
        )
    if not competitor_page_id:
        primary_pages = pages_from_result(record.result)
        competitor_pages = pages_from_result(competitor_scan.result)
        left = next((page for page in primary_pages.items if page.id == primary_page_id and page.scan_id == scan_id), None)
        if left is None:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "PAGE_NOT_FOUND", "message": "Select pages that were actually crawled in each scan."}},
            )
        return {"suggestions": suggest_matches(left, competitor_pages.items)}
    try:
        return page_comparison_payload(
            primary=record,
            competitor=competitor_scan,
            primary_page_id=primary_page_id,
            competitor_page_id=competitor_page_id,
        )
    except KeyError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "PAGE_NOT_FOUND", "message": "Select pages that were actually crawled in each scan."}},
        )


@router.get("/scans/{scan_id}/competitors/{competitor_id}")
async def get_scan_competitor(scan_id: str, competitor_id: str):
    try:
        record, item, competitor_scan = _competitor_service().get(scan_id, competitor_id)
    except ScanError as exc:
        return _competitor_error(exc)
    return competitor_detail(item, record, competitor_scan)


@router.post("/scans/{scan_id}/competitors/{competitor_id}/rescan")
async def rescan_scan_competitor(scan_id: str, competitor_id: str, background_tasks: BackgroundTasks):
    try:
        item, created = _competitor_service().rescan(scan_id, competitor_id)
    except ScanError as exc:
        return _competitor_error(exc)
    background_tasks.add_task(service.run, created.id)
    return {"competitor": competitor_to_card(item, created)}


@router.delete("/scans/{scan_id}/competitors/{competitor_id}")
async def delete_scan_competitor(scan_id: str, competitor_id: str):
    try:
        item = _competitor_service().remove(scan_id, competitor_id)
    except ScanError as exc:
        return _competitor_error(exc)
    return {"removed": True, "id": item.id}


@router.get("/scans/{scan_id}/mobile")
async def get_scan_mobile(scan_id: str):
    record = service.get(scan_id)
    if record is not None and record.status == "completed":
        error = (record.result or {}).get("mobile_error")
        if error and not (record.result or {}).get("mobile"):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": error.get("code") or "MOBILE_NOT_AVAILABLE",
                        "message": error.get("message") or "Mobile analysis is not available for this scan.",
                    }
                },
            )
    payload = _module_payload(
        record,
        "mobile",
        "Mobile",
        extra=(
            "environment",
            "viewport",
            "navigation",
            "layout",
            "typography",
            "touch_targets",
            "forms",
            "images",
            "tables",
            "media",
            "overlays",
            "sticky_elements",
            "screenshots",
            "limitations",
            "findings",
            "severity_counts",
            "category_cards",
            "comparison",
            "overview",
        ),
    )
    if isinstance(payload, dict):
        payload["status"] = record.status
        payload["url"] = record.normalized_url
        if payload.get("findings") is None:
            payload["findings"] = payload.get("checks") or []
    return payload


@router.get("/scans/{scan_id}/cro")
async def get_scan_cro(scan_id: str):
    record = service.get(scan_id)
    if record is not None and record.status == "completed":
        error = (record.result or {}).get("cro_error")
        if error and not (record.result or {}).get("cro"):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": error.get("code") or "CRO_NOT_AVAILABLE",
                        "message": error.get("message") or "CRO analysis is not available for this scan.",
                    }
                },
            )
    payload = _module_payload(
        record,
        "cro",
        "CRO",
        extra=(
            "category_cards",
            "findings",
            "pages",
            "ctas",
            "forms",
            "conversion_paths",
            "methodology",
            "limitations",
            "screenshots",
            "score_note",
            "crawl_note",
            "viewports",
        ),
    )
    if isinstance(payload, dict):
        payload["status"] = record.status
        payload["url"] = record.normalized_url
        if payload.get("findings") is None:
            payload["findings"] = payload.get("checks") or []
        if payload.get("score") is None and not (record.result or {}).get("cro"):
            payload["narrative"] = payload.get("narrative") or "CRO analysis unavailable."
    return payload


@router.get("/scans/{scan_id}/cro/pages/{page_id}")
async def get_scan_cro_page(scan_id: str, page_id: str):
    record = service.get(scan_id)
    payload = _module_payload(
        record,
        "cro",
        "CRO",
        extra=("pages", "ctas", "forms", "conversion_paths", "findings", "checks", "screenshots", "methodology", "limitations"),
    )
    if not isinstance(payload, dict):
        return payload
    pages = payload.get("pages") or []
    page = next((item for item in pages if item.get("page_id") == page_id), None)
    if page is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "PAGE_NOT_FOUND", "message": "CRO results are not available for this page."}},
        )
    checks = [item for item in (payload.get("checks") or []) if item.get("page_id") == page_id]
    return {
        "scan_id": record.id,
        "page": page,
        "checks": checks,
        "ctas": [item for item in (payload.get("ctas") or []) if item.get("page_id") == page_id],
        "forms": [item for item in (payload.get("forms") or []) if item.get("page_id") == page_id],
        "conversion_paths": payload.get("conversion_paths") or [],
        "methodology": payload.get("methodology"),
        "limitations": payload.get("limitations") or [],
    }


@router.get("/scans/{scan_id}/trust")
async def get_scan_trust(scan_id: str):
    record = service.get(scan_id)
    if record is not None and record.status == "completed":
        error = (record.result or {}).get("trust_error")
        if error and not (record.result or {}).get("trust"):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": error.get("code") or "TRUST_NOT_AVAILABLE",
                        "message": error.get("message") or "Trust & Credibility analysis unavailable.",
                    }
                },
            )
    payload = _module_payload(
        record,
        "trust",
        "Trust",
        extra=(
            "category_cards",
            "findings",
            "pages",
            "signals",
            "gaps",
            "policies",
            "authors",
            "social_proof",
            "consistency",
            "security",
            "methodology",
            "limitations",
            "score_note",
            "crawl_note",
        ),
    )
    if isinstance(payload, dict):
        payload["status"] = record.status
        payload["url"] = record.normalized_url
        if payload.get("findings") is None:
            payload["findings"] = payload.get("checks") or []
        if payload.get("score") is None and not (record.result or {}).get("trust"):
            payload["narrative"] = payload.get("narrative") or "Trust & Credibility analysis unavailable."
    return payload


@router.get("/scans/{scan_id}/trust/pages/{page_id}")
async def get_scan_trust_page(scan_id: str, page_id: str):
    record = service.get(scan_id)
    payload = _module_payload(
        record,
        "trust",
        "Trust",
        extra=(
            "pages",
            "findings",
            "checks",
            "signals",
            "gaps",
            "policies",
            "authors",
            "social_proof",
            "consistency",
            "security",
            "methodology",
            "limitations",
        ),
    )
    if not isinstance(payload, dict):
        return payload
    pages = payload.get("pages") or []
    page = next((item for item in pages if item.get("page_id") == page_id), None)
    if page is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "PAGE_NOT_FOUND", "message": "Trust results are not available for this page."}},
        )
    checks = [item for item in (payload.get("checks") or []) if item.get("page_id") == page_id]
    return {
        "scan_id": record.id,
        "page": page,
        "checks": checks,
        "signals": [item for item in (payload.get("signals") or []) if item.get("page_id") == page_id],
        "gaps": [item for item in (payload.get("gaps") or []) if item.get("page_id") == page_id],
        "authors": [item for item in (payload.get("authors") or []) if item.get("page_id") == page_id],
        "social_proof": [item for item in (payload.get("social_proof") or []) if item.get("page_url") == page.get("url")],
        "consistency": payload.get("consistency") or [],
        "security": payload.get("security") or [],
        "policies": payload.get("policies") or [],
        "methodology": payload.get("methodology"),
        "limitations": payload.get("limitations") or [],
        "score_note": payload.get("score_note"),
        "crawl_note": payload.get("crawl_note"),
    }


def _score_record(record):
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    if record.status == "failed":
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "SCAN_FAILED",
                    "message": (record.error or {}).get("message") or "This scan did not complete.",
                }
            },
        )
    if record.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": "Health score is not available yet."}},
        )
    error = (record.result or {}).get("health_error")
    health = health_from_result(record.result)
    if health is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": (error or {}).get("code") if isinstance(error, dict) else "SCORE_NOT_AVAILABLE",
                    "message": (error or {}).get("message") if isinstance(error, dict) else "Health score unavailable.",
                }
            },
        )
    return health, record


@router.get("/scans/{scan_id}/score")
async def get_scan_score(scan_id: str):
    loaded = _score_record(service.get(scan_id))
    if not isinstance(loaded, tuple):
        return loaded
    health, record = loaded
    return score_response(record.id, health)


@router.get("/scans/{scan_id}/score/methodology")
async def get_scan_score_methodology(scan_id: str):
    record = service.get(scan_id)
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    health = health_from_result(record.result) if record.status == "completed" else None
    return methodology_response(record.id, health)


def _report_payload(scan_id: str):
    record = service.get(scan_id)
    if record is None:
        return None, JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    if record.status == "failed":
        return None, JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "SCAN_FAILED",
                    "message": (record.error or {}).get("message") or "This scan did not complete.",
                }
            },
        )
    if record.status != "completed":
        return None, JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": "The report is not available until the scan completes."}},
        )
    comparison = None
    try:
        _primary, items = _competitor_service().list(scan_id)
        pairs = []
        for item in items:
            if item.scan_id != scan_id:
                continue
            competitor_scan = service.get(item.competitor_scan_id)
            if competitor_scan is None:
                continue
            pairs.append((item, competitor_scan))
        if pairs:
            comparison = build_comparison(record, pairs)
    except ScanError:
        comparison = None
    try:
        return assemble_report(record, competitor_comparison=comparison), None
    except Exception:
        logger.exception("report_assembly_failed scan_id=%s", scan_id)
        return None, JSONResponse(
            status_code=500,
            content={"error": {"code": "REPORT_UNAVAILABLE", "message": REPORT_UNAVAILABLE}},
        )


@router.get("/scans/{scan_id}/report.pdf")
async def get_scan_report_pdf(scan_id: str):
    payload, error = _report_payload(scan_id)
    if error is not None:
        return error
    try:
        pdf_bytes = render_report_pdf(payload)
    except Exception:
        logger.exception("report_pdf_failed scan_id=%s", scan_id)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "REPORT_UNAVAILABLE", "message": REPORT_UNAVAILABLE}},
        )
    filename = report_pdf_filename(payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}',
            "Cache-Control": "no-store",
        },
    )


@router.get("/scans/{scan_id}/report")
async def get_scan_report(scan_id: str):
    payload, error = _report_payload(scan_id)
    if error is not None:
        return error
    return payload


@router.get("/scans/{scan_id}/uiux/screenshots/{viewport}")
async def get_uiux_screenshot(scan_id: str, viewport: str):
    record = service.get(scan_id)
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    if record.status == "failed":
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "SCAN_FAILED",
                    "message": (record.error or {}).get("message") or "This scan did not complete.",
                }
            },
        )
    if record.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": "UI/UX screenshots are not available yet."}},
        )
    if viewport not in all_known_viewports():
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCREENSHOT_NOT_FOUND", "message": "Screenshot not found."}},
        )
    data = service.screenshots.get(scan_id, viewport)
    if not data:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCREENSHOT_NOT_FOUND", "message": "Screenshot not found."}},
        )
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/scans/{scan_id}/mobile/screenshots/{name}")
async def get_mobile_screenshot(scan_id: str, name: str):
    record = service.get(scan_id)
    if record is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCAN_NOT_FOUND", "message": "Scan not found."}},
        )
    if record.status == "failed":
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "SCAN_FAILED",
                    "message": (record.error or {}).get("message") or "This scan did not complete.",
                }
            },
        )
    if record.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "SCAN_NOT_READY", "message": "Mobile screenshots are not available yet."}},
        )
    if not allowed_screenshot_key(name):
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCREENSHOT_NOT_FOUND", "message": "Screenshot not found."}},
        )
    data = service.screenshots.get(scan_id, name)
    if not data:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "SCREENSHOT_NOT_FOUND", "message": "Screenshot not found."}},
        )
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})
