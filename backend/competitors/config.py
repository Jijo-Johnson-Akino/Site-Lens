"""Limits and copy for competitor benchmarking. No ranking scores."""

from __future__ import annotations

import os

from backend.analyzers.uiux.config import VIEWPORTS
from backend.pages.config import MAX_DEPTH, MAX_PAGES

METHODOLOGY_VERSION = "16"

METHODOLOGY = (
    "Competitor benchmarking compares websites using SiteLens's observable analysis. "
    "Each website is independently crawled and analyzed using the configured SiteLens limits and environment."
)
LIMITATIONS = (
    "Results represent measurements from the SiteLens scan and should not be interpreted as search rankings, "
    "traffic estimates, conversion rates, or business-performance predictions."
)
LIMIT_NOTE_TEMPLATE = "Up to {max_competitors} competitors can be benchmarked per scan."
SCOPE_NOTE_TEMPLATE = (
    "All sites were analyzed with the same SiteLens crawl limits: up to {max_pages} pages and depth {max_depth}."
)

MAX_NAME_LENGTH = 80
MAX_URL_LENGTH = 2048
MAX_ISSUE_ROWS = 80
MAX_OBSERVATIONS = 8
STALE_SECONDS = 24 * 60 * 60

STATUSES = ("queued", "scanning", "completed", "failed", "cancelled")

ANALYZER_CATEGORIES = (
    ("seo", "SEO"),
    ("aeo", "AEO"),
    ("uiux", "UI/UX"),
    ("accessibility", "Accessibility"),
    ("performance", "Performance"),
    ("content", "Content"),
    ("structured_data", "Structured Data"),
    ("mobile", "Mobile"),
)

ISSUE_LABELS = {
    "seo.title.missing": "Missing titles",
    "seo.meta_description.missing": "Missing meta descriptions",
    "seo.canonical.missing": "Missing canonical URLs",
    "seo.can.002": "Canonical issues",
    "seo.img.001": "Images missing alt text",
    "aeo.entity.organization.missing": "Missing Organization entity",
    "aeo.answer.001": "Direct answer structure",
    "aeo.question.001": "Question headings",
    "accessibility.form.label.missing": "Form label issues",
    "accessibility.img.001": "Accessibility alt text",
    "accessibility.contrast.001": "Color contrast findings",
    "performance.image.large": "Large images",
    "performance.javascript.large_payload": "Large JavaScript payloads",
    "content.thin_page": "Thin page content",
    "structured_data.invalid_jsonld": "Invalid JSON-LD",
    "mobile.touch_target.small": "Small touch targets",
    "mobile.horizontal_overflow": "Mobile horizontal overflow",
}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


MAX_COMPETITORS = max(1, min(5, _int_env("SITEBENCH_MAX_COMPETITORS", 5)))


def methodology_snapshot() -> dict:
    return {
        "version": METHODOLOGY_VERSION,
        "max_pages": MAX_PAGES,
        "max_depth": MAX_DEPTH,
        "viewports": {name: dict(size) for name, size in VIEWPORTS.items()},
    }


def limit_note() -> str:
    return LIMIT_NOTE_TEMPLATE.format(max_competitors=MAX_COMPETITORS)


def scope_note(max_pages: int | None = None, max_depth: int | None = None) -> str:
    return SCOPE_NOTE_TEMPLATE.format(
        max_pages=max_pages if max_pages is not None else MAX_PAGES,
        max_depth=max_depth if max_depth is not None else MAX_DEPTH,
    )
