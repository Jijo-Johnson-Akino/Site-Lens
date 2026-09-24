from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.pages.models import PageRecord


@dataclass
class PageTrustContext:
    page: PageRecord
    url: str
    page_type: str
    signals: dict[str, Any]
    schema_entities: list[dict[str, Any]] = field(default_factory=list)
    content_authors: list[str] = field(default_factory=list)
    content_dates: list[str] = field(default_factory=list)
    https: bool = False
    site_host: str = ""
    current_year: int = 0
    is_seed: bool = False


@dataclass
class SiteTrustContext:
    seed_url: str
    seed_page_id: str | None
    host: str
    https: bool
    current_year: int
    pages: list[PageTrustContext]
    org_names: dict[str, str] = field(default_factory=dict)
    emails: list[str] = field(default_factory=list)
    email_pages: dict[str, str] = field(default_factory=dict)
    phones: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    about_pages: list[dict[str, Any]] = field(default_factory=list)
    about_links: list[dict[str, Any]] = field(default_factory=list)
    contact_pages: list[dict[str, Any]] = field(default_factory=list)
    contact_forms: bool = False
    policies: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    social_profiles: list[dict[str, str]] = field(default_factory=list)
    schema_types: set[str] = field(default_factory=set)
    schema_entities: list[dict[str, Any]] = field(default_factory=list)
    logo: bool = False
    hours: list[str] = field(default_factory=list)
    identifiers: list[str] = field(default_factory=list)
    copyright_years: list[int] = field(default_factory=list)
    has_product: bool = False
    has_articles: bool = False
    has_login: bool = False
    citations: bool = False
    methodology: bool = False
    footer_present: bool = False
    article_count: int = 0
    articles_with_author: int = 0
    articles_with_date: int = 0
    latest_date: str | None = None
