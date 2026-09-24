from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.pages.models import PageRecord


@dataclass
class PageCroContext:
    page: PageRecord
    url: str
    page_type: str
    signals: dict[str, Any]
    ctas: list[dict[str, Any]]
    forms: list[dict[str, Any]]
    desktop: dict[str, Any] | None = None
    mobile: dict[str, Any] | None = None
    a11y_form_label_issue: bool = False
    site_has_contact: bool = False
    site_has_conversion_page: bool = False
    conversion_path: list[dict[str, Any]] = field(default_factory=list)
    rendered: bool = False
    mobile_rendered: bool = False
    nav_links: int | None = None
    overlays: list[dict[str, Any]] = field(default_factory=list)
    mobile_forms_overflow: bool = False
    mobile_cta: dict[str, Any] = field(default_factory=dict)
