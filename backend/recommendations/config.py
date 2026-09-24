"""Limits and labels for the deterministic recommendations engine.

Recommendations interpret existing findings. They do not add analyzer checks.
"""

from __future__ import annotations

import os

from backend.issues.config import CATEGORY_VALUES as ISSUE_CATEGORIES


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


DEFAULT_PAGE_SIZE = _int_env("SITEBENCH_DEFAULT_RECOMMENDATION_PAGE_SIZE", 25)
MAX_PAGE_SIZE = _int_env("SITEBENCH_MAX_RECOMMENDATION_PAGE_SIZE", 100)
MAX_SEARCH_LENGTH = _int_env("SITEBENCH_MAX_RECOMMENDATION_SEARCH_LENGTH", 200)
MAX_EVIDENCE_URLS = _int_env("SITEBENCH_MAX_RECOMMENDATION_EVIDENCE_URLS", 50)
MAX_EVIDENCE_RESOURCES = _int_env("SITEBENCH_MAX_RECOMMENDATION_EVIDENCE_RESOURCES", 25)
HIGH_PAGE_IMPACT = _int_env("SITEBENCH_RECOMMENDATION_HIGH_PAGE_IMPACT", 5)
MEDIUM_PAGE_IMPACT = _int_env("SITEBENCH_RECOMMENDATION_MEDIUM_PAGE_IMPACT", 2)
HIGH_ELEMENT_IMPACT = _int_env("SITEBENCH_RECOMMENDATION_HIGH_ELEMENT_IMPACT", 20)
MEDIUM_ELEMENT_IMPACT = _int_env("SITEBENCH_RECOMMENDATION_MEDIUM_ELEMENT_IMPACT", 8)

CATEGORY_VALUES = ISSUE_CATEGORIES + ("Architecture",)
PRIORITIES = ("critical", "high", "medium", "low", "info")
IMPACTS = ("high", "medium", "low")
EFFORTS = ("small", "medium", "large")
STATUSES = ("open", "in_progress", "completed", "dismissed")
SCOPES = ("site",)

SORT_FIELDS = (
    "priority",
    "impact",
    "effort",
        "affected_pages",
        "issue_count",
        "category",
        "status",
)

METHODOLOGY = (
    "Recommendations are generated from SiteLens's deterministic analysis findings. "
    "They are intended as implementation guidance and do not guarantee specific search rankings, "
    "traffic, conversions, or other business outcomes."
)

SOURCE_TO_CATEGORY = {
    "seo": "SEO",
    "aeo": "AEO",
    "uiux": "UI/UX",
    "accessibility": "Accessibility",
    "performance": "Performance",
    "content": "Content",
    "structured_data": "Structured Data",
    "mobile": "Mobile",
    "cro": "CRO",
    "trust": "Trust",
    "architecture": "Architecture",
}
