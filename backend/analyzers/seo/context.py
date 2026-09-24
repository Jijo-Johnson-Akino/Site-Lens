from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeoContext:
    """Raw website data already collected by the scan engine. No extra HTTP."""

    page_url: str
    final_url: str
    status_code: int | None
    html: dict
    x_robots_tag: str | None
    robots_txt: dict
    sitemap: dict
