"""Filter, search, sort, and paginate unified issues. In-memory, parameterized-style."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.issues.urls import normalize_page_url
from backend.issues.config import (
    ACTIONABLE_STATUSES,
    CATEGORY_VALUES,
    DEFAULT_PAGE_SIZE,
    LIFECYCLE_STATUSES,
    MAX_PAGE_SIZE,
    MAX_SEARCH_LENGTH,
    PRIORITIES,
    SEVERITIES,
    SORT_FIELDS,
    SOURCE_TO_CATEGORY,
    SOURCE_VALUES,
    CHECK_STATUSES,
)
from backend.issues.models import UnifiedIssue
from backend.issues.priority import PRIORITY_RANK, SEVERITY_RANK

_CATEGORY_ALIASES = {value.lower(): value for value in CATEGORY_VALUES}
_CATEGORY_ALIASES.update(
    {
        "uiux": "UI/UX",
        "ui/ux": "UI/UX",
        "ui_ux": "UI/UX",
        "a11y": "Accessibility",
        "structureddata": "Structured Data",
        "structured_data": "Structured Data",
        "perf": "Performance",
        "trust": "Trust",
        "trust & credibility": "Trust",
    }
)
_SOURCE_ALIASES = {value: value for value in SOURCE_VALUES}
_SOURCE_ALIASES.update(
    {
        "ui/ux": "uiux",
        "ui_ux": "uiux",
        "a11y": "accessibility",
        "perf": "performance",
        "schema": "structured_data",
        "structured-data": "structured_data",
    }
)


def parse_page(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1
    return max(1, value)


def parse_page_size(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return max(1, min(MAX_PAGE_SIZE, value))


def parse_search(raw: Any) -> str:
    text = str(raw or "")
    if len(text) > MAX_SEARCH_LENGTH:
        return text[:MAX_SEARCH_LENGTH]
    return text


def parse_sort(raw: Any) -> str:
    value = str(raw or "priority").strip().lower()
    aliases = {
        "affected_pages": "affected_pages",
        "pages": "affected_pages",
        "affected_elements": "affected_elements",
        "elements": "affected_elements",
        "created": "created_at",
        "created_at": "created_at",
    }
    mapped = aliases.get(value, value)
    return mapped if mapped in SORT_FIELDS else "priority"


def parse_order(raw: Any) -> str:
    value = str(raw or "desc").strip().lower()
    return "asc" if value == "asc" else "desc"


def parse_enum(raw: Any, allowed: tuple[str, ...] | frozenset[str], aliases: dict[str, str] | None = None) -> str | None:
    if raw is None or raw == "" or str(raw).lower() == "all":
        return None
    value = str(raw).strip().lower()
    if aliases and value in aliases:
        return aliases[value]
    for item in allowed:
        if item.lower() == value:
            return item
    return None


def parse_source(raw: Any) -> str | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower().replace(" ", "_")
    if value in _SOURCE_ALIASES:
        return _SOURCE_ALIASES[value]
    return value if value in SOURCE_VALUES else None


def parse_category(raw: Any) -> str | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower()
    if value in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[value]
    mapped = SOURCE_TO_CATEGORY.get(value)
    return mapped


def _search_blob(issue: UnifiedIssue) -> str:
    parts = [
        issue.title,
        issue.issue_key,
        issue.description,
        issue.category,
        issue.subcategory or "",
        issue.page_url or "",
        issue.selector or "",
        issue.recommendation or "",
        issue.check_id,
        issue.source,
        " ".join(issue.pages),
    ]
    for occurrence in issue.occurrences:
        parts.append(occurrence.page_url)
        parts.append(occurrence.selector or "")
        parts.append(occurrence.message)
        parts.append(occurrence.recommendation or "")
    return " ".join(parts).lower()


def filter_issues(
    issues: list[UnifiedIssue],
    *,
    status: str | None = None,
    severity: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    source: str | None = None,
    check_status: str | None = None,
    page_url: str | None = None,
    issue_key: str | None = None,
    issue_ids: set[str] | None = None,
    search: str = "",
    include_non_actionable: bool = False,
) -> list[UnifiedIssue]:
    needle = search.strip().lower()
    selected: list[UnifiedIssue] = []
    for issue in issues:
        if status and issue.status != status:
            continue
        if severity and issue.severity != severity:
            continue
        if priority and issue.priority != priority:
            continue
        if category and issue.category != category:
            continue
        if source and issue.source != source:
            continue
        if check_status and issue.check_status != check_status:
            continue
        if not include_non_actionable and not check_status and issue.check_status not in ACTIONABLE_STATUSES:
            continue
        if issue_key and issue.issue_key != issue_key:
            continue
        if issue_ids and issue.issue_id not in issue_ids:
            continue
        if page_url:
            target = normalize_page_url(page_url)
            related = {normalize_page_url(item) for item in issue.pages if item}
            if issue.page_url:
                related.add(normalize_page_url(issue.page_url))
            for occurrence in issue.occurrences:
                if occurrence.page_url:
                    related.add(normalize_page_url(occurrence.page_url))
            if target not in related:
                continue
        if needle and needle not in _search_blob(issue):
            continue
        selected.append(issue)
    return selected


def _created_stamp(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def sort_issues(issues: list[UnifiedIssue], sort: str, order: str) -> list[UnifiedIssue]:
    reverse = order != "asc"

    def key(issue: UnifiedIssue) -> tuple:
        if sort == "severity":
            primary: Any = SEVERITY_RANK.get(issue.severity, 0)
        elif sort == "category":
            primary = issue.category.lower()
        elif sort == "affected_pages":
            primary = issue.affected_page_count
        elif sort == "affected_elements":
            primary = issue.affected_element_count
        elif sort == "created_at":
            primary = _created_stamp(issue.created_at)
        else:
            primary = PRIORITY_RANK.get(issue.priority, 0)
        return (
            primary,
            PRIORITY_RANK.get(issue.priority, 0),
            SEVERITY_RANK.get(issue.severity, 0),
            issue.affected_page_count,
            issue.title.lower(),
        )

    return sorted(issues, key=key, reverse=reverse)


def paginate(items: list[UnifiedIssue], page: int, page_size: int) -> tuple[list[UnifiedIssue], dict[str, int]]:
    total = len(items)
    pages = max(1, (total + page_size - 1) // page_size) if total else 1
    current = min(page, pages)
    start = (current - 1) * page_size
    end = start + page_size
    return items[start:end], {
        "page": current,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    }


def query_issues(
    issues: list[UnifiedIssue],
    params: dict[str, Any],
) -> tuple[list[UnifiedIssue], dict[str, int]]:
    status = parse_enum(params.get("status"), LIFECYCLE_STATUSES)
    severity = parse_enum(params.get("severity"), SEVERITIES)
    priority = parse_enum(params.get("priority"), PRIORITIES)
    check_status = parse_enum(params.get("check_status"), CHECK_STATUSES)
    category = parse_category(params.get("category"))
    source = parse_source(params.get("source"))
    search = parse_search(params.get("search"))
    page_url = str(params.get("page_url") or "").strip() or None
    include_all = str(params.get("include_all") or "").lower() in {"1", "true", "yes"}
    issue_key = str(params.get("issue_key") or "").strip() or None
    raw_ids = str(params.get("issue_ids") or "").strip()
    issue_ids = {part.strip() for part in raw_ids.split(",") if part.strip()} if raw_ids else None
    if issue_ids and len(issue_ids) > 100:
        issue_ids = set(list(issue_ids)[:100])
    filtered = filter_issues(
        issues,
        status=status,
        severity=severity,
        priority=priority,
        category=category,
        source=source,
        check_status=check_status,
        page_url=page_url,
        issue_key=issue_key,
        issue_ids=issue_ids,
        search=search,
        include_non_actionable=include_all or bool(check_status),
    )
    sorted_items = sort_issues(filtered, parse_sort(params.get("sort")), parse_order(params.get("order")))
    return paginate(sorted_items, parse_page(params.get("page")), parse_page_size(params.get("page_size")))
