"""Attach analyzer availability and Phase 12 issue counts to crawled pages."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.issues.config import ACTIONABLE_STATUSES
from backend.issues.models import IssuesPayload, UnifiedIssue
from backend.pages.config import ANALYZER_HREFS, ANALYZER_KEYS, ANALYZER_LABELS
from backend.pages.models import PageRecord, PagesPayload
from backend.services.url_identity import normalize_page_url


def payload_from_result(result: dict[str, Any] | None) -> PagesPayload:
    data = (result or {}).get("pages")
    if not data:
        return PagesPayload()
    if isinstance(data, PagesPayload):
        return data
    return PagesPayload.model_validate(data)


def attach_analyzers(pages: list[PageRecord], result: dict[str, Any] | None) -> None:
    payload = result or {}
    for page in pages:
        scores: dict[str, int | None] = {}
        available: list[str] = []
        if page.is_seed:
            for key in ANALYZER_KEYS:
                data = payload.get(key)
                if isinstance(data, dict):
                    available.append(key)
                    score = data.get("score")
                    scores[key] = int(score) if isinstance(score, (int, float)) else None
                else:
                    scores[key] = None
        else:
            for key in ANALYZER_KEYS:
                scores[key] = None
        page.available_analyzers = available
        page.analyzer_scores = scores
        if page.is_seed:
            seo = payload.get("seo") or {}
            indexable = seo.get("indexable")
            if isinstance(indexable, dict) and "indexable" in indexable:
                page.indexable = bool(indexable.get("indexable"))

    cro = payload.get("cro")
    if isinstance(cro, dict):
        by_id = {item.get("page_id"): item for item in cro.get("pages") or [] if isinstance(item, dict)}
        by_url = {
            normalize_page_url(item.get("url")): item
            for item in cro.get("pages") or []
            if isinstance(item, dict) and item.get("url")
        }
        for page in pages:
            row = by_id.get(page.id) or by_url.get(normalize_page_url(page.normalized_url or page.url))
            if not row or not row.get("available"):
                continue
            if "cro" not in page.available_analyzers:
                page.available_analyzers = [*page.available_analyzers, "cro"]
            scores = dict(page.analyzer_scores)
            score = row.get("score")
            scores["cro"] = int(score) if isinstance(score, (int, float)) else None
            page.analyzer_scores = scores

    trust = payload.get("trust")
    if isinstance(trust, dict):
        by_id = {item.get("page_id"): item for item in trust.get("pages") or [] if isinstance(item, dict)}
        by_url = {
            normalize_page_url(item.get("url")): item
            for item in trust.get("pages") or []
            if isinstance(item, dict) and item.get("url")
        }
        for page in pages:
            row = by_id.get(page.id) or by_url.get(normalize_page_url(page.normalized_url or page.url))
            if not row or not row.get("available"):
                continue
            if "trust" not in page.available_analyzers:
                page.available_analyzers = [*page.available_analyzers, "trust"]
            scores = dict(page.analyzer_scores)
            score = row.get("score")
            scores["trust"] = int(score) if isinstance(score, (int, float)) else None
            page.analyzer_scores = scores


def _issue_urls(issue: UnifiedIssue) -> set[str]:
    urls: set[str] = set()
    if issue.page_url:
        urls.add(normalize_page_url(issue.page_url))
    for page in issue.pages:
        urls.add(normalize_page_url(page))
    for occurrence in issue.occurrences:
        if occurrence.page_url:
            urls.add(normalize_page_url(occurrence.page_url))
    return {url for url in urls if url}


def attach_issues(pages: list[PageRecord], issues_payload: IssuesPayload | dict[str, Any] | None) -> None:
    if issues_payload is None:
        return
    if isinstance(issues_payload, dict):
        parsed = IssuesPayload.model_validate(issues_payload)
    else:
        parsed = issues_payload
    by_url: dict[str, list[UnifiedIssue]] = defaultdict(list)
    for issue in parsed.issues:
        if issue.check_status not in ACTIONABLE_STATUSES:
            continue
        if issue.status != "open":
            continue
        for url in _issue_urls(issue):
            by_url[url].append(issue)

    for page in pages:
        keys = {
            page.normalized_url,
            normalize_page_url(page.final_url),
            normalize_page_url(page.url),
        }
        matched: list[UnifiedIssue] = []
        seen: set[str] = set()
        for key in keys:
            if not key:
                continue
            for issue in by_url.get(key, []):
                if issue.issue_id in seen:
                    continue
                seen.add(issue.issue_id)
                matched.append(issue)
        page.related_issue_ids = [issue.issue_id for issue in matched]
        page.issue_count = len(matched)
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for issue in matched:
            if issue.severity in counts:
                counts[issue.severity] += 1
        page.severity_counts = counts


def analyzer_cards(page: PageRecord, scan_id: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for key in ANALYZER_KEYS:
        available = key in page.available_analyzers
        href = f"/scan/{scan_id}/{ANALYZER_HREFS[key]}" if available else None
        note = None
        link_label = None
        if available:
            link_label = f"View {ANALYZER_LABELS[key]} analysis"
        elif page.is_seed:
            note = "Not analyzed"
        else:
            note = "Available in site analysis"
            href = f"/scan/{scan_id}/{ANALYZER_HREFS[key]}"
            link_label = None
        cards.append(
            {
                "id": key,
                "label": ANALYZER_LABELS[key],
                "available": available,
                "score": page.analyzer_scores.get(key),
                "href": href if available else None,
                "link_label": link_label if available else None,
                "note": note if not available else None,
                "site_href": f"/scan/{scan_id}/{ANALYZER_HREFS[key]}" if not available and not page.is_seed else None,
            }
        )
    return cards


def related_issue_items(page: PageRecord, issues_payload: IssuesPayload | None) -> list[dict[str, Any]]:
    if issues_payload is None:
        return []
    by_id = {issue.issue_id: issue for issue in issues_payload.issues}
    items: list[dict[str, Any]] = []
    for issue_id in page.related_issue_ids:
        issue = by_id.get(issue_id)
        if issue is None:
            continue
        items.append(
            {
                "issue_id": issue.issue_id,
                "issue_key": issue.issue_key,
                "title": issue.title,
                "severity": issue.severity,
                "priority": issue.priority,
                "status": issue.status,
                "source": issue.source,
                "category": issue.category,
                "check_status": issue.check_status,
            }
        )
    return items
