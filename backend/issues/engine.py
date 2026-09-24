"""Aggregate existing analyzer findings into unified issues.

Does not re-run analyzers, recrawl, or invent findings.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from backend.issues.config import (
    ACTIONABLE_STATUSES,
    CATEGORY_VALUES,
    MAX_FINDINGS_PER_ANALYZER,
    MAX_ISSUES_PER_SCAN,
    PRIORITIES,
    SEVERITIES,
    SOURCE_HREF,
    SOURCE_LABELS,
    SOURCE_TO_CATEGORY,
    SOURCE_TO_ERROR_KEY,
    SOURCE_TO_PAYLOAD_KEY,
    SOURCE_VALUES,
)
from backend.issues.dedupe import merge_findings, occurrence_from_finding
from backend.issues.grouping import group_ids
from backend.issues.media import attach_snippets, visual_kind_for
from backend.issues.models import IssueSummary, IssuesPayload, ScreenshotCaptureSummary, UnifiedIssue
from backend.issues.normalize import normalize_finding, stable_id
from backend.issues.priority import SEVERITY_RANK, calculate_priority
from backend.issues.related import related_keys_for
from backend.issues.urls import normalize_page_url

logger = logging.getLogger("sitebench.issues")

STATUS_RANK = {
    "fail": 4,
    "warning": 3,
    "info": 2,
    "pass": 1,
    "not_applicable": 0,
}


def analyzer_status_map(result: dict[str, Any] | None) -> dict[str, str]:
    payload = result or {}
    statuses: dict[str, str] = {}
    for source in SOURCE_VALUES:
        data = payload.get(SOURCE_TO_PAYLOAD_KEY[source])
        error = payload.get(SOURCE_TO_ERROR_KEY[source])
        if isinstance(data, dict):
            statuses[source] = "completed"
        elif error:
            statuses[source] = "failed"
        else:
            statuses[source] = "missing"
    return statuses


def _primary_page(result: dict[str, Any] | None) -> str:
    payload = result or {}
    website = payload.get("website") or {}
    return normalize_page_url(website.get("final_url") or website.get("url") or payload.get("url"))


def _extract_checks(payload: dict[str, Any]) -> list[Any]:
    checks = payload.get("checks")
    if isinstance(checks, list):
        return checks
    findings = payload.get("findings")
    if isinstance(findings, list):
        return findings
    return []


def _finding_rank(finding: dict[str, Any]) -> tuple[int, int, int]:
    return (
        SEVERITY_RANK.get(finding.get("severity") or "medium", 0),
        STATUS_RANK.get(finding.get("status") or "fail", 0),
        int(finding.get("affected_element_count") or 0),
    )


def collect_findings(
    result: dict[str, Any] | None,
    *,
    scan_id: str,
    created_at: str | None,
) -> tuple[list[dict[str, Any]], bool]:
    payload = result or {}
    primary = _primary_page(payload)
    collected: list[dict[str, Any]] = []
    truncated = False
    for source in SOURCE_VALUES:
        analyzer = payload.get(SOURCE_TO_PAYLOAD_KEY[source])
        if not isinstance(analyzer, dict):
            continue
        raw_items = _extract_checks(analyzer)
        normalized: list[dict[str, Any]] = []
        for raw in raw_items:
            try:
                item = normalize_finding(
                    raw,
                    source=source,
                    scan_id=scan_id,
                    fallback_page=primary,
                    created_at=created_at,
                )
            except Exception:
                logger.info("issues_malformed_finding source=%s reason=normalize_error", source)
                continue
            if item is None:
                continue
            normalized.append(item)
        if len(normalized) > MAX_FINDINGS_PER_ANALYZER:
            truncated = True
            normalized.sort(key=_finding_rank, reverse=True)
            normalized = normalized[:MAX_FINDINGS_PER_ANALYZER]
            logger.info(
                "issues_truncated source=%s kept=%s",
                source,
                MAX_FINDINGS_PER_ANALYZER,
            )
        collected.extend(normalized)
    return collected, truncated


def _group_key(finding: dict[str, Any]) -> tuple[str, str]:
    return (str(finding.get("source") or "unknown"), str(finding.get("issue_key") or "unknown"))


def _build_grouped_issue(
    findings: list[dict[str, Any]],
    *,
    scan_id: str,
    primary_page: str,
    created_at: str | None,
) -> UnifiedIssue:
    head = findings[0]
    source = head.get("source") or "unknown"
    issue_key = head.get("issue_key") or f"{source}.unknown"
    issue_id = stable_id("issue", scan_id, source, issue_key)
    occurrences = [occurrence_from_finding(item, scan_id) for item in findings]
    pages: list[str] = []
    for item in findings:
        page = item.get("page_url") or ""
        if page and page not in pages:
            pages.append(page)
    element_count = sum(int(item.get("affected_element_count") or 0) for item in findings)
    worst = head
    for item in findings:
        if STATUS_RANK.get(item.get("status") or "", 0) > STATUS_RANK.get(worst.get("status") or "", 0):
            worst = item
        elif STATUS_RANK.get(item.get("status") or "", 0) == STATUS_RANK.get(worst.get("status") or "", 0):
            if SEVERITY_RANK.get(item.get("severity") or "", 0) > SEVERITY_RANK.get(worst.get("severity") or "", 0):
                worst = item
    recommendation = next((item.get("recommendation") for item in findings if item.get("recommendation")), None)
    evidence = dict(worst.get("evidence") or {})
    if len(pages) > 1:
        evidence["affected_pages"] = pages
    grouped = {
        **worst,
        "pages": pages,
        "page_url": pages[0] if pages else worst.get("page_url"),
        "affected_element_count": element_count,
        "status": worst.get("status"),
        "evidence": evidence,
    }
    priority_score, priority = calculate_priority(
        grouped,
        affected_page_count=max(1, len(pages)),
        affected_element_count=element_count,
        primary_page=primary_page,
    )
    created = head.get("created_at") or created_at
    return UnifiedIssue(
        issue_id=issue_id,
        issue_key=issue_key,
        source=source,
        analyzer=SOURCE_LABELS.get(source, "Unknown Analyzer"),
        category=SOURCE_TO_CATEGORY.get(source, head.get("category") or "Unknown"),
        subcategory=head.get("subcategory"),
        check_id=head.get("check_id") or "UNKNOWN",
        title=head.get("name") or issue_key,
        description=worst.get("message") or head.get("message") or "",
        recommendation=recommendation,
        status="open",
        check_status=worst.get("status") or "fail",
        severity=worst.get("severity") or "medium",
        source_severity=worst.get("source_severity"),
        priority=priority,
        priority_score=priority_score,
        score=worst.get("score"),
        page_url=pages[0] if pages else None,
        selector=worst.get("selector"),
        resource_url=worst.get("resource_url"),
        schema_entity_id=worst.get("schema_entity_id"),
        viewport=worst.get("viewport"),
        affected_page_count=len(pages),
        affected_element_count=element_count,
        pages=pages,
        evidence=evidence,
        wcag_reference=worst.get("wcag_reference"),
        related_issue_ids=[],
        occurrences=occurrences,
        source_href=SOURCE_HREF.get(source),
        first_seen_scan_id=scan_id,
        last_seen_scan_id=scan_id,
        created_at=created,
        updated_at=created,
        details={
            "check_id": head.get("check_id"),
            "finding_ids": [fid for item in findings for fid in (item.get("finding_ids") or [item.get("finding_id")]) if fid],
            "occurrence_count": len(occurrences),
            "why": worst.get("why"),
        },
    )


def _attach_related(issues: list[UnifiedIssue]) -> None:
    by_key: dict[str, list[UnifiedIssue]] = defaultdict(list)
    for issue in issues:
        by_key[issue.issue_key].append(issue)
    for issue in issues:
        related: list[str] = []
        for other_key in related_keys_for(issue.issue_key):
            for other in by_key.get(other_key, []):
                if other.issue_id != issue.issue_id and other.issue_id not in related:
                    related.append(other.issue_id)
        issue.related_issue_ids = related


def summarize_issues(
    issues: list[UnifiedIssue],
    *,
    actionable_only: bool = True,
) -> IssueSummary:
    selected = [item for item in issues if (item.check_status in ACTIONABLE_STATUSES)] if actionable_only else list(issues)
    by_category = {label: 0 for label in CATEGORY_VALUES}
    by_priority = {label: 0 for label in PRIORITIES}
    by_severity = {label: 0 for label in SEVERITIES}
    by_source = {label: 0 for label in SOURCE_VALUES}
    by_page: dict[str, int] = {}
    failures = warnings = info = passed = 0
    occurrences = 0
    keys: set[str] = set()
    for issue in selected:
        by_category[issue.category] = by_category.get(issue.category, 0) + 1
        by_priority[issue.priority] = by_priority.get(issue.priority, 0) + 1
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
        by_source[issue.source] = by_source.get(issue.source, 0) + 1
        keys.add(issue.issue_key)
        occurrences += max(1, len(issue.occurrences) or issue.affected_page_count)
        if issue.check_status == "fail":
            failures += 1
        elif issue.check_status == "warning":
            warnings += 1
        elif issue.check_status == "info":
            info += 1
        elif issue.check_status == "pass":
            passed += 1
        for page in issue.pages:
            by_page[page] = by_page.get(page, 0) + 1
    return IssueSummary(
        total=len(selected),
        occurrences=occurrences,
        issue_types=len(keys),
        failures=failures,
        warnings=warnings,
        info=info,
        passed=passed,
        critical=by_priority.get("critical", 0),
        high=by_priority.get("high", 0),
        medium=by_priority.get("medium", 0),
        low=by_priority.get("low", 0),
        by_category=by_category,
        by_priority=by_priority,
        by_severity=by_severity,
        by_source=by_source,
        by_page=by_page,
    )


def aggregate(scan_id: str, result: dict[str, Any] | None, created_at: str | None = None) -> IssuesPayload:
    """Build a unified issues payload from stored analyzer results."""
    statuses = analyzer_status_map(result)
    try:
        findings, truncated = collect_findings(result, scan_id=scan_id, created_at=created_at)
        merged = merge_findings(findings)
        buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        order: list[tuple[str, str]] = []
        for finding in merged:
            key = _group_key(finding)
            if key not in buckets:
                order.append(key)
            buckets[key].append(finding)
        issues = [
            _build_grouped_issue(buckets[key], scan_id=scan_id, primary_page=_primary_page(result), created_at=created_at)
            for key in order
        ]
        if len(issues) > MAX_ISSUES_PER_SCAN:
            truncated = True
            issues.sort(key=lambda item: (item.priority_score, SEVERITY_RANK.get(item.severity, 0)), reverse=True)
            issues = issues[:MAX_ISSUES_PER_SCAN]
            logger.info("issues_truncated scan_id=%s kept=%s", scan_id, MAX_ISSUES_PER_SCAN)
        _attach_related(issues)
        attach_snippets(issues, result)
        visual = sum(
            1
            for issue in issues
            if visual_kind_for(issue.check_id) == "screenshot" and issue.check_status in ACTIONABLE_STATUSES
        )
        return IssuesPayload(
            version=1,
            truncated=truncated,
            analyzer_status=statuses,
            summary=summarize_issues(issues, actionable_only=True),
            issues=issues,
            groups=group_ids(issues),
            screenshot_capture=ScreenshotCaptureSummary(
                status="pending" if visual else "completed",
                captured=0,
                visual=visual,
                note=f"Screenshots captured for 0 of {visual} visual issues." if visual else None,
            ),
        )
    except Exception:
        logger.exception("issues_aggregate_failed scan_id=%s", scan_id)
        return IssuesPayload(
            version=1,
            truncated=False,
            analyzer_status=statuses,
            summary=summarize_issues([]),
            issues=[],
            groups={},
        )


def payload_from_result(scan_id: str, result: dict[str, Any] | None, created_at: str | None = None) -> IssuesPayload:
    stored = (result or {}).get("issues")
    if isinstance(stored, dict) and isinstance(stored.get("issues"), list):
        try:
            return IssuesPayload.model_validate(stored)
        except Exception:
            logger.info("issues_stored_payload_invalid scan_id=%s", scan_id)
    return aggregate(scan_id, result, created_at)


def issue_to_list_item(issue: UnifiedIssue) -> dict[str, Any]:
    return {
        "issue_id": issue.issue_id,
        "issue_key": issue.issue_key,
        "title": issue.title,
        "description": issue.description,
        "source": issue.source,
        "analyzer": issue.analyzer,
        "category": issue.category,
        "subcategory": issue.subcategory,
        "check_id": issue.check_id,
        "status": issue.status,
        "check_status": issue.check_status,
        "severity": issue.severity,
        "priority": issue.priority,
        "priority_score": issue.priority_score,
        "page_url": issue.page_url,
        "affected_page_count": issue.affected_page_count,
        "affected_element_count": issue.affected_element_count,
        "occurrence_count": len(issue.occurrences),
        "recommendation": issue.recommendation,
        "source_href": issue.source_href,
        "related_issue_ids": issue.related_issue_ids,
        "screenshot_url": issue.screenshot_url,
        "screenshot_caption": issue.screenshot_caption,
        "highlighted_selector": issue.highlighted_selector,
        "viewport_type": issue.viewport_type,
        "snippet": issue.snippet,
        "snippet_language": issue.snippet_language,
        "snippet_highlight_line": issue.snippet_highlight_line,
        "screenshot_unavailable": issue.screenshot_unavailable,
        "screenshot_unavailable_reason": issue.screenshot_unavailable_reason,
        "visual_kind": (issue.details or {}).get("visual_kind"),
        "whats_wrong": issue.description,
        "why_it_matters": (issue.details or {}).get("why"),
        "how_to_fix": issue.recommendation,
    }


def issue_to_detail(issue: UnifiedIssue, scan_id: str, siblings: list[UnifiedIssue]) -> dict[str, Any]:
    related = []
    by_id = {item.issue_id: item for item in siblings}
    for related_id in issue.related_issue_ids:
        other = by_id.get(related_id)
        if other:
            related.append(
                {
                    "issue_id": other.issue_id,
                    "issue_key": other.issue_key,
                    "title": other.title,
                    "source": other.source,
                    "category": other.category,
                    "priority": other.priority,
                    "severity": other.severity,
                }
            )
    return {
        "scan_id": scan_id,
        "issue": {
            **issue.model_dump(mode="json"),
            "whats_wrong": issue.description,
            "why_it_matters": (issue.details or {}).get("why"),
            "how_to_fix": issue.recommendation,
            "visual_kind": (issue.details or {}).get("visual_kind"),
            "related_issues": related,
            "original_finding": {
                "check_id": issue.check_id,
                "source": issue.source,
                "finding_ids": issue.details.get("finding_ids") or [],
                "source_severity": issue.source_severity,
                "score": issue.score,
            },
        },
    }