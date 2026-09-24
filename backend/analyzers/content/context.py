from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtraPage:
    url: str
    html_source: str


@dataclass(frozen=True)
class ContentContext:
    """Primary-page HTML already fetched by the scan. No extra HTTP from checks."""

    page_url: str
    final_url: str
    html: dict
    html_source: str
    extra_pages: tuple[ExtraPage, ...] = field(default_factory=tuple)
