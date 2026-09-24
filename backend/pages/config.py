"""Configurable limits for the bounded Pages Explorer crawler."""

from __future__ import annotations

import os


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


MAX_PAGES = _int_env("SITEBENCH_MAX_PAGES", 50)
MAX_DEPTH = _int_env("SITEBENCH_MAX_DEPTH", 3)
DEFAULT_PAGE_SIZE = _int_env("SITEBENCH_PAGES_PAGE_SIZE", 25)
MAX_PAGE_SIZE = _int_env("SITEBENCH_PAGES_MAX_PAGE_SIZE", 100)
MAX_SEARCH_LENGTH = _int_env("SITEBENCH_PAGES_MAX_SEARCH_LENGTH", 200)
MAX_SITEMAP_URLS = _int_env("SITEBENCH_MAX_SITEMAP_URLS", 50)
MAX_RECORDS = _int_env("SITEBENCH_MAX_PAGE_RECORDS", 500)
MAX_INTERNAL_LINKS = _int_env("SITEBENCH_MAX_INTERNAL_LINKS", 2000)

ANALYZER_KEYS = (
    "seo",
    "aeo",
    "uiux",
    "accessibility",
    "performance",
    "content",
    "structured_data",
    "mobile",
    "cro",
    "trust",
)

ANALYZER_HREFS = {
    "seo": "seo",
    "aeo": "aeo",
    "uiux": "uiux",
    "accessibility": "accessibility",
    "performance": "performance",
    "content": "content",
    "structured_data": "structured-data",
    "mobile": "mobile",
    "cro": "cro",
    "trust": "trust",
}

ANALYZER_LABELS = {
    "seo": "SEO",
    "aeo": "AEO",
    "uiux": "UI/UX",
    "accessibility": "Accessibility",
    "performance": "Performance",
    "content": "Content",
    "structured_data": "Structured Data",
    "mobile": "Mobile",
    "cro": "CRO",
    "trust": "Trust & Credibility",
}

PAGE_TYPE_FILTERS = (
    "homepage",
    "article",
    "blog",
    "product",
    "service",
    "contact",
    "about",
    "login",
    "listing",
    "search",
    "application",
    "unknown",
)

CRAWL_STATUS_FILTERS = ("crawled", "failed", "skipped", "queued", "crawling", "discovered")

HTTP_CLASS_FILTERS = ("2xx", "3xx", "4xx", "5xx")

TYPE_ALIASES = {
    "article": frozenset({"article", "blog"}),
    "blog": frozenset({"blog", "article"}),
    "login": frozenset({"login", "signup"}),
    "signup": frozenset({"login", "signup"}),
    "login / signup": frozenset({"login", "signup"}),
}

PAGE_TYPE_LABELS = {
    "homepage": "Homepage",
    "article": "Article",
    "blog": "Blog",
    "product": "Product",
    "service": "Service",
    "contact": "Contact",
    "about": "About",
    "login": "Login / Signup",
    "signup": "Login / Signup",
    "listing": "Listing",
    "search": "Search",
    "application": "Application",
    "unknown": "Unknown",
}

SORT_FIELDS = (
    "url",
    "title",
    "page_type",
    "http_status",
    "response_time",
    "word_count",
    "issue_count",
    "crawl_status",
)
