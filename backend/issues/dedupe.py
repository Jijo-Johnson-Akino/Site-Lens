"""Deterministic intra-source finding deduplication.

Primary key: source + issue_key + normalized page URL + normalized location.

Different issue keys or sources are never merged.
"""

from __future__ import annotations

from typing import Any

from backend.issues.models import AffectedElement, IssueOccurrence
from backend.issues.normalize import stable_id
from backend.issues.priority import SEVERITY_RANK

STATUS_RANK = {
    "fail": 4,
    "warning": 3,
    "info": 2,
    "pass": 1,
    "not_applicable": 0,
}


def dedupe_key(finding: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(finding.get("source") or "unknown"),
        str(finding.get("issue_key") or "unknown"),
        str(finding.get("page_url") or ""),
        str(finding.get("location_key") or ""),
    )


def _worse_status(left: str, right: str) -> str:
    return left if STATUS_RANK.get(left, 0) >= STATUS_RANK.get(right, 0) else right


def _worse_severity(left: str, right: str) -> str:
    return left if SEVERITY_RANK.get(left, 0) >= SEVERITY_RANK.get(right, 0) else right


def _merge_evidence(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base or {})
    for key, value in (extra or {}).items():
        if key not in merged or merged[key] in (None, "", [], {}):
            merged[key] = value
    return merged


def merge_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge duplicate findings that share the same dedupe key."""
    buckets: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    order: list[tuple[str, str, str, str]] = []
    for finding in findings:
        key = dedupe_key(finding)
        existing = buckets.get(key)
        if existing is None:
            clone = dict(finding)
            clone["finding_ids"] = [finding.get("finding_id")]
            buckets[key] = clone
            order.append(key)
            continue
        existing["finding_ids"].append(finding.get("finding_id"))
        existing["status"] = _worse_status(existing.get("status") or "fail", finding.get("status") or "fail")
        existing["severity"] = _worse_severity(existing.get("severity") or "medium", finding.get("severity") or "medium")
        existing["affected_element_count"] = int(existing.get("affected_element_count") or 0) + int(
            finding.get("affected_element_count") or 0
        )
        existing["evidence"] = _merge_evidence(existing.get("evidence") or {}, finding.get("evidence") or {})
        if not existing.get("recommendation") and finding.get("recommendation"):
            existing["recommendation"] = finding.get("recommendation")
        if not existing.get("selector") and finding.get("selector"):
            existing["selector"] = finding.get("selector")
        if not existing.get("message") and finding.get("message"):
            existing["message"] = finding.get("message")
    return [buckets[key] for key in order]


def occurrence_from_finding(finding: dict[str, Any], scan_id: str) -> IssueOccurrence:
    location = finding.get("location_key") or ""
    occurrence_id = stable_id(
        "occ",
        scan_id,
        finding.get("source"),
        finding.get("issue_key"),
        finding.get("page_url"),
        location,
    )
    elements: list[AffectedElement] = []
    if finding.get("selector") or finding.get("resource_url") or finding.get("schema_entity_id"):
        width = None
        evidence = finding.get("evidence") or {}
        if isinstance(evidence.get("document_width"), (int, float)):
            width = evidence.get("document_width")
        elements.append(
            AffectedElement(
                selector=finding.get("selector"),
                resource_url=finding.get("resource_url"),
                schema_entity_id=finding.get("schema_entity_id"),
                viewport=finding.get("viewport"),
                snippet=(finding.get("evidence") or {}).get("detected") if isinstance(finding.get("evidence"), dict) else None,
                width=width,
            )
        )
    return IssueOccurrence(
        occurrence_id=occurrence_id,
        finding_ids=[item for item in (finding.get("finding_ids") or [finding.get("finding_id")]) if item],
        page_url=finding.get("page_url") or "",
        selector=finding.get("selector"),
        resource_url=finding.get("resource_url"),
        schema_entity_id=finding.get("schema_entity_id"),
        viewport=finding.get("viewport"),
        affected_element_count=int(finding.get("affected_element_count") or 0),
        evidence=finding.get("evidence") or {},
        check_status=finding.get("status") or "fail",
        severity=finding.get("severity") or "medium",
        message=finding.get("message") or "",
        recommendation=finding.get("recommendation"),
        wcag_reference=finding.get("wcag_reference"),
        details=finding.get("details") or {},
        affected_elements=elements,
    )
