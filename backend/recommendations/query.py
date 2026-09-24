"""Filter, search, sort, and paginate recommendations."""

from __future__ import annotations

from typing import Any

from backend.recommendations.config import (
    CATEGORY_VALUES,
    DEFAULT_PAGE_SIZE,
    EFFORTS,
    IMPACTS,
    MAX_PAGE_SIZE,
    MAX_SEARCH_LENGTH,
    PRIORITIES,
    SORT_FIELDS,
    STATUSES,
)
from backend.recommendations.models import Recommendation
from backend.recommendations.scoring import EFFORT_RANK, IMPACT_RANK, PRIORITY_RANK, STATUS_RANK

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
        "architecture": "Architecture",
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
        "issue_count": "issue_count",
        "issues": "issue_count",
        "priority": "priority",
        "impact": "impact",
        "effort": "effort",
        "category": "category",
        "status": "status",
    }
    mapped = aliases.get(value, value)
    return mapped if mapped in SORT_FIELDS else "priority"


def parse_order(raw: Any) -> str:
    value = str(raw or "desc").strip().lower()
    return "asc" if value == "asc" else "desc"


def parse_enum(raw: Any, allowed: tuple[str, ...], aliases: dict[str, str] | None = None) -> str | None:
    if raw is None or raw == "" or str(raw).lower() == "all":
        return None
    value = str(raw).strip().lower()
    if aliases and value in aliases:
        return aliases[value]
    for item in allowed:
        if item.lower() == value:
            return item
    return None


def parse_category(raw: Any) -> str | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower()
    if value in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[value]
    return None


def _search_blob(item: Recommendation) -> str:
    parts = [
        item.title,
        item.summary,
        item.category,
        item.recommendation_key,
        item.rationale,
        " ".join(item.page_urls),
        " ".join(item.issue_keys),
        " ".join(item.action_steps),
    ]
    return " ".join(parts).lower()


def filter_recommendations(
    items: list[Recommendation],
    *,
    category: str | None = None,
    priority: str | None = None,
    impact: str | None = None,
    effort: str | None = None,
    status: str | None = None,
    search: str = "",
) -> list[Recommendation]:
    needle = search.strip().lower()
    selected: list[Recommendation] = []
    for item in items:
        if category and item.category != category:
            continue
        if priority and item.priority != priority:
            continue
        if impact and item.impact != impact:
            continue
        if effort and item.effort != effort:
            continue
        if status and item.status != status:
            continue
        if needle and needle not in _search_blob(item):
            continue
        selected.append(item)
    return selected


def sort_recommendations(items: list[Recommendation], sort: str, order: str) -> list[Recommendation]:
    reverse = order != "asc"

    def key(item: Recommendation) -> tuple:
        if sort == "impact":
            primary: Any = IMPACT_RANK.get(item.impact, 0)
        elif sort == "effort":
            primary = EFFORT_RANK.get(item.effort, 0)
        elif sort == "affected_pages":
            primary = item.affected_page_count
        elif sort == "issue_count":
            primary = item.issue_count
        elif sort == "category":
            primary = item.category.lower()
        elif sort == "status":
            primary = STATUS_RANK.get(item.status, 0)
        else:
            primary = PRIORITY_RANK.get(item.priority, 0)
        return (
            primary,
            PRIORITY_RANK.get(item.priority, 0),
            item.affected_page_count,
            item.issue_count,
            item.title.lower(),
        )

    return sorted(items, key=key, reverse=reverse)


def paginate(items: list[Recommendation], page: int, page_size: int) -> tuple[list[Recommendation], dict[str, int]]:
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


def query_recommendations(items: list[Recommendation], params: dict[str, Any]) -> tuple[list[Recommendation], dict[str, int]]:
    filtered = filter_recommendations(
        items,
        category=parse_category(params.get("category")),
        priority=parse_enum(params.get("priority"), PRIORITIES),
        impact=parse_enum(params.get("impact"), IMPACTS),
        effort=parse_enum(params.get("effort"), EFFORTS),
        status=parse_enum(params.get("status"), STATUSES),
        search=parse_search(params.get("search")),
    )
    sorted_items = sort_recommendations(filtered, parse_sort(params.get("sort")), parse_order(params.get("order")))
    return paginate(sorted_items, parse_page(params.get("page")), parse_page_size(params.get("page_size")))
