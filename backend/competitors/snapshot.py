"""Extract comparable metrics from a stored scan. Does not rerun analyzers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.architecture.engine import build_architecture, page_type_distribution, summary_from_graph
from backend.competitors.config import ANALYZER_CATEGORIES, METHODOLOGY_VERSION, methodology_snapshot
from backend.pages.engine import payload_from_result as pages_from_result
from backend.schemas.scan import ScanRecord


def _iso(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _module(result: dict[str, Any], key: str) -> dict[str, Any] | None:
    payload = result.get(key)
    return payload if isinstance(payload, dict) else None


def _analyzer_status(result: dict[str, Any], key: str) -> str:
    if _module(result, key):
        return "completed"
    error = result.get(f"{key}_error")
    if isinstance(error, dict) and error:
        return "failed"
    issues = result.get("issues") if isinstance(result.get("issues"), dict) else {}
    status = (issues.get("analyzer_status") or {}).get(key)
    if status in {"completed", "failed", "missing"}:
        return status
    return "missing"


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _check_summary(module: dict[str, Any] | None) -> dict[str, int | None]:
    if not module:
        return {"passed": None, "warnings": None, "failed": None, "not_applicable": None, "available_checks": None}
    summary = module.get("summary") if isinstance(module.get("summary"), dict) else {}
    checks = module.get("checks") if isinstance(module.get("checks"), list) else []
    available = len(checks)
    if not available:
        parts = [_int(summary.get("passed")), _int(summary.get("warnings")), _int(summary.get("failed")), _int(summary.get("not_applicable"))]
        if any(part is not None for part in parts):
            available = sum(part or 0 for part in parts)
    return {
        "passed": _int(summary.get("passed")),
        "warnings": _int(summary.get("warnings")),
        "failed": _int(summary.get("failed")),
        "not_applicable": _int(summary.get("not_applicable")),
        "available_checks": available or None,
    }


def _issue_counts(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("issues") if isinstance(result.get("issues"), dict) else None
    if not payload or not isinstance(payload.get("issues"), list):
        return {"available": False}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    by_key: dict[str, dict[str, Any]] = {}
    for issue in payload.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        key = str(issue.get("issue_key") or "").strip()
        if not key:
            continue
        count = _int(issue.get("affected_page_count")) or len(issue.get("occurrences") or []) or _int(issue.get("affected_element_count")) or 1
        entry = by_key.setdefault(
            key,
            {
                "issue_key": key,
                "title": issue.get("title") or key,
                "category": issue.get("category") or issue.get("source") or "",
                "source": issue.get("source") or "",
                "count": 0,
            },
        )
        entry["count"] += count
        if not entry.get("title") or entry["title"] == key:
            entry["title"] = issue.get("title") or key
    recs = result.get("recommendations") if isinstance(result.get("recommendations"), dict) else None
    rec_summary = recs.get("summary") if recs and isinstance(recs.get("summary"), dict) else {}
    return {
        "available": True,
        "total": _int(summary.get("total")),
        "occurrences": _int(summary.get("occurrences")),
        "failures": _int(summary.get("failures")),
        "warnings": _int(summary.get("warnings")),
        "info": _int(summary.get("info")),
        "critical": _int(summary.get("critical")) or _int((summary.get("by_severity") or {}).get("critical")),
        "high": _int(summary.get("high")) or _int((summary.get("by_severity") or {}).get("high")),
        "medium": _int(summary.get("medium")) or _int((summary.get("by_severity") or {}).get("medium")),
        "low": _int(summary.get("low")) or _int((summary.get("by_severity") or {}).get("low")),
        "by_severity": dict(summary.get("by_severity") or {}),
        "by_category": dict(summary.get("by_category") or {}),
        "by_source": dict(summary.get("by_source") or {}),
        "by_key": by_key,
        "recommendations_total": _int(rec_summary.get("total")) if recs else None,
        "recommendations_by_category": dict(rec_summary.get("by_category") or {}) if recs else {},
        "recommendations_available": bool(recs),
    }


def _pages(result: dict[str, Any]) -> dict[str, Any]:
    payload = pages_from_result(result)
    summary = payload.summary
    crawled = [page for page in payload.items if page.crawl_status == "crawled"]
    words = [page.word_count for page in crawled if isinstance(page.word_count, int)]
    types: dict[str, int] = {}
    for page in payload.items:
        kind = (page.page_type or "unknown").lower() or "unknown"
        types[kind] = types.get(kind, 0) + 1
    return {
        "available": bool(payload.items) or bool(summary.discovered),
        "discovered": summary.discovered,
        "crawled": summary.crawled,
        "failed": summary.failed,
        "skipped": summary.skipped,
        "max_depth_reached": summary.max_depth_reached,
        "max_pages": summary.max_pages or payload.limits.get("max_pages"),
        "max_depth": summary.max_depth or payload.limits.get("max_depth"),
        "page_limit_reached": summary.page_limit_reached,
        "depth_limit_reached": summary.depth_limit_reached,
        "average_word_count": round(sum(words) / len(words), 1) if words else None,
        "page_type_distribution": types,
        "pages": [
            {
                "id": page.id,
                "url": page.url,
                "normalized_url": page.normalized_url,
                "title": page.title,
                "page_type": page.page_type,
                "page_type_label": page.page_type_label,
                "crawl_status": page.crawl_status,
                "http_status": page.http_status,
                "word_count": page.word_count,
                "issue_count": page.issue_count,
                "is_seed": page.is_seed,
                "depth": page.depth,
            }
            for page in payload.items[:200]
        ],
    }


def _architecture(result: dict[str, Any]) -> dict[str, Any]:
    pages = result.get("pages")
    if not isinstance(pages, dict):
        return {"available": False}
    graph = build_architecture(result)
    summary = summary_from_graph(graph)
    return {
        "available": True,
        **summary,
        "page_type_distribution": page_type_distribution(graph),
    }


def _performance(result: dict[str, Any]) -> dict[str, Any]:
    module = _module(result, "performance")
    status = _analyzer_status(result, "performance")
    if not module or status != "completed":
        return {"available": False, "status": status}
    timing = module.get("timing") if isinstance(module.get("timing"), dict) else {}
    vitals = module.get("vitals") if isinstance(module.get("vitals"), dict) else {}
    resources = module.get("resources") if isinstance(module.get("resources"), dict) else {}
    environment = module.get("environment") if isinstance(module.get("environment"), dict) else {}

    def vital(name: str) -> dict[str, Any]:
        raw = vitals.get(name) if isinstance(vitals.get(name), dict) else {}
        value = _num(raw.get("value"))
        return {
            "value": value,
            "status": raw.get("status") or ("unavailable" if value is None else None),
            "unit": raw.get("unit"),
            "available": value is not None,
        }

    return {
        "available": True,
        "status": status,
        "score": _int(module.get("score")),
        "ttfb_ms": _num(timing.get("ttfb_ms")),
        "load_event_ms": _num(timing.get("load_event_ms")),
        "dom_content_loaded_ms": _num(timing.get("dom_content_loaded_ms")),
        "lcp": vital("lcp"),
        "cls": vital("cls"),
        "inp": vital("inp"),
        "resource_bytes": _int(resources.get("resource_bytes")) or _int(resources.get("transfer_bytes")),
        "transfer_bytes": _int(resources.get("transfer_bytes")),
        "total_requests": _int(resources.get("total_requests")),
        "environment": {
            "browser": environment.get("browser"),
            "browser_version": environment.get("browser_version"),
            "viewport": environment.get("viewport"),
            "viewport_name": environment.get("viewport_name"),
            "network_profile": environment.get("network_profile"),
            "cache_mode": environment.get("cache_mode"),
        },
    }


def _seo_signals(result: dict[str, Any]) -> dict[str, Any]:
    module = _module(result, "seo")
    if not module:
        return {"available": False}
    html = result.get("html") if isinstance(result.get("html"), dict) else {}
    robots = result.get("robots_txt") if isinstance(result.get("robots_txt"), dict) else {}
    sitemap = result.get("sitemap") if isinstance(result.get("sitemap"), dict) else {}
    indexable = module.get("indexable") if isinstance(module.get("indexable"), dict) else {}
    return {
        "available": True,
        "title_present": bool(html.get("title")),
        "meta_description_present": bool(html.get("meta_description")),
        "h1_count": _int(html.get("h1_count")),
        "canonical_present": bool(html.get("canonical")),
        "robots_txt_exists": robots.get("exists") if "exists" in robots else None,
        "sitemap_exists": sitemap.get("exists") if "exists" in sitemap else None,
        "indexable": indexable.get("indexable") if "indexable" in indexable else None,
    }


def _probe_bool(module: dict[str, Any] | None, check_id: str) -> bool | None:
    if not module:
        return None
    for check in module.get("checks") or []:
        if isinstance(check, dict) and check.get("check_id") == check_id:
            status = check.get("status")
            if status == "pass":
                return True
            if status in {"fail", "warning"}:
                return False
            return None
    return None


def snapshot_from_record(
    record: ScanRecord,
    *,
    column_id: str,
    label: str,
    role: str = "competitor",
) -> dict[str, Any]:
    result = record.result if isinstance(record.result, dict) else {}
    stored_method = result.get("methodology") if isinstance(result.get("methodology"), dict) else {}
    methodology = {**methodology_snapshot(), **stored_method}
    categories: dict[str, Any] = {}
    for key, label_name in ANALYZER_CATEGORIES:
        module = _module(result, key)
        status = _analyzer_status(result, key)
        summary = _check_summary(module)
        issues = result.get("issues") if isinstance(result.get("issues"), dict) else {}
        by_source = (issues.get("summary") or {}).get("by_source") if isinstance(issues.get("summary"), dict) else {}
        categories[key] = {
            "id": key,
            "label": label_name,
            "available": bool(module) and status == "completed",
            "status": status,
            "score": _int(module.get("score")) if module and status == "completed" else None,
            "available_checks": summary.get("available_checks") if module else None,
            "passed": summary.get("passed"),
            "failed": summary.get("failed"),
            "warnings": summary.get("warnings"),
            "issue_count": _int((by_source or {}).get(key)),
        }
    cro = _module(result, "cro")
    if cro:
        categories["cro"] = {
            "id": "cro",
            "label": "CRO",
            "available": True,
            "status": "completed",
            "score": _int(cro.get("score")),
            "available_checks": len(cro.get("checks") or []) if isinstance(cro.get("checks"), list) else None,
            "issue_count": None,
        }
    trust = _module(result, "trust")
    if trust:
        categories["trust"] = {
            "id": "trust",
            "label": "Trust",
            "available": True,
            "status": "completed",
            "score": _int(trust.get("score")),
            "available_checks": len(trust.get("checks") or []) if isinstance(trust.get("checks"), list) else None,
            "issue_count": None,
        }
    screenshots = []
    uiux = _module(result, "uiux")
    if uiux:
        for shot in uiux.get("screenshots") or []:
            if isinstance(shot, dict) and shot.get("url"):
                screenshots.append(
                    {
                        "viewport": shot.get("viewport"),
                        "width": shot.get("width"),
                        "height": shot.get("height"),
                        "url": shot.get("url"),
                    }
                )
    error = record.error if isinstance(record.error, dict) else None
    return {
        "column_id": column_id,
        "role": role,
        "label": label,
        "scan_id": record.id,
        "url": record.url,
        "normalized_url": record.normalized_url,
        "status": record.status,
        "progress": record.progress if record.status in {"queued", "running"} else None,
        "current_step": record.current_step if record.status == "running" else None,
        "created_at": _iso(record.created_at),
        "started_at": _iso(record.started_at),
        "completed_at": _iso(record.completed_at),
        "error": {"code": error.get("code"), "message": error.get("message")} if error else None,
        "methodology": methodology,
        "categories": categories,
        "issues": _issue_counts(result) if record.status == "completed" else {"available": False},
        "pages": _pages(result) if record.status == "completed" or result.get("pages") else {"available": False},
        "architecture": _architecture(result) if record.status == "completed" else {"available": False},
        "performance": _performance(result) if record.status == "completed" else {"available": False, "status": _analyzer_status(result, "performance")},
        "seo_signals": _seo_signals(result) if record.status == "completed" else {"available": False},
        "aeo_signals": {
            "available": bool(_module(result, "aeo")),
            "organization": _probe_bool(_module(result, "aeo"), "AEO-ENTITY-002"),
            "faq": _probe_bool(_module(result, "aeo"), "AEO-QUESTION-002"),
        }
        if record.status == "completed"
        else {"available": False},
        "schema_signals": {
            "available": bool(_module(result, "structured_data")),
            "jsonld_present": _probe_bool(_module(result, "structured_data"), "SCHEMA-DETECT-001")
            or _probe_bool(_module(result, "aeo"), "AEO-JSON-001"),
        }
        if record.status == "completed"
        else {"available": False},
        "screenshots": screenshots,
        "http": result.get("http") if isinstance(result.get("http"), dict) else {},
        "html": result.get("html") if isinstance(result.get("html"), dict) else {},
        "website": result.get("website") if isinstance(result.get("website"), dict) else {},
        "methodology_version": methodology.get("version") or METHODOLOGY_VERSION,
    }
