"""Normalize analyzer findings into a common internal shape.

Malformed findings are skipped. This module never invents new checks.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from backend.analyzers.uiux.sanitizer import sanitize_selector, sanitize_text
from backend.issues.config import (
    MAX_EVIDENCE_SIZE,
    SOURCE_TO_CATEGORY,
    SOURCE_VALUES,
    SUBCATEGORY_LABELS,
)
from backend.issues.keys import issue_key_for
from backend.issues.urls import normalize_page_url

logger = logging.getLogger("sitebench.issues")

SEVERITY_ALIASES = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "info": "info",
    "informational": "info",
    "serious": "high",
    "moderate": "medium",
    "minor": "low",
    "warning": "medium",
}

STATUS_ALIASES = {
    "pass": "pass",
    "passed": "pass",
    "ok": "pass",
    "warning": "warning",
    "warn": "warning",
    "fail": "fail",
    "failed": "fail",
    "failure": "fail",
    "not_applicable": "not_applicable",
    "n/a": "not_applicable",
    "na": "not_applicable",
    "inapplicable": "not_applicable",
    "info": "info",
    "informational": "info",
}

UNSAFE_EVIDENCE_KEYS = {
    "html",
    "html_source",
    "innerhtml",
    "outerhtml",
    "markup",
    "raw_html",
    "body",
    "document",
    "stack",
    "traceback",
    "exception",
}


def stable_id(prefix: str, *parts: Any) -> str:
    material = "|".join("" if part is None else str(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def normalize_source(value: str | None) -> str:
    raw = (value or "").strip().lower().replace("/", "").replace(" ", "_")
    aliases = {
        "ui_ux": "uiux",
        "ux": "uiux",
        "a11y": "accessibility",
        "perf": "performance",
        "schema": "structured_data",
        "structureddata": "structured_data",
    }
    mapped = aliases.get(raw, raw)
    if mapped in SOURCE_VALUES:
        return mapped
    if mapped:
        logger.info("issues_unknown_source source=%s", mapped[:40])
    return "unknown"


def normalize_severity(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return SEVERITY_ALIASES.get(raw, "medium")


def normalize_status(value: Any) -> str:
    raw = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return STATUS_ALIASES.get(raw, "fail" if raw else "fail")


def normalize_selector(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = " ".join(str(value).split())
    return sanitize_selector(collapsed)


def subcategory_for(group: str | None) -> str | None:
    if not group:
        return None
    key = str(group).strip()
    if not key:
        return None
    return SUBCATEGORY_LABELS.get(key, key.replace("_", " ").title())


def _clip_value(value: Any, remaining: int) -> Any:
    if remaining <= 0:
        return None
    if isinstance(value, str):
        cleaned = sanitize_text(value, limit=min(240, remaining)) or ""
        return cleaned[:remaining]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        clipped: list[Any] = []
        for item in value[:12]:
            piece = _clip_value(item, remaining)
            if piece is None:
                break
            clipped.append(piece)
            remaining -= len(json.dumps(piece, default=str))
            if remaining <= 0:
                break
        return clipped
    if isinstance(value, dict):
        return clip_evidence(value, remaining)
    return str(value)[: min(120, remaining)]


def clip_evidence(evidence: dict[str, Any] | None, max_bytes: int = MAX_EVIDENCE_SIZE) -> dict[str, Any]:
    if not evidence:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in evidence.items():
        name = str(key)
        if name.lower() in UNSAFE_EVIDENCE_KEYS:
            continue
        if not name.isidentifier() and not all(ch.isalnum() or ch in "._-" for ch in name):
            continue
        cleaned[name] = value
    encoded = json.dumps(cleaned, default=str)
    if len(encoded) <= max_bytes:
        return cleaned
    clipped: dict[str, Any] = {}
    remaining = max_bytes
    for key, value in cleaned.items():
        piece = _clip_value(value, remaining)
        if piece is None:
            continue
        clipped[key] = piece
        remaining = max_bytes - len(json.dumps(clipped, default=str))
        if remaining <= 80:
            break
    return clipped


def build_evidence(source: str, raw: dict[str, Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    detected = raw.get("detected")
    if detected:
        evidence["detected"] = sanitize_text(str(detected), limit=240)
    details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
    for key in (
        "title_length",
        "word_count",
        "javascript_bytes",
        "js_bytes",
        "image_bytes",
        "bytes",
        "overflow_px",
        "document_width",
        "viewport_width",
        "viewport_height",
        "axe_rule",
        "impact",
        "schema_type",
        "missing_property",
        "property",
        "threshold",
        "similarity",
        "kind",
        "boilerplate_words",
        "visible_words",
        "ratio",
    ):
        if key in details and details[key] is not None:
            evidence[key] = details[key]
        elif raw.get(key) is not None and key not in evidence:
            evidence[key] = raw.get(key)

    if source == "accessibility":
        if raw.get("axe_rule_id"):
            evidence["axe_rule"] = raw.get("axe_rule_id")
        if details.get("impact"):
            evidence["impact"] = details.get("impact")
        if raw.get("wcag_reference"):
            evidence["wcag_reference"] = raw.get("wcag_reference")
    if source == "performance":
        if raw.get("resource_url"):
            evidence["resource_url"] = sanitize_text(str(raw.get("resource_url")), limit=200)
        if raw.get("affected_element_count"):
            evidence["affected_element_count"] = raw.get("affected_element_count")
    if source == "mobile":
        if raw.get("viewport"):
            evidence["viewport"] = raw.get("viewport")
        if raw.get("measured_value") is not None:
            evidence["measured_value"] = raw.get("measured_value")
        if raw.get("expected_value") is not None:
            evidence["expected_value"] = raw.get("expected_value")
    if source == "structured_data":
        if raw.get("schema_type"):
            evidence["schema_type"] = raw.get("schema_type")
        if raw.get("property"):
            evidence["missing_property"] = raw.get("property")
        if raw.get("affected_entity"):
            evidence["schema_entity_id"] = raw.get("affected_entity")
    if source == "content" and raw.get("affected_element_count"):
        evidence["affected_element_count"] = raw.get("affected_element_count")
    if source == "uiux" and raw.get("viewport"):
        evidence["viewport"] = raw.get("viewport")
    if source == "cro":
        if raw.get("viewport"):
            evidence["viewport"] = raw.get("viewport")
        if raw.get("detected"):
            evidence.setdefault("detected", sanitize_text(str(raw.get("detected")), limit=240))
        details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
        evidence_block = raw.get("evidence") if isinstance(raw.get("evidence"), dict) else {}
        for key, value in {**details, **evidence_block}.items():
            if key not in evidence and value is not None:
                evidence[key] = value
    if source == "trust":
        if raw.get("detected"):
            evidence.setdefault("detected", sanitize_text(str(raw.get("detected")), limit=240))
        details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
        evidence_block = raw.get("evidence") if isinstance(raw.get("evidence"), dict) else {}
        for key, value in {**details, **evidence_block}.items():
            if key not in evidence and value is not None:
                evidence[key] = value
    if source == "seo":
        if "title" in (raw.get("name") or "").lower() and detected:
            evidence.setdefault("title", sanitize_text(str(detected), limit=160))
        if "meta description" in (raw.get("name") or "").lower():
            evidence.setdefault("meta_description", sanitize_text(str(detected or "Missing"), limit=160))
    return clip_evidence(evidence)


def location_key(
    *,
    selector: str | None,
    resource_url: str | None,
    schema_entity_id: str | None,
    viewport: str | None,
) -> str:
    parts: list[str] = []
    if viewport:
        parts.append(f"vp={viewport}")
    if selector:
        parts.append(f"sel={selector}")
    if resource_url:
        parts.append(f"res={resource_url}")
    if schema_entity_id:
        parts.append(f"ent={schema_entity_id}")
    return "|".join(parts)


def normalize_finding(
    raw: Any,
    *,
    source: str,
    scan_id: str,
    fallback_page: str | None,
    created_at: str | None,
) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        logger.info("issues_malformed_finding source=%s reason=not_object", source)
        return None
    check_id = str(raw.get("check_id") or "").strip()
    name = str(raw.get("name") or "").strip()
    if not check_id and not name:
        logger.info("issues_malformed_finding source=%s reason=missing_identity", source)
        return None
    source_norm = normalize_source(source)
    issue_key = issue_key_for(source_norm, check_id or None)
    page_url = normalize_page_url(raw.get("page_url"), fallback_page)
    selector = normalize_selector(raw.get("selector") or raw.get("affected_element"))
    resource_url = sanitize_text(raw.get("resource_url"), limit=200) if raw.get("resource_url") else None
    schema_entity_id = sanitize_text(str(raw.get("affected_entity")), limit=120) if raw.get("affected_entity") else None
    viewport = str(raw.get("viewport") or "").strip() or None
    try:
        element_count = int(raw.get("affected_element_count") or 0)
    except (TypeError, ValueError):
        element_count = 0
    if element_count < 0:
        element_count = 0
    if element_count == 0 and selector:
        element_count = 1
    status = normalize_status(raw.get("status"))
    severity = normalize_severity(raw.get("severity"))
    source_severity = str(raw.get("severity") or "").strip() or None
    recommendation = raw.get("recommendation")
    if recommendation is not None:
        recommendation = sanitize_text(str(recommendation), limit=400)
    message = sanitize_text(str(raw.get("message") or name or "Finding"), limit=400) or name
    finding_id = stable_id("finding", scan_id, source_norm, check_id, page_url, location_key(selector=selector, resource_url=resource_url, schema_entity_id=schema_entity_id, viewport=viewport), name)
    details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
    safe_details = clip_evidence({k: v for k, v in details.items() if k.lower() not in UNSAFE_EVIDENCE_KEYS})
    return {
        "finding_id": finding_id,
        "issue_key": issue_key,
        "source": source_norm,
        "category": SOURCE_TO_CATEGORY.get(source_norm, "Unknown"),
        "subcategory": subcategory_for(raw.get("group")),
        "check_id": check_id or "UNKNOWN",
        "name": name or issue_key,
        "status": status,
        "severity": severity,
        "source_severity": source_severity,
        "score": raw.get("score"),
        "message": message,
        "recommendation": recommendation,
        "page_url": page_url,
        "selector": selector,
        "resource_url": resource_url,
        "schema_entity_id": schema_entity_id,
        "viewport": viewport,
        "affected_element_count": element_count,
        "wcag_reference": raw.get("wcag_reference"),
        "evidence": build_evidence(source_norm, raw),
        "created_at": created_at,
        "details": safe_details,
        "location_key": location_key(
            selector=selector,
            resource_url=resource_url,
            schema_entity_id=schema_entity_id,
            viewport=viewport,
        ),
        "group": raw.get("group"),
        "axe_rule_id": raw.get("axe_rule_id"),
        "why": sanitize_text(raw.get("why"), limit=400) if raw.get("why") else None,
    }
