"""Limits and copy for Website Architecture. No scores."""

from __future__ import annotations

import os

from backend.pages.config import PAGE_TYPE_LABELS


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


MAX_GRAPH_NODES = _int_env("SITEBENCH_MAX_GRAPH_NODES", 100)
DEFAULT_PAGE_SIZE = _int_env("SITEBENCH_ARCHITECTURE_PAGE_SIZE", 25)
MAX_PAGE_SIZE = _int_env("SITEBENCH_ARCHITECTURE_MAX_PAGE_SIZE", 100)
MAX_SEARCH_LENGTH = _int_env("SITEBENCH_ARCHITECTURE_MAX_SEARCH_LENGTH", 200)
MAX_DETAIL_NEIGHBORS = _int_env("SITEBENCH_ARCHITECTURE_MAX_NEIGHBORS", 100)
MAX_URL_TREE_NODES = _int_env("SITEBENCH_ARCHITECTURE_MAX_URL_NODES", 200)

TERMINAL_PAGE_TYPES = frozenset({"contact", "login", "signup"})

SORT_FIELDS = (
    "url",
    "depth",
    "inbound",
    "outbound",
    "issue_count",
    "page_type",
    "crawl_status",
)

LINK_SORT_FIELDS = ("source", "destination", "anchor", "destination_type")

METHODOLOGY = (
    "Website Architecture reflects pages and internal links observed during the SiteLens crawl. "
    "Pages outside the crawl scope, blocked pages, authenticated areas, dynamically inaccessible routes, "
    "and links not observable during crawling may not be represented."
)
ORPHAN_NOTE = (
    "Potential orphan pages are pages with no inbound internal links within the crawled graph."
)
LINKS_NOTE = "Architecture reflects links observed during the crawl."
DEPTH_NOTE = (
    "Crawl depth is the discovery distance from the seed URL. URL path depth counts path segments "
    "and is not the same measurement."
)

PAGE_TYPE_LABELS = PAGE_TYPE_LABELS
