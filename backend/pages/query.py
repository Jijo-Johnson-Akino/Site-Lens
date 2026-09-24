"""Filter, search, sort, and paginate page records. Bounded, parameterized-style."""

from __future__ import annotations

from typing import Any

from backend.pages.config import (
    CRAWL_STATUS_FILTERS,
    DEFAULT_PAGE_SIZE,
    HTTP_CLASS_FILTERS,
    MAX_PAGE_SIZE,
    MAX_SEARCH_LENGTH,
    PAGE_TYPE_FILTERS,
    SORT_FIELDS,
    TYPE_ALIASES,
)
from backend.pages.models import PageRecord


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
    value = str(raw or "issue_count").strip().lower()
    aliases = {
        "response_time_ms": "response_time",
        "response_time": "response_time",
        "issues": "issue_count",
        "status": "crawl_status",
        "type": "page_type",
        "http": "http_status",
    }
    mapped = aliases.get(value, value)
    return mapped if mapped in SORT_FIELDS else "issue_count"


def parse_order(raw: Any) -> str:
    value = str(raw or "desc").strip().lower()
    return "asc" if value == "asc" else "desc"


def parse_page_type(raw: Any) -> str | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower().replace("-", " ").replace("_", " ")
    compact = value.replace(" ", "")
    for item in PAGE_TYPE_FILTERS:
        if item == value or item.replace(" ", "") == compact:
            return item
    if compact in {"login/signup", "loginsignup"}:
        return "login"
    return None


def parse_crawl_status(raw: Any) -> str | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower()
    return value if value in CRAWL_STATUS_FILTERS else None


def parse_http_status(raw: Any) -> str | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower()
    if value in HTTP_CLASS_FILTERS:
        return value
    try:
        code = int(value)
    except ValueError:
        return None
    if 100 <= code <= 599:
        return str(code)
    return None


def parse_indexable(raw: Any) -> str | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower()
    if value in {"true", "1", "yes", "indexable"}:
        return "true"
    if value in {"false", "0", "no", "noindex"}:
        return "false"
    if value in {"unknown", "null", "none"}:
        return "unknown"
    return None


def parse_has_issues(raw: Any) -> bool | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower()
    if value in {"true", "1", "yes", "has_issues", "issues"}:
        return True
    if value in {"false", "0", "no", "none", "no_issues"}:
        return False
    return None


def _http_matches(code: int | None, needle: str) -> bool:
    if needle in HTTP_CLASS_FILTERS:
        if code is None:
            return False
        bucket = f"{code // 100}xx"
        return bucket == needle
    try:
        return code == int(needle)
    except ValueError:
        return False


def _type_matches(page: PageRecord, needle: str) -> bool:
    actual = (page.page_type or "unknown").lower()
    aliases = TYPE_ALIASES.get(needle, frozenset({needle}))
    return actual in aliases


def filter_pages(
    pages: list[PageRecord],
    *,
    search: str = "",
    page_type: str | None = None,
    crawl_status: str | None = None,
    http_status: str | None = None,
    indexable: str | None = None,
    has_issues: bool | None = None,
) -> list[PageRecord]:
    needle = search.strip().lower()
    selected: list[PageRecord] = []
    for page in pages:
        if page_type and not _type_matches(page, page_type):
            continue
        if crawl_status and page.crawl_status != crawl_status:
            continue
        if http_status and not _http_matches(page.http_status, http_status):
            continue
        if indexable == "true" and page.indexable is not True:
            continue
        if indexable == "false" and page.indexable is not False:
            continue
        if indexable == "unknown" and page.indexable is not None:
            continue
        if has_issues is True and page.issue_count <= 0:
            continue
        if has_issues is False and page.issue_count > 0:
            continue
        if needle:
            blob = " ".join(
                filter(
                    None,
                    [
                        page.url,
                        page.normalized_url,
                        page.final_url or "",
                        page.title or "",
                        page.h1 or "",
                    ],
                )
            ).lower()
            if needle not in blob:
                continue
        selected.append(page)
    return selected


def _sort_value(page: PageRecord, sort: str) -> Any:
    if sort == "url":
        return (page.normalized_url or page.url).lower()
    if sort == "title":
        return (page.title or "").lower()
    if sort == "page_type":
        return (page.page_type or "unknown").lower()
    if sort == "http_status":
        return page.http_status if page.http_status is not None else -1
    if sort == "response_time":
        return page.response_time_ms if page.response_time_ms is not None else -1
    if sort == "word_count":
        return page.word_count if page.word_count is not None else -1
    if sort == "crawl_status":
        return page.crawl_status
    return page.issue_count


def sort_pages(pages: list[PageRecord], sort: str, order: str) -> list[PageRecord]:
    reverse = order != "asc"

    def key(page: PageRecord) -> tuple:
        primary = _sort_value(page, sort)
        return (primary, page.issue_count, (page.normalized_url or page.url).lower())

    return sorted(pages, key=key, reverse=reverse)


def paginate(items: list[PageRecord], page: int, page_size: int) -> tuple[list[PageRecord], dict[str, int]]:
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
        "total_pages": pages,
    }


def query_pages(
    pages: list[PageRecord],
    params: dict[str, Any],
) -> tuple[list[PageRecord], dict[str, int]]:
    filtered = filter_pages(
        pages,
        search=parse_search(params.get("search")),
        page_type=parse_page_type(params.get("page_type")),
        crawl_status=parse_crawl_status(params.get("crawl_status")),
        http_status=parse_http_status(params.get("http_status")),
        indexable=parse_indexable(params.get("indexable")),
        has_issues=parse_has_issues(params.get("has_issues")),
    )
    sorted_items = sort_pages(filtered, parse_sort(params.get("sort")), parse_order(params.get("order")))
    return paginate(sorted_items, parse_page(params.get("page")), parse_page_size(params.get("page_size")))
