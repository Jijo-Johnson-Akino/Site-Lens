"""Bounded same-origin BFS crawler for Pages Explorer.

Reuses WebsiteFetcher SSRF, redirect, timeout, and size limits.
Does not run analyzers or execute page actions.
"""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from backend.errors import ScanError
from backend.pages.config import MAX_DEPTH, MAX_INTERNAL_LINKS, MAX_PAGES, MAX_RECORDS, MAX_SITEMAP_URLS
from backend.pages.discover import (
    discover_from_page,
    extract_internal_link_edges,
    html_data_from_source,
    parse_sitemap_locs,
)
from backend.pages.ids import make_link_id, make_page_id
from backend.pages.metadata import apply_html
from backend.pages.models import InternalLink, PageRecord, PagesPayload, PagesSummary
from backend.pages.reasons import SKIP_DEPTH_LIMIT, SKIP_PAGE_LIMIT, classify_fetch_error
from backend.services.url_identity import hostname_of, is_skippable_resource, normalize_page_url, same_site
from backend.services.url_validator import safe_display_url

logger = logging.getLogger("sitebench.pages")

ProgressCallback = Callable[[PagesPayload], None]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp(record: PageRecord) -> PageRecord:
    now = _now()
    if not record.created_at:
        record.created_at = now
    record.updated_at = now
    return record


