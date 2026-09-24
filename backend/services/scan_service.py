"""Orchestrates a homepage scan, then runs SEO, AEO, UI/UX, accessibility, performance, content, structured-data, mobile, CRO, Trust, unified issues aggregation, recommendations, and overall scoring."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from backend.analyzers.accessibility.analyzer import PlaywrightA11yAnalyzer
from backend.analyzers.aeo import analyze_aeo
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.content import analyze_content
from backend.analyzers.content.context import ContentContext
from backend.analyzers.cro import analyze_cro
from backend.analyzers.trust import analyze_trust
from backend.analyzers.mobile.analyzer import PlaywrightMobileAnalyzer
from backend.analyzers.structured_data import analyze_structured_data
from backend.analyzers.structured_data.context import StructuredDataContext
from backend.analyzers.performance.analyzer import PlaywrightPerfAnalyzer
from backend.analyzers.seo import analyze_seo
from backend.analyzers.seo.context import SeoContext
from backend.analyzers.uiux.analyzer import PlaywrightUiuxAnalyzer
from backend.config import MAX_CONCURRENT_SCANS
from backend.errors import ScanError
from backend.issues.engine import aggregate
from backend.issues.capture import IssueCaptureEngine
from backend.issues.models import IssuesPayload
from backend.store.issue_screenshots import IssueScreenshotStore
from backend.pages.config import MAX_DEPTH, MAX_PAGES
from backend.competitors.config import methodology_snapshot
from backend.recommendations.engine import apply_status, generate, payload_from_result as recommendations_from_result
from backend.recommendations.config import STATUSES as RECOMMENDATION_STATUSES
from backend.scoring.repository import attach_health
from backend.pages.crawler import SiteCrawler, crawl_site
from backend.pages.engine import attach_analyzers, attach_issues
from backend.parser.html_parser import parse_html
from backend.schemas.scan import ScanRecord
from backend.services.url_identity import hostname_of
from backend.services.url_validator import UrlValidator, safe_display_url
from backend.services.website_fetcher import WebsiteFetcher
from backend.store.scans import InMemoryScanStore, ScanRepository
from backend.store.screenshots import InMemoryScreenshotStore, ScreenshotRepository

logger = logging.getLogger("sitebench.scan")

STEPS = [
    (0, "Validating website"),
    (15, "Connecting"),
    (30, "Fetching homepage"),
    (40, "Parsing website"),
    (45, "Discovering pages"),
    (50, "SEO analysis"),
    (65, "AEO analysis"),
    (75, "Rendering website"),
    (82, "UI/UX analysis"),
    (88, "Capturing screenshots"),
    (92, "Accessibility analysis"),
    (96, "Performance analysis"),
    (97, "Content analysis"),
    (98, "Structured Data Analysis"),
    (99, "Mobile Analysis"),
    (99, "CRO Analysis"),
    (99, "Trust & Credibility Analysis"),
    (99, "Aggregating Issues"),
    (99, "Generating Recommendations"),
    (99, "Calculating Health Score"),
    (100, "Analysis complete"),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _new_id() -> str:
    return f"scan_{uuid4().hex}"


def _probe_public(probe: dict) -> dict:
    return {
        "exists": bool(probe.get("exists")),
        "status_code": probe.get("status_code"),
    }


class ScanService:
    def __init__(
        self,
        store: ScanRepository | None = None,
        validator: UrlValidator | None = None,
        fetcher: WebsiteFetcher | None = None,
        uiux_analyzer=None,
        a11y_analyzer=None,
        perf_analyzer=None,
        content_analyzer=None,
        schema_analyzer=None,
        mobile_analyzer=None,
        screenshot_store: ScreenshotRepository | None = None,
        issue_screenshot_store: IssueScreenshotStore | None = None,
        issue_capture: IssueCaptureEngine | None = None,
    ) -> None:
        self._store = store or InMemoryScanStore()
        self._validator = validator or UrlValidator()
        self._fetcher = fetcher or WebsiteFetcher(self._validator)
        self._screenshots = screenshot_store or InMemoryScreenshotStore()
        self._issue_screenshots = issue_screenshot_store or IssueScreenshotStore()
        self._issue_capture = issue_capture or IssueCaptureEngine(self._issue_screenshots)
        self._uiux = uiux_analyzer or PlaywrightUiuxAnalyzer(self._validator, self._screenshots)
        self._a11y = a11y_analyzer or PlaywrightA11yAnalyzer(self._validator)
        self._perf = perf_analyzer or PlaywrightPerfAnalyzer(self._validator)
        self._content = content_analyzer or analyze_content
        self._schema = schema_analyzer or analyze_structured_data
        self._mobile = mobile_analyzer or PlaywrightMobileAnalyzer(self._validator, self._screenshots)

    @property
    def screenshots(self) -> ScreenshotRepository:
        return self._screenshots

    @property
    def issue_screenshots(self) -> IssueScreenshotStore:
        return self._issue_screenshots

    def create(self, raw_url: str) -> ScanRecord:
        normalized = self._validator.validate(raw_url)
        active = self._active_count()
        if active >= MAX_CONCURRENT_SCANS:
            logger.info("scan_limit_reached active=%s max=%s", active, MAX_CONCURRENT_SCANS)
            raise ScanError(
                "SCAN_LIMIT",
                "SiteLens is already running the maximum number of scans. Try again shortly.",
            )
        record = ScanRecord(
            id=_new_id(),
            url=raw_url.strip(),
            normalized_url=normalized,
            status="queued",
            progress=0,
            current_step=STEPS[0][1],
            created_at=_now(),
        )
        saved = self._store.create(record)
        logger.info("scan_created scan_id=%s host=%s", saved.id, safe_display_url(normalized))
        return saved

    def get(self, scan_id: str) -> ScanRecord | None:
        return self._store.get(scan_id)

    def _active_count(self) -> int:
        count_fn = getattr(self._store, "active_count", None)
        if callable(count_fn):
            return int(count_fn())
        return 0

    def update_recommendation_status(self, scan_id: str, recommendation_id: str, status: str):
        if status not in RECOMMENDATION_STATUSES:
            return "invalid_status"
        record = self._store.get(scan_id)
        if record is None:
            return None
        if record.status == "failed":
            return "scan_failed"
        if record.status != "completed":
            return "scan_not_ready"
        created = record.created_at.isoformat() if record.created_at else None
        payload = recommendations_from_result(record.id, record.result, created)
        updated = apply_status(payload, recommendation_id, status)
        if updated is None:
            return "not_found"
        result = dict(record.result or {})
        result["recommendations"] = payload.model_dump(mode="json")
        self._update(record, result=result)
        return updated

    def _persist_issues(self, scan_id: str, payload: IssuesPayload) -> None:
        record = self._store.get(scan_id)
        if record is None or not record.result:
            return
        result = dict(record.result)
        result["issues"] = payload.model_dump(mode="json")
        self._update(record, result=result)

    def _capture_issue_screenshots(self, scan_id: str) -> None:
        record = self._store.get(scan_id)
        if record is None or record.status != "completed" or not record.result:
            return
        try:
            payload = IssuesPayload.model_validate((record.result or {}).get("issues") or {})
        except Exception:
            logger.info("issue_capture_skipped scan_id=%s reason=invalid_payload", scan_id)
            return
        try:
            self._issue_capture.attach(
                scan_id,
                payload,
                persist=lambda current: self._persist_issues(scan_id, current),
            )
        except Exception:
            logger.exception("issue_capture_failed scan_id=%s", scan_id)
            payload.screenshot_capture.status = "completed"
            self._persist_issues(scan_id, payload)

    def _update(self, record: ScanRecord, **changes) -> ScanRecord:
        updated = record.model_copy(update=changes)
        return self._store.save(updated)

    async def run(self, scan_id: str) -> None:
        record = self._store.get(scan_id)
        if record is None:
            return
        logger.info("scan_started scan_id=%s", scan_id)
        record = self._update(
            record,
            status="running",
            started_at=_now(),
            progress=0,
            current_step=STEPS[0][1],
        )
        try:
            record = self._update(record, progress=15, current_step="Connecting")
            record = self._update(record, progress=30, current_step="Fetching homepage")
            fetched = await self._fetcher.fetch_homepage(record.normalized_url)

            origin = _origin(fetched["final_url"])
            robots = await self._fetcher.fetch_probe(f"{origin}/robots.txt")
            sitemap = await self._fetcher.fetch_probe(f"{origin}/sitemap.xml")
            llms = await self._fetcher.fetch_probe(f"{origin}/llms.txt")

            record = self._update(record, progress=40, current_step="Parsing website")
            html_data = parse_html(fetched["html"])

            record = self._update(record, progress=45, current_step="Discovering pages")
            pages_payload = None

            def on_pages_progress(snapshot) -> None:
                nonlocal record
                record = self._update(
                    record,
                    progress=45,
                    current_step="Discovering pages",
                    result={"pages": snapshot.model_dump(mode="json")},
                )

            allowed_host = hostname_of(fetched["final_url"] or record.normalized_url)
            try:
                pages_payload = await crawl_site(
                    scan_id=record.id,
                    seed_url=record.normalized_url,
                    seed_fetch=fetched,
                    seed_html=fetched["html"],
                    seed_html_data=html_data,
                    fetcher=self._fetcher,
                    allowed_host=allowed_host,
                    sitemap_body=sitemap.get("body") if sitemap.get("exists") else None,
                    max_pages=MAX_PAGES,
                    max_depth=MAX_DEPTH,
                    on_progress=on_pages_progress,
                )
            except Exception:
                logger.exception("pages_crawl_failed scan_id=%s", scan_id)
                fallback = SiteCrawler(
                    scan_id=record.id,
                    seed_url=record.normalized_url,
                    fetcher=self._fetcher,
                    allowed_host=allowed_host or hostname_of(record.normalized_url),
                    max_pages=MAX_PAGES,
                    max_depth=MAX_DEPTH,
                )
                fallback.ingest_seed(
                    seed_fetch=fetched,
                    seed_html=fetched["html"],
                    seed_html_data=html_data,
                    sitemap_body=None,
                )
                pages_payload = fallback.snapshot(in_progress=False)

            if pages_payload is not None:
                record = self._update(
                    record,
                    progress=45,
                    current_step="Discovering pages",
                    result={"pages": pages_payload.model_dump(mode="json")},
                )

            record = self._update(record, progress=50, current_step="SEO analysis")
            seo = analyze_seo(
                SeoContext(
                    page_url=record.normalized_url,
                    final_url=fetched["final_url"],
                    status_code=fetched["status_code"],
                    html=html_data,
                    x_robots_tag=fetched.get("x_robots_tag"),
                    robots_txt=robots,
                    sitemap=sitemap,
                )
            )

            record = self._update(record, progress=65, current_step="AEO analysis")
            aeo = analyze_aeo(
                AeoContext(
                    page_url=record.normalized_url,
                    final_url=fetched["final_url"],
                    status_code=fetched["status_code"],
                    html=html_data,
                    robots_txt=robots,
                    llms_txt=llms,
                )
            )

            record = self._update(record, progress=75, current_step="Rendering website")

            def on_progress(progress: int, step: str) -> None:
                nonlocal record
                record = self._update(record, progress=progress, current_step=step)

            uiux = await self._uiux.analyze(
                url=fetched["final_url"],
                scan_id=record.id,
                on_progress=on_progress,
            )

            record = self._update(record, progress=92, current_step="Accessibility analysis")
            accessibility_payload = None
            accessibility_error = None
            try:
                a11y = await self._a11y.analyze(
                    url=fetched["final_url"],
                    scan_id=record.id,
                    screenshots=[item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in uiux.screenshots],
                    on_progress=on_progress,
                )
                accessibility_payload = a11y.model_dump(mode="json")
            except ScanError as exc:
                logger.info("accessibility_failed scan_id=%s code=%s", scan_id, exc.code)
                accessibility_error = {"code": exc.code, "message": exc.message}
            except Exception:
                logger.exception("accessibility_failed scan_id=%s", scan_id)
                accessibility_error = {
                    "code": "A11Y_FAILED",
                    "message": "Accessibility analysis could not be completed.",
                }

            record = self._update(record, progress=96, current_step="Performance analysis")
            performance_payload = None
            performance_error = None
            try:
                perf = await self._perf.analyze(
                    url=fetched["final_url"],
                    scan_id=record.id,
                    on_progress=on_progress,
                )
                performance_payload = perf.model_dump(mode="json")
            except ScanError as exc:
                logger.info("performance_failed scan_id=%s code=%s", scan_id, exc.code)
                performance_error = {"code": exc.code, "message": exc.message}
            except Exception:
                logger.exception("performance_failed scan_id=%s", scan_id)
                performance_error = {
                    "code": "PERF_FAILED",
                    "message": "Performance analysis could not be completed.",
                }

            record = self._update(record, progress=97, current_step="Content analysis")
            content_payload = None
            content_error = None
            try:
                content = self._content(
                    ContentContext(
                        page_url=record.normalized_url,
                        final_url=fetched["final_url"],
                        html=html_data,
                        html_source=fetched["html"],
                    )
                )
                content_payload = content.model_dump(mode="json")
            except ScanError as exc:
                logger.info("content_failed scan_id=%s code=%s", scan_id, exc.code)
                content_error = {"code": exc.code, "message": exc.message}
            except Exception:
                logger.exception("content_failed scan_id=%s", scan_id)
                content_error = {
                    "code": "CONTENT_FAILED",
                    "message": "Content analysis could not be completed.",
                }

            record = self._update(record, progress=98, current_step="Structured Data Analysis")
            schema_payload = None
            schema_error = None
            try:
                page_type = None
                if content_payload:
                    raw_type = content_payload.get("page_type") or {}
                    if raw_type.get("type"):
                        from backend.analyzers.content.models import ContentPageType

                        try:
                            page_type = ContentPageType(
                                type=raw_type.get("type") or "unknown",
                                confidence=float(raw_type.get("confidence") or 0),
                                reasons=list(raw_type.get("reasons") or []),
                            )
                        except Exception:
                            page_type = None
                schema = self._schema(
                    StructuredDataContext(
                        page_url=record.normalized_url,
                        final_url=fetched["final_url"],
                        html=html_data,
                        html_source=fetched["html"],
                        page_type=page_type,
                    )
                )
                schema_payload = schema.model_dump(mode="json")
            except ScanError as exc:
                logger.info("schema_failed scan_id=%s code=%s", scan_id, exc.code)
                schema_error = {"code": exc.code, "message": exc.message}
            except Exception:
                logger.exception("schema_failed scan_id=%s", scan_id)
                schema_error = {
                    "code": "SCHEMA_FAILED",
                    "message": "Structured data analysis could not be completed.",
                }

            record = self._update(record, progress=99, current_step="Mobile Analysis")
            mobile_payload = None
            mobile_error = None
            try:
                mobile = await self._mobile.analyze(
                    url=fetched["final_url"],
                    scan_id=record.id,
                    on_progress=on_progress,
                )
                mobile_payload = mobile.model_dump(mode="json")
            except ScanError as exc:
                logger.info("mobile_failed scan_id=%s code=%s", scan_id, exc.code)
                mobile_error = {"code": exc.code, "message": exc.message}
            except Exception:
                logger.exception("mobile_failed scan_id=%s", scan_id)
                mobile_error = {
                    "code": "MOBILE_FAILED",
                    "message": "Mobile analysis could not be completed.",
                }

            first_h1 = next((item.get("text") for item in html_data.get("h1s") or [] if item.get("text")), None)
            result = {
                "scan": {"id": record.id},
                "website": {
                    "url": record.normalized_url,
                    "final_url": fetched["final_url"],
                },
                "http": {
                    "status_code": fetched["status_code"],
                    "response_time_ms": fetched["response_time_ms"],
                    "content_type": fetched["content_type"],
                    "html_size_bytes": fetched["html_size_bytes"],
                    "x_robots_tag": fetched.get("x_robots_tag"),
                },
                "html": {
                    "title": html_data["title"],
                    "meta_description": html_data["meta_description"],
                    "canonical": html_data["canonical"],
                    "language": html_data["language"],
                    "h1": first_h1,
                    "h1_count": html_data["h1_count"],
                    "h2_count": html_data["h2_count"],
                    "h3_count": html_data["h3_count"],
                    "script_count": html_data["script_count"],
                    "stylesheet_count": html_data["stylesheet_count"],
                    "form_count": html_data["form_count"],
                },
                "links": {"total": html_data["link_count"]},
                "images": {"total": html_data["image_count"]},
                "robots_txt": _probe_public(robots),
                "sitemap": _probe_public(sitemap),
                "llms_txt": _probe_public(llms),
                "seo": seo.model_dump(mode="json"),
                "aeo": aeo.model_dump(mode="json"),
                "uiux": uiux.model_dump(mode="json"),
                "accessibility": accessibility_payload,
                "accessibility_error": accessibility_error,
                "performance": performance_payload,
                "performance_error": performance_error,
                "content": content_payload,
                "content_error": content_error,
                "structured_data": schema_payload,
                "structured_data_error": schema_error,
                "mobile": mobile_payload,
                "mobile_error": mobile_error,
            }
            if pages_payload is not None:
                attach_analyzers(pages_payload.items, result)
            record = self._update(record, progress=99, current_step="CRO Analysis")
            try:
                cro = analyze_cro(result, pages=pages_payload)
                result["cro"] = cro.model_dump(mode="json")
                result.pop("cro_error", None)
            except ScanError as exc:
                logger.info("cro_failed scan_id=%s code=%s", scan_id, exc.code)
                result["cro"] = None
                result["cro_error"] = {"code": exc.code, "message": exc.message}
            except Exception:
                logger.exception("cro_failed scan_id=%s", scan_id)
                result["cro"] = None
                result["cro_error"] = {
                    "code": "CRO_FAILED",
                    "message": "CRO analysis could not be completed.",
                }
            if pages_payload is not None:
                attach_analyzers(pages_payload.items, result)
            record = self._update(record, progress=99, current_step="Trust & Credibility Analysis")
            try:
                trust = analyze_trust(result, pages=pages_payload)
                result["trust"] = trust.model_dump(mode="json")
                result.pop("trust_error", None)
            except ScanError as exc:
                logger.info("trust_failed scan_id=%s code=%s", scan_id, exc.code)
                result["trust"] = None
                result["trust_error"] = {"code": exc.code, "message": exc.message}
            except Exception:
                logger.exception("trust_failed scan_id=%s", scan_id)
                result["trust"] = None
                result["trust_error"] = {
                    "code": "TRUST_FAILED",
                    "message": "Trust & Credibility analysis unavailable.",
                }
            if pages_payload is not None:
                attach_analyzers(pages_payload.items, result)
            previous = (self._store.get(scan_id) or record).result or {}
            if previous.get("competitors"):
                result["competitors"] = previous["competitors"]
            result["methodology"] = methodology_snapshot()
            record = self._update(record, progress=99, current_step="Aggregating Issues")
            created = record.created_at.isoformat() if record.created_at else None
            try:
                issues_payload = aggregate(record.id, result, created)
                result["issues"] = issues_payload.model_dump(mode="json")
            except Exception:
                logger.exception("issues_aggregate_failed scan_id=%s", scan_id)
                issues_payload = None
                result["issues"] = {
                    "version": 1,
                    "truncated": False,
                    "analyzer_status": {},
                    "summary": {"total": 0, "failures": 0, "warnings": 0, "info": 0},
                    "issues": [],
                    "groups": {},
                }
            if pages_payload is not None:
                if issues_payload is not None:
                    attach_issues(pages_payload.items, issues_payload)
                result["pages"] = pages_payload.model_dump(mode="json")
            record = self._update(record, progress=99, current_step="Generating Recommendations", result=result)
            try:
                recs_payload = generate(record.id, result, created)
                result["recommendations"] = recs_payload.model_dump(mode="json")
                result.pop("recommendations_error", None)
            except Exception:
                logger.exception("recommendations_generate_failed scan_id=%s", scan_id)
                result["recommendations_error"] = {
                    "code": "RECOMMENDATIONS_FAILED",
                    "message": "Recommendations could not be generated from the stored findings.",
                }
            record = self._update(record, progress=99, current_step="Calculating Health Score", result=result)
            try:
                health = attach_health(result)
                logger.info(
                    "scoring_stored scan_id=%s version=%s coverage=%s score=%s",
                    scan_id,
                    health.calculation_version,
                    health.coverage.coverage_percent,
                    health.overall.score,
                )
            except ScanError as exc:
                logger.info("score_failed scan_id=%s code=%s", scan_id, exc.code)
                result["health"] = None
                result["health_error"] = {"code": exc.code, "message": exc.message}
            except Exception:
                logger.exception("score_failed scan_id=%s", scan_id)
                result["health"] = None
                result["health_error"] = {
                    "code": "SCORE_FAILED",
                    "message": "Health score unavailable.",
                }
            self._update(
                record,
                status="completed",
                progress=100,
                current_step="Analysis complete",
                completed_at=_now(),
                error=None,
                result=result,
            )
            logger.info(
                "scan_completed scan_id=%s seo_score=%s aeo_score=%s uiux_score=%s a11y_score=%s perf_score=%s content_score=%s schema_score=%s mobile_score=%s cro_score=%s trust_score=%s health_score=%s",
                scan_id,
                seo.score,
                aeo.score,
                uiux.score,
                (accessibility_payload or {}).get("score"),
                (performance_payload or {}).get("score"),
                (content_payload or {}).get("score"),
                (schema_payload or {}).get("score"),
                (mobile_payload or {}).get("score"),
                (result.get("cro") or {}).get("score"),
                (result.get("trust") or {}).get("score"),
                (result.get("health") or {}).get("overall", {}).get("score") if isinstance(result.get("health"), dict) else None,
            )
            await asyncio.to_thread(self._capture_issue_screenshots, scan_id)
        except ScanError as exc:
            logger.info("scan_failed scan_id=%s code=%s", scan_id, exc.code)
            latest = self._store.get(scan_id) or record
            self._update(
                latest,
                status="failed",
                completed_at=_now(),
                error={"code": exc.code, "message": exc.message},
            )
        except Exception:
            logger.exception("scan_failed scan_id=%s code=INTERNAL_ERROR", scan_id)
            latest = self._store.get(scan_id) or record
            self._update(
                latest,
                status="failed",
                completed_at=_now(),
                error={
                    "code": "INTERNAL_ERROR",
                    "message": "Unable to analyze this website.",
                },
            )
