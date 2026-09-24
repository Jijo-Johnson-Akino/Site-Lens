"""Configurable CRO thresholds. Heuristic signals only — not conversion rates."""

from __future__ import annotations

import os

from backend.analyzers.uiux.config import VIEWPORTS


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


FORM_FIELD_WARNING_THRESHOLD = _int_env("SITEBENCH_CRO_FORM_FIELD_WARNING", 5)
FORM_FIELD_HIGH_THRESHOLD = _int_env("SITEBENCH_CRO_FORM_FIELD_HIGH", 8)
CTA_TEXT_MIN_LENGTH = _int_env("SITEBENCH_CRO_CTA_TEXT_MIN_LENGTH", 3)
COMPETING_CTA_THRESHOLD = _int_env("SITEBENCH_CRO_COMPETING_CTA", 4)
NAV_ITEM_WARNING = _int_env("SITEBENCH_CRO_NAV_ITEM_WARNING", 12)
PRIMARY_CTA_MIN_CONFIDENCE = _int_env("SITEBENCH_CRO_PRIMARY_CONFIDENCE", 5)
OVERLAY_COVER_THRESHOLD = 0.5
MAX_CTAS = _int_env("SITEBENCH_CRO_MAX_CTAS", 24)
MAX_FORMS = _int_env("SITEBENCH_CRO_MAX_FORMS", 8)

DESKTOP_VIEWPORT = (VIEWPORTS["desktop"]["width"], VIEWPORTS["desktop"]["height"])
TABLET_VIEWPORT = (VIEWPORTS["tablet"]["width"], VIEWPORTS["tablet"]["height"])
MOBILE_VIEWPORT = (VIEWPORTS["mobile"]["width"], VIEWPORTS["mobile"]["height"])

CATEGORY_WEIGHTS: dict[str, int] = {
    "primary_cta": 20,
    "cta_clarity": 10,
    "value_proposition": 15,
    "forms": 15,
    "conversion_path": 15,
    "navigation": 5,
    "pricing": 5,
    "contact": 5,
    "mobile": 5,
    "interaction": 5,
}

CATEGORY_LABELS: dict[str, str] = {
    "primary_cta": "Primary CTA",
    "cta_clarity": "CTA Clarity",
    "value_proposition": "Value Proposition",
    "forms": "Forms",
    "conversion_path": "Conversion Path",
    "navigation": "Navigation Friction",
    "pricing": "Pricing / Offer",
    "contact": "Contact Opportunities",
    "mobile": "Mobile Conversion",
    "interaction": "Interaction Friction",
}

METHODOLOGY = (
    "SiteLens CRO analysis evaluates observable website elements that may influence conversion "
    "friction and action clarity. It does not measure actual conversion rates or guarantee business outcomes."
)
CRAWL_NOTE = "Results are based on pages and interactions observable within the SiteLens crawl."
SCORE_NOTE = "SiteLens CRO score reflects observable conversion-related website signals."
LIMITATIONS = [
    "CRO analysis does not measure actual conversion rates, revenue, or predicted business outcomes.",
    "Viewport visibility is measured only on pages rendered in the SiteLens browser session.",
    "Forms are inspected, not submitted.",
]

CONVERSION_PAGE_TYPES = frozenset({"contact", "signup", "login", "pricing", "product", "service"})
QUOTE_PAGE_TYPES = frozenset({"service", "product", "pricing", "homepage"})
VP_PAGE_TYPES = frozenset({"homepage", "product", "service", "pricing"})
FORM_PAGE_TYPES = frozenset({"contact", "signup", "login"})
OPTIONAL_CTA_TYPES = frozenset({"article", "blog", "about", "unknown"})
