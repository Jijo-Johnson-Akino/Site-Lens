"""Generate consolidated recommendations from stored issues and architecture observations."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from backend.architecture.engine import build_architecture
from backend.issues.config import ACTIONABLE_STATUSES
from backend.issues.engine import analyzer_status_map, payload_from_result as issues_from_result
from backend.issues.models import UnifiedIssue
from backend.issues.normalize import stable_id
from backend.pages.engine import payload_from_result as pages_from_result
from backend.recommendations.config import (
    CATEGORY_VALUES,
    MAX_EVIDENCE_RESOURCES,
    MAX_EVIDENCE_URLS,
    METHODOLOGY,
    PRIORITIES,
    STATUSES,
)
from backend.recommendations.models import Recommendation, RecommendationSummary, RecommendationsPayload
from backend.recommendations.registry import all_rules
from backend.recommendations.rules.architecture import (
    DEAD_END_KEY,
    DEEP_KEY,
    ORPHAN_KEY,
    architecture_rule_copy,
    dead_end_nodes,
    deep_nodes,
    orphan_nodes,
)
from backend.recommendations.scoring import calculate_effort, calculate_impact, calculate_priority
from backend.services.url_identity import normalize_page_url

logger = logging.getLogger("sitebench.recommendations")


def grouping_key(recommendation_key: str, scope_identifier: str = "site") -> str:
    return f"{recommendation_key}|{scope_identifier}"


def _actionable_issues(issues: list[UnifiedIssue]) -> list[UnifiedIssue]:
    selected = []
    for issue in issues:
        if issue.check_status not in ACTIONABLE_STATUSES:
            continue
        if issue.status == "ignored":
            continue
        selected.append(issue)
    return selected


def _page_lookup(result: dict[str, Any] | None) -> dict[str, Any]:
    payload = pages_from_result(result)
    lookup: dict[str, Any] = {}
    for page in payload.items:
        for raw in (page.normalized_url, page.url, page.final_url):
            url = normalize_page_url(raw)
            if url and url not in lookup:
                lookup[url] = page
    return lookup


def _issue_urls(issue: UnifiedIssue) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for raw in [issue.page_url, *issue.pages, *[item.page_url for item in issue.occurrences]]:
        url = normalize_page_url(raw)
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _issue_resources(issue: UnifiedIssue) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    candidates = [issue.resource_url]
    for occurrence in issue.occurrences:
        candidates.append(occurrence.resource_url)
        for element in occurrence.affected_elements:
            candidates.append(element.resource_url)
        evidence = occurrence.evidence or {}
        if isinstance(evidence, dict):
            candidates.append(evidence.get("resource_url") if isinstance(evidence.get("resource_url"), str) else None)
    for item in candidates:
        if not item:
            continue
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            values.append(text)
    return values


def _occurrence_count(issue: UnifiedIssue) -> int:
    return max(len(issue.occurrences), issue.affected_page_count, 1)


def _pages_for_urls(urls: list[str], lookup: dict[str, Any]) -> tuple[list[str], list[str]]:
    page_ids: list[str] = []
    page_urls: list[str] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for url in urls:
        if url not in seen_urls:
            seen_urls.add(url)
            page_urls.append(url)
        page = lookup.get(url)
        if page is not None and page.id and page.id not in seen_ids:
            seen_ids.add(page.id)
            page_ids.append(page.id)
    return page_ids[:MAX_EVIDENCE_URLS], page_urls[:MAX_EVIDENCE_URLS]


def _preserve_status(
    grouping: str,
    previous: RecommendationsPayload | None,
    user_status: dict[str, str],
) -> str:
    if grouping in user_status and user_status[grouping] in STATUSES:
        return user_status[grouping]
    if previous:
        for item in previous.recommendations:
            if item.grouping_key == grouping and item.status in STATUSES:
                return item.status
    return "open"


def _build_from_issues(
    rule,
    matches: list[UnifiedIssue],
    *,
    scan_id: str,
    lookup: dict[str, Any],
    created_at: str | None,
    previous: RecommendationsPayload | None,
    user_status: dict[str, str],
) -> Recommendation:
    urls: list[str] = []
    seen_urls: set[str] = set()
    resources: list[str] = []
    seen_resources: set[str] = set()
    issue_ids: list[str] = []
    issue_keys: list[str] = []
    element_count = 0
    issue_count = 0
    for issue in matches:
        issue_ids.append(issue.issue_id)
        if issue.issue_key not in issue_keys:
            issue_keys.append(issue.issue_key)
        element_count += int(issue.affected_element_count or 0)
        issue_count += _occurrence_count(issue)
        for url in _issue_urls(issue):
            if url not in seen_urls:
                seen_urls.add(url)
                urls.append(url)
        for resource in _issue_resources(issue):
            if resource not in seen_resources:
                seen_resources.add(resource)
                resources.append(resource)
    page_ids, page_urls = _pages_for_urls(urls, lookup)
    priority = calculate_priority(matches, cap=rule.priority_cap)
    impact = calculate_impact(
        base=rule.impact,
        priority=priority,
        page_count=len(page_urls) or len(urls),
        element_count=element_count,
    )
    scope_id = "site"
    group = grouping_key(rule.recommendation_key, scope_id)
    evidence: dict[str, Any] = {
        "issue_keys": issue_keys,
        "issue_ids": issue_ids,
        "page_urls": page_urls,
        "page_ids": page_ids,
        "resources": resources[:MAX_EVIDENCE_RESOURCES],
        "affected_page_count": len(page_urls) or len(urls),
        "affected_element_count": element_count,
        "issue_count": issue_count,
    }
    if rule.recommendation_key == "performance.enable_lazy_loading":
        evidence["lcp_note"] = (
            "Do not lazy-load an image identified as Largest Contentful Paint. "
            "The source finding already excludes a confirmed LCP image when that evidence is available."
        )
    created = created_at
    if previous:
        for item in previous.recommendations:
            if item.grouping_key == group and item.created_at:
                created = item.created_at
                break
    return Recommendation(
        id=stable_id("rec", scan_id, rule.recommendation_key, scope_id),
        scan_id=scan_id,
        recommendation_key=rule.recommendation_key,
        grouping_key=group,
        scope="site",
        scope_identifier=scope_id,
        title=rule.title,
        summary=rule.summary,
        category=rule.category,
        priority=priority,  # type: ignore[arg-type]
        effort=calculate_effort(rule.effort),  # type: ignore[arg-type]
        impact=impact,  # type: ignore[arg-type]
        status=_preserve_status(group, previous, user_status),  # type: ignore[arg-type]
        affected_page_count=len(page_urls) or len(urls),
        affected_element_count=element_count,
        issue_count=issue_count,
        issue_ids=issue_ids,
        issue_keys=issue_keys,
        page_ids=page_ids,
        page_urls=page_urls,
        rationale=rule.rationale,
        action_steps=list(rule.action_steps),
        evidence=evidence,
        depends_on_recommendation_keys=list(rule.depends_on),
        source_kind="issues",
        created_at=created,
        updated_at=created_at,
    )


def _build_from_architecture(
    recommendation_key: str,
    nodes: list[Any],
    *,
    scan_id: str,
    created_at: str | None,
    previous: RecommendationsPayload | None,
    user_status: dict[str, str],
    extra_evidence: dict[str, Any] | None = None,
) -> Recommendation:
    copy = architecture_rule_copy(recommendation_key)
    page_ids: list[str] = []
    page_urls: list[str] = []
    for node in nodes:
        page = node.page
        if page.id and page.id not in page_ids:
            page_ids.append(page.id)
        url = normalize_page_url(page.normalized_url or page.url)
        if url and url not in page_urls:
            page_urls.append(url)
    page_ids = page_ids[:MAX_EVIDENCE_URLS]
    page_urls = page_urls[:MAX_EVIDENCE_URLS]
    page_count = len(page_urls) or len(nodes)
    priority = copy["priority"]
    if recommendation_key == ORPHAN_KEY and page_count >= 5:
        priority = "high"
    impact = calculate_impact(
        base=copy["impact"],
        priority=priority,
        page_count=page_count,
        element_count=0,
    )
    group = grouping_key(recommendation_key, "site")
    evidence: dict[str, Any] = {
        "observation": recommendation_key,
        "page_urls": page_urls,
        "page_ids": page_ids,
        "affected_page_count": page_count,
        "links_recorded": True,
    }
    if extra_evidence:
        evidence.update(extra_evidence)
    created = created_at
    if previous:
        for item in previous.recommendations:
            if item.grouping_key == group and item.created_at:
                created = item.created_at
                break
    return Recommendation(
        id=stable_id("rec", scan_id, recommendation_key, "site"),
        scan_id=scan_id,
        recommendation_key=recommendation_key,
        grouping_key=group,
        scope="site",
        scope_identifier="site",
        title=copy["title"],
        summary=copy["summary"],
        category=copy["category"],
        priority=priority,
        effort=copy["effort"],
        impact=impact,  # type: ignore[arg-type]
        status=_preserve_status(group, previous, user_status),  # type: ignore[arg-type]
        affected_page_count=page_count,
        affected_element_count=0,
        issue_count=0,
        issue_ids=[],
        issue_keys=[],
        page_ids=page_ids,
        page_urls=page_urls,
        rationale=copy["rationale"],
        action_steps=list(copy["action_steps"]),
        evidence=evidence,
        source_kind="architecture",
        created_at=created,
        updated_at=created_at,
    )


def _apply_dependencies(items: list[Recommendation]) -> None:
    by_key = {item.recommendation_key: item for item in items}
    for item in items:
        resolved: list[str] = []
        for key in item.depends_on_recommendation_keys:
            other = by_key.get(key)
            if other:
                resolved.append(other.id)
        item.depends_on_recommendation_ids = resolved


def summarize_recommendations(items: list[Recommendation]) -> RecommendationSummary:
    by_category = {label: 0 for label in CATEGORY_VALUES}
    by_priority = {label: 0 for label in PRIORITIES}
    by_status = {label: 0 for label in STATUSES}
    high_by_category = {label: 0 for label in CATEGORY_VALUES}
    high_priority = 0
    for item in items:
        by_category[item.category] = by_category.get(item.category, 0) + 1
        by_priority[item.priority] = by_priority.get(item.priority, 0) + 1
        by_status[item.status] = by_status.get(item.status, 0) + 1
        if item.priority in {"critical", "high"}:
            high_priority += 1
            high_by_category[item.category] = high_by_category.get(item.category, 0) + 1
    return RecommendationSummary(
        total=len(items),
        open=by_status.get("open", 0),
        in_progress=by_status.get("in_progress", 0),
        completed=by_status.get("completed", 0),
        dismissed=by_status.get("dismissed", 0),
        high_priority=high_priority,
        critical=by_priority.get("critical", 0),
        high=by_priority.get("high", 0),
        medium=by_priority.get("medium", 0),
        low=by_priority.get("low", 0),
        info=by_priority.get("info", 0),
        by_category=by_category,
        by_priority=by_priority,
        by_status=by_status,
        high_priority_by_category=high_by_category,
    )


def previous_from_result(result: dict[str, Any] | None) -> RecommendationsPayload | None:
    stored = (result or {}).get("recommendations")
    if isinstance(stored, dict) and isinstance(stored.get("recommendations"), list):
        try:
            return RecommendationsPayload.model_validate(stored)
        except Exception:
            logger.info("recommendations_stored_payload_invalid")
            return None
    return None


def generate(scan_id: str, result: dict[str, Any] | None, created_at: str | None = None) -> RecommendationsPayload:
    """Build recommendations from stored issues and architecture observations."""
    payload = result or {}
    statuses = analyzer_status_map(payload)
    previous = previous_from_result(payload)
    user_status = dict(previous.user_status) if previous else {}
    issues_payload = issues_from_result(scan_id, payload, created_at)
    actionable = _actionable_issues(issues_payload.issues)
    by_key: dict[str, list[UnifiedIssue]] = defaultdict(list)
    for issue in actionable:
        by_key[issue.issue_key].append(issue)
    lookup = _page_lookup(payload)
    items: list[Recommendation] = []
    seen_groups: set[str] = set()
    for rec_rule in all_rules():
        matches: list[UnifiedIssue] = []
        for issue_key in rec_rule.trigger_issue_keys:
            matches.extend(by_key.get(issue_key, []))
        if not matches:
            continue
        rec = _build_from_issues(
            rec_rule,
            matches,
            scan_id=scan_id,
            lookup=lookup,
            created_at=created_at,
            previous=previous,
            user_status=user_status,
        )
        if rec.grouping_key in seen_groups:
            continue
        seen_groups.add(rec.grouping_key)
        items.append(rec)

    graph = build_architecture(payload)
    if graph.links_recorded:
        orphans = orphan_nodes(graph)
        if orphans:
            rec = _build_from_architecture(
                ORPHAN_KEY,
                orphans,
                scan_id=scan_id,
                created_at=created_at,
                previous=previous,
                user_status=user_status,
            )
            if rec.grouping_key not in seen_groups:
                seen_groups.add(rec.grouping_key)
                items.append(rec)
        deep = deep_nodes(graph)
        if deep:
            rec = _build_from_architecture(
                DEEP_KEY,
                deep,
                scan_id=scan_id,
                created_at=created_at,
                previous=previous,
                user_status=user_status,
                extra_evidence={"max_observed_depth": max(node.page.depth for node in deep)},
            )
            if rec.grouping_key not in seen_groups:
                seen_groups.add(rec.grouping_key)
                items.append(rec)
        dead_ends = dead_end_nodes(graph)
        if dead_ends:
            rec = _build_from_architecture(
                DEAD_END_KEY,
                dead_ends,
                scan_id=scan_id,
                created_at=created_at,
                previous=previous,
                user_status=user_status,
            )
            if rec.grouping_key not in seen_groups:
                seen_groups.add(rec.grouping_key)
                items.append(rec)

    _apply_dependencies(items)
    for item in items:
        user_status[item.grouping_key] = item.status
    return RecommendationsPayload(
        version=1,
        truncated=False,
        analyzer_status=statuses,  # type: ignore[arg-type]
        summary=summarize_recommendations(items),
        recommendations=items,
        user_status=user_status,  # type: ignore[arg-type]
        methodology=METHODOLOGY,
    )


def payload_from_result(scan_id: str, result: dict[str, Any] | None, created_at: str | None = None) -> RecommendationsPayload:
    stored = (result or {}).get("recommendations")
    if isinstance(stored, dict) and isinstance(stored.get("recommendations"), list):
        try:
            return RecommendationsPayload.model_validate(stored)
        except Exception:
            logger.info("recommendations_stored_payload_invalid scan_id=%s", scan_id)
    if (result or {}).get("recommendations_error"):
        return RecommendationsPayload(
            version=1,
            analyzer_status=analyzer_status_map(result),  # type: ignore[arg-type]
            summary=summarize_recommendations([]),
            recommendations=[],
            methodology=METHODOLOGY,
        )
    return generate(scan_id, result, created_at)


def apply_status(payload: RecommendationsPayload, recommendation_id: str, status: str) -> Recommendation | None:
    if status not in STATUSES:
        return None
    for item in payload.recommendations:
        if item.id == recommendation_id:
            item.status = status  # type: ignore[assignment]
            item.updated_at = datetime.now(timezone.utc).isoformat()
            payload.user_status[item.grouping_key] = status  # type: ignore[assignment]
            payload.summary = summarize_recommendations(payload.recommendations)
            return item
    return None
