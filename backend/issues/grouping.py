"""Reusable grouping helpers for unified issues."""

from __future__ import annotations

from collections import defaultdict

from backend.issues.models import UnifiedIssue


def group_by_category(issues: list[UnifiedIssue]) -> dict[str, list[UnifiedIssue]]:
    grouped: dict[str, list[UnifiedIssue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.category].append(issue)
    return dict(grouped)


def group_by_priority(issues: list[UnifiedIssue]) -> dict[str, list[UnifiedIssue]]:
    grouped: dict[str, list[UnifiedIssue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.priority].append(issue)
    return dict(grouped)


def group_by_page(issues: list[UnifiedIssue]) -> dict[str, list[UnifiedIssue]]:
    grouped: dict[str, list[UnifiedIssue]] = defaultdict(list)
    for issue in issues:
        pages = issue.pages or ([issue.page_url] if issue.page_url else [])
        if not pages:
            grouped[""].append(issue)
            continue
        for page in pages:
            grouped[page].append(issue)
    return dict(grouped)


def group_by_source(issues: list[UnifiedIssue]) -> dict[str, list[UnifiedIssue]]:
    grouped: dict[str, list[UnifiedIssue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.source].append(issue)
    return dict(grouped)


def group_by_issue_key(issues: list[UnifiedIssue]) -> dict[str, list[UnifiedIssue]]:
    grouped: dict[str, list[UnifiedIssue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.issue_key].append(issue)
    return dict(grouped)


def group_ids(issues: list[UnifiedIssue]) -> dict[str, dict[str, list[str]]]:
    return {
        "category": {key: [item.issue_id for item in values] for key, values in group_by_category(issues).items()},
        "priority": {key: [item.issue_id for item in values] for key, values in group_by_priority(issues).items()},
        "page": {key: [item.issue_id for item in values] for key, values in group_by_page(issues).items()},
        "source": {key: [item.issue_id for item in values] for key, values in group_by_source(issues).items()},
        "issue_key": {key: [item.issue_id for item in values] for key, values in group_by_issue_key(issues).items()},
    }
