"""Page records for Pages Explorer. Crawl metadata only — no invented scores."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CrawlStatus = Literal["discovered", "queued", "crawling", "crawled", "failed", "skipped"]
DiscoveryMethod = Literal["seed", "internal_link", "sitemap", "canonical", "other"]


class PageRecord(BaseModel):
    id: str
    scan_id: str
    url: str
    normalized_url: str
    final_url: str | None = None
    depth: int = 0
    discovered_from: str | None = None
    discovery_method: DiscoveryMethod = "other"
    crawl_status: CrawlStatus = "discovered"
    http_status: int | None = None
    content_type: str | None = None
    response_time_ms: int | None = None
    response_size_bytes: int | None = None
    title: str | None = None
    meta_description: str | None = None
    h1: str | None = None
    h1_count: int | None = None
    h2_count: int | None = None
    canonical_url: str | None = None
    indexable: bool | None = None
    robots_directive: str | None = None
    language: str | None = None
    word_count: int | None = None
    page_type: str | None = None
    page_type_label: str | None = None
    page_type_confidence: float | None = None
    internal_link_count: int | None = None
    external_link_count: int | None = None
    image_count: int | None = None
    paragraph_count: int | None = None
    list_count: int | None = None
    schema_types: list[str] = Field(default_factory=list)
    headings: list[dict[str, Any]] = Field(default_factory=list)
    failure_reason: str | None = None
    skip_reason: str | None = None
    related_issue_ids: list[str] = Field(default_factory=list)
    issue_count: int = 0
    severity_counts: dict[str, int] = Field(
        default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    )
    available_analyzers: list[str] = Field(default_factory=list)
    analyzer_scores: dict[str, int | None] = Field(default_factory=dict)
    cro_signals: dict[str, Any] = Field(default_factory=dict)
    trust_signals: dict[str, Any] = Field(default_factory=dict)
    is_seed: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class InternalLink(BaseModel):
    id: str
    scan_id: str
    source_page_id: str
    destination_page_id: str
    source_url: str
    destination_url: str
    anchor_text: str | None = None
    rel: str | None = None
    created_at: str | None = None


class PagesSummary(BaseModel):
    discovered: int = 0
    crawled: int = 0
    failed: int = 0
    skipped: int = 0
    queued: int = 0
    internal_pages: int = 0
    external_links_discovered: int = 0
    max_depth_reached: int = 0
    max_pages: int = 0
    max_depth: int = 0
    page_limit_reached: bool = False
    depth_limit_reached: bool = False


class PagesPayload(BaseModel):
    version: int = 1
    summary: PagesSummary = Field(default_factory=PagesSummary)
    limits: dict[str, int] = Field(default_factory=dict)
    items: list[PageRecord] = Field(default_factory=list)
    internal_links: list[InternalLink] = Field(default_factory=list)
    internal_links_recorded: bool = False
    in_progress: bool = False