class SiteCrawler:
    def __init__(
        self,
        *,
        scan_id: str,
        seed_url: str,
        fetcher,
        allowed_host: str,
        max_pages: int = MAX_PAGES,
        max_depth: int = MAX_DEPTH,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self.scan_id = scan_id
        self.seed_url = seed_url
        self.fetcher = fetcher
        self.allowed_host = allowed_host.lower()
        self.max_pages = max(1, max_pages)
        self.max_depth = max(0, max_depth)
        self.on_progress = on_progress
        self.records: dict[str, PageRecord] = {}
        self.links: dict[str, InternalLink] = {}
        self.queue: deque[str] = deque()
        self.external: set[str] = set()
        self.page_limit_reached = False
        self.depth_limit_reached = False
        self.crawled_count = 0

    def _budget_remaining(self) -> int:
        return max(0, self.max_pages - self.crawled_count)

    def snapshot(self, *, in_progress: bool) -> PagesPayload:
        items = list(self.records.values())
        crawled = sum(1 for item in items if item.crawl_status == "crawled")
        failed = sum(1 for item in items if item.crawl_status == "failed")
        skipped = sum(1 for item in items if item.crawl_status == "skipped")
        queued = sum(1 for item in items if item.crawl_status in {"queued", "crawling", "discovered"})
        depths = [item.depth for item in items]
        summary = PagesSummary(
            discovered=len(items),
            crawled=crawled,
            failed=failed,
            skipped=skipped,
            queued=queued,
            internal_pages=len(items),
            external_links_discovered=len(self.external),
            max_depth_reached=max(depths) if depths else 0,
            max_pages=self.max_pages,
            max_depth=self.max_depth,
            page_limit_reached=self.page_limit_reached,
            depth_limit_reached=self.depth_limit_reached,
        )
        return PagesPayload(
            summary=summary,
            limits={"max_pages": self.max_pages, "max_depth": self.max_depth},
            items=items,
            internal_links=list(self.links.values()),
            internal_links_recorded=True,
            in_progress=in_progress,
        )

    def _emit(self, *, in_progress: bool = True) -> None:
        if self.on_progress:
            self.on_progress(self.snapshot(in_progress=in_progress))

    def _new_record(
        self,
        url: str,
        *,
        depth: int,
        discovered_from: str | None,
        method: str,
        status: str,
    ) -> PageRecord | None:
        normalized = normalize_page_url(url)
        if not normalized:
            return None
        if normalized in self.records:
            return None
        if len(self.records) >= MAX_RECORDS:
            self.page_limit_reached = True
            return None
        record = PageRecord(
            id=make_page_id(self.scan_id, normalized),
            scan_id=self.scan_id,
            url=url,
            normalized_url=normalized,
            depth=depth,
            discovered_from=discovered_from,
            discovery_method=method,  # type: ignore[arg-type]
            crawl_status=status,  # type: ignore[arg-type]
            is_seed=depth == 0 and method == "seed",
        )
        self.records[normalized] = _stamp(record)
        logger.info(
            "page_discovered scan_id=%s url=%s method=%s depth=%s",
            self.scan_id,
            safe_display_url(normalized),
            method,
            depth,
        )
        return record

    def consider(
        self,
        url: str,
        *,
        depth: int,
        discovered_from: str | None,
        method: str,
    ) -> None:
        if is_skippable_resource(url):
            return
        if not same_site(url, self.seed_url) or hostname_of(url) != self.allowed_host:
            key = normalize_page_url(url) or url
            self.external.add(key)
            return
        try:
            validated = self.fetcher._validator.validate(url)
        except ScanError:
            normalized = normalize_page_url(url)
            if not normalized or normalized in self.records:
                return
            record = self._new_record(
                url,
                depth=depth,
                discovered_from=discovered_from,
                method=method,
                status="skipped",
            )
            if record:
                record.skip_reason = "Disallowed destination."
                logger.info(
                    "page_skipped scan_id=%s url=%s reason=disallowed_destination",
                    self.scan_id,
                    safe_display_url(record.normalized_url),
                )
            return

        normalized = normalize_page_url(validated)
        if not normalized:
            return
        if normalized in self.records:
            return
        if depth > self.max_depth:
            self.depth_limit_reached = True
            record = self._new_record(
                validated,
                depth=depth,
                discovered_from=discovered_from,
                method=method,
                status="skipped",
            )
            if record:
                record.skip_reason = SKIP_DEPTH_LIMIT
                logger.info(
                    "page_skipped scan_id=%s url=%s reason=depth_limit depth=%s",
                    self.scan_id,
                    safe_display_url(record.normalized_url),
                    depth,
                )
                logger.info("depth_limit_reached scan_id=%s max_depth=%s", self.scan_id, self.max_depth)
            return

        queued_like = sum(1 for item in self.records.values() if item.crawl_status in {"queued", "crawling"})
        if self.crawled_count + queued_like >= self.max_pages:
            self.page_limit_reached = True
            record = self._new_record(
                validated,
                depth=depth,
                discovered_from=discovered_from,
                method=method,
                status="skipped",
            )
            if record:
                record.skip_reason = SKIP_PAGE_LIMIT
                logger.info(
                    "page_skipped scan_id=%s url=%s reason=page_limit",
                    self.scan_id,
                    safe_display_url(record.normalized_url),
                )
                logger.info("crawl_limit_reached scan_id=%s max_pages=%s", self.scan_id, self.max_pages)
            return

        record = self._new_record(
            validated,
            depth=depth,
            discovered_from=discovered_from,
            method=method,
            status="queued",
        )
        if record:
            logger.info(
                "page_queued scan_id=%s url=%s depth=%s",
                self.scan_id,
                safe_display_url(record.normalized_url),
                depth,
            )
            self.queue.append(normalized)

    def _record_edges(self, record: PageRecord, html_data: dict, base_url: str) -> None:
        if len(self.links) >= MAX_INTERNAL_LINKS:
            return
        for edge in extract_internal_link_edges(html_data, base_url=base_url, seed_url=self.seed_url):
            destination_url = edge.get("destination_url") or ""
            destination = self.records.get(destination_url)
            if destination is None or destination.id == record.id:
                continue
            anchor = edge.get("anchor_text")
            link_id = make_link_id(self.scan_id, record.id, destination.id, anchor)
            if link_id in self.links:
                continue
            if len(self.links) >= MAX_INTERNAL_LINKS:
                break
            self.links[link_id] = InternalLink(
                id=link_id,
                scan_id=self.scan_id,
                source_page_id=record.id,
                destination_page_id=destination.id,
                source_url=record.normalized_url,
                destination_url=destination.normalized_url,
                anchor_text=anchor,
                rel=edge.get("rel"),
                created_at=_now(),
            )

    def _harvest(self, record: PageRecord, html_data: dict, base_url: str) -> None:
        candidates, external = discover_from_page(html_data, base_url=base_url, seed_url=self.seed_url)
        for href in external:
            self.external.add(normalize_page_url(href) or href)
        for url, method in candidates:
            self.consider(
                url,
                depth=record.depth + 1,
                discovered_from=record.normalized_url,
                method=method,
            )
        self._record_edges(record, html_data, base_url)

    def ingest_seed(
        self,
        *,
        seed_fetch: dict[str, Any],
        seed_html: str,
        seed_html_data: dict,
        sitemap_body: str | None = None,
    ) -> PageRecord:
        final_url = seed_fetch.get("final_url") or self.seed_url
        record = self._new_record(
            final_url,
            depth=0,
            discovered_from=None,
            method="seed",
            status="crawled",
        )
        if record is None:
            existing = self.records[normalize_page_url(final_url)]
            record = existing
        record.url = self.seed_url
        record.final_url = final_url
        record.http_status = seed_fetch.get("status_code")
        record.content_type = seed_fetch.get("content_type")
        record.response_time_ms = seed_fetch.get("response_time_ms")
        record.response_size_bytes = seed_fetch.get("html_size_bytes")
        record.crawl_status = "crawled"
        record.is_seed = True
        apply_html(
            record,
            html_source=seed_html,
            html_data=seed_html_data,
            page_url=final_url,
            x_robots_tag=seed_fetch.get("x_robots_tag"),
        )
        _stamp(record)
        self.crawled_count = 1
        logger.info(
            "page_crawled scan_id=%s url=%s status=%s",
            self.scan_id,
            safe_display_url(record.normalized_url),
            record.http_status,
        )
        self._harvest(record, seed_html_data, final_url)
        if sitemap_body:
            for loc in parse_sitemap_locs(sitemap_body, limit=MAX_SITEMAP_URLS):
                self.consider(loc, depth=1, discovered_from=record.normalized_url, method="sitemap")
        self._emit()
        return record

    async def _crawl_one(self, key: str) -> None:
        record = self.records.get(key)
        if record is None or record.crawl_status not in {"queued", "discovered"}:
            return
        if self.crawled_count >= self.max_pages:
            self.page_limit_reached = True
            record.crawl_status = "skipped"
            record.skip_reason = SKIP_PAGE_LIMIT
            _stamp(record)
            logger.info(
                "page_skipped scan_id=%s url=%s reason=page_limit",
                self.scan_id,
                safe_display_url(record.normalized_url),
            )
            return
        record.crawl_status = "crawling"
        _stamp(record)
        try:
            fetched = await self.fetcher.fetch_document(record.url, allowed_host=self.allowed_host)
        except ScanError as exc:
            status, reason = classify_fetch_error(exc)
            record.crawl_status = status  # type: ignore[assignment]
            if status == "skipped":
                record.skip_reason = reason
                logger.info(
                    "page_skipped scan_id=%s url=%s reason=%s",
                    self.scan_id,
                    safe_display_url(record.normalized_url),
                    exc.code.lower(),
                )
            else:
                record.failure_reason = reason
                logger.info(
                    "page_failed scan_id=%s url=%s reason=%s",
                    self.scan_id,
                    safe_display_url(record.normalized_url),
                    exc.code.lower(),
                )
            _stamp(record)
            return
        except Exception:
            logger.exception("page_failed scan_id=%s url=%s", self.scan_id, safe_display_url(record.normalized_url))
            record.crawl_status = "failed"
            record.failure_reason = "The page could not be retrieved."
            _stamp(record)
            return

        html = fetched.get("html") or ""
        html_data = html_data_from_source(html)
        final_url = fetched.get("final_url") or record.url
        record.final_url = final_url
        record.http_status = fetched.get("status_code")
        record.content_type = fetched.get("content_type")
        record.response_time_ms = fetched.get("response_time_ms")
        record.response_size_bytes = fetched.get("html_size_bytes")
        record.crawl_status = "crawled"
        apply_html(
            record,
            html_source=html,
            html_data=html_data,
            page_url=final_url,
            x_robots_tag=fetched.get("x_robots_tag"),
        )
        _stamp(record)
        self.crawled_count += 1
        logger.info(
            "page_crawled scan_id=%s url=%s status=%s",
            self.scan_id,
            safe_display_url(record.normalized_url),
            record.http_status,
        )
        self._harvest(record, html_data, final_url)

    def _flush_queue_limits(self) -> None:
        while self.queue:
            key = self.queue.popleft()
            record = self.records.get(key)
            if record is None or record.crawl_status not in {"queued", "discovered", "crawling"}:
                continue
            record.crawl_status = "skipped"
            if record.depth > self.max_depth:
                record.skip_reason = SKIP_DEPTH_LIMIT
                self.depth_limit_reached = True
            else:
                record.skip_reason = SKIP_PAGE_LIMIT
                self.page_limit_reached = True
            _stamp(record)

    async def run(self) -> PagesPayload:
        while self.queue and self.crawled_count < self.max_pages:
            key = self.queue.popleft()
            await self._crawl_one(key)
            self._emit()
        if self.queue:
            self.page_limit_reached = True
            logger.info("crawl_limit_reached scan_id=%s max_pages=%s", self.scan_id, self.max_pages)
            self._flush_queue_limits()
        self._emit(in_progress=False)
        return self.snapshot(in_progress=False)


async def crawl_site(
    *,
    scan_id: str,
    seed_url: str,
    seed_fetch: dict[str, Any],
    seed_html: str,
    seed_html_data: dict,
    fetcher,
    allowed_host: str,
    sitemap_body: str | None = None,
    max_pages: int = MAX_PAGES,
    max_depth: int = MAX_DEPTH,
    on_progress: ProgressCallback | None = None,
) -> PagesPayload:
    host = (allowed_host or hostname_of(seed_url)).lower()
    crawler = SiteCrawler(
        scan_id=scan_id,
        seed_url=seed_url,
        fetcher=fetcher,
        allowed_host=host,
        max_pages=max_pages,
        max_depth=max_depth,
        on_progress=on_progress,
    )
    crawler.ingest_seed(
        seed_fetch=seed_fetch,
        seed_html=seed_html,
        seed_html_data=seed_html_data,
        sitemap_body=sitemap_body,
    )
    return await crawler.run()
