from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.analyzers.content.models import ContentPageType


@dataclass(frozen=True)
class StructuredDataContext:
    """Homepage HTML already fetched by the scan. No extra HTTP from schema checks."""

    page_url: str
    final_url: str
    html: dict
    html_source: str
    page_type: ContentPageType | None = None
    parsed: dict[str, Any] | None = None
