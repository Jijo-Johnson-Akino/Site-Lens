from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from backend.analyzers.performance.checks import CHECK_RUNNERS
from backend.analyzers.performance.collection import PerformanceCollector
from backend.analyzers.performance.config import DEFAULT_SCORING, LIMITATIONS, WAIT_AFTER_LOAD_MS, PerfScoringConfig
from backend.analyzers.performance.models import (
    CheckResult,
    PerfCategoryScore,
    PerfEnvironment,
    PerfPageInfo,
    PerfResources,
    PerfResult,
    PerfTiming,
    PerfVitalMetric,
    PerfVitals,
    PerformanceSnapshot,
    ResourceRecord,
)
from backend.analyzers.performance.scoring import (
    CATEGORY_LABELS,
    apply_weights,
    category_scores,
    collect_issues,
    narrative_summary,
    overall_score,
    severity_counts,
    summarize,
)
from backend.analyzers.uiux.browser import UIUXBrowser
from backend.errors import ScanError
from backend.services.url_validator import UrlValidator

ProgressFn = Callable[[int, str], Awaitable[None] | None]


def collect_checks(snapshot: PerformanceSnapshot, config: PerfScoringConfig | None = None) -> list[CheckResult]:
    scoring = config or DEFAULT_SCORING
    checks: list[CheckResult] = []
    for runner in CHECK_RUNNERS:
        checks.extend(runner(snapshot, scoring))
    return checks


def _vital(value: float | None, *, unit: str, good: float, poor: float, reason: str | None = None) -> PerfVitalMetric:
    if value is None:
        return PerfVitalMetric(value=None, status="unavailable", unit=unit, reason=reason or "This metric could not be reliably measured in this automated run.")
    if value <= good:
        status = "good"
    elif value <= poor:
        status = "needs_improvement"
    else:
        status = "poor"
    return PerfVitalMetric(value=value, status=status, unit=unit)


def analyze_snapshot(snapshot: PerformanceSnapshot, config: PerfScoringConfig | None = None) -> PerfResult:
    scoring = config or DEFAULT_SCORING
    checks = apply_weights(collect_checks(snapshot, scoring), scoring)
    categories = category_scores(checks, scoring)
    score = overall_score(checks, scoring)
    cards = [
        PerfCategoryScore(
            id=group,
            name=CATEGORY_LABELS.get(group, group),
            score=categories.get(group),
            finding_count=sum(1 for check in checks if check.group == group and check.status in {"fail", "warning"}),
        )
        for group in scoring.category_weights
    ]
    timing_raw = snapshot.timing or {}
    lcp = snapshot.vitals.get("lcp") if isinstance(snapshot.vitals, dict) else None
    lcp_ms = lcp.get("value") if isinstance(lcp, dict) else None
    if lcp_ms == 0:
        lcp_ms = None
    cls = snapshot.vitals.get("cls") if isinstance(snapshot.vitals, dict) else None
    env = snapshot.environment or {}
    totals = snapshot.totals or {}
    return PerfResult(
        score=score,
        summary=summarize(checks),
        narrative=narrative_summary(score, checks),
        categories=categories,
        category_cards=cards,
        checks=checks,
        findings=checks,
        issues=collect_issues(checks),
        page=PerfPageInfo(
            analyzed_url=str(snapshot.page.get("url") or ""),
            final_url=str(snapshot.page.get("final_url") or snapshot.page.get("url") or ""),
        ),
        environment=PerfEnvironment(
            browser=str(env.get("browser") or "chromium"),
            browser_version=env.get("browser_version"),
            viewport=env.get("viewport") or {},
            viewport_name=str(env.get("viewport_name") or "desktop"),
            network_profile=str(env.get("network_profile") or "default"),
            cpu_throttling=bool(env.get("cpu_throttling")),
            cache_enabled=bool(env.get("cache_enabled")),
            cache_mode=str(env.get("cache_mode") or "cold"),
        ),
        timing=PerfTiming(
            navigation_start_ms=timing_raw.get("navigation_start_ms"),
            fetch_start_ms=timing_raw.get("fetch_start_ms"),
            dns_ms=timing_raw.get("dns_ms"),
            connection_ms=timing_raw.get("connection_ms"),
            tls_ms=timing_raw.get("tls_ms"),
            ttfb_ms=timing_raw.get("ttfb_ms"),
            response_end_ms=timing_raw.get("response_end_ms"),
            dom_interactive_ms=timing_raw.get("dom_interactive_ms"),
            dom_content_loaded_ms=timing_raw.get("dom_content_loaded_ms"),
            load_event_ms=timing_raw.get("load_event_ms"),
            redirect_ms=timing_raw.get("redirect_ms"),
            redirect_count=timing_raw.get("redirect_count"),
        ),
        vitals=PerfVitals(
            lcp=_vital(lcp_ms, unit="ms", good=scoring.lcp_good_ms, poor=scoring.lcp_poor_ms),
            cls=_vital(cls, unit="score", good=scoring.cls_good, poor=scoring.cls_poor),
            inp=PerfVitalMetric(
                value=None,
                status="unavailable",
                unit="ms",
                reason=str(snapshot.vitals.get("inp_reason") or "No representative interaction was available during the automated run."),
            ),
        ),
        resources=PerfResources(
            total_requests=int(totals.get("total_requests") or 0),
            transfer_bytes=int(totals.get("transfer_bytes") or 0),
            resource_bytes=int(totals.get("resource_bytes") or 0),
            html_bytes=int(totals.get("html_bytes") or 0),
            css_bytes=int(totals.get("css_bytes") or 0),
            js_bytes=int(totals.get("js_bytes") or 0),
            image_bytes=int(totals.get("image_bytes") or 0),
            font_bytes=int(totals.get("font_bytes") or 0),
            media_bytes=int(totals.get("media_bytes") or 0),
            other_bytes=int(totals.get("other_bytes") or 0),
            third_party_bytes=int(totals.get("third_party_bytes") or 0),
            third_party_requests=int(totals.get("third_party_requests") or 0),
            percentages=totals.get("percentages") or {},
        ),
        resource_table=[ResourceRecord.model_validate(item) for item in snapshot.resources],
        limitations=list(LIMITATIONS),
        severity_counts=severity_counts(checks),
    )


class PlaywrightPerfAnalyzer:
    def __init__(self, validator: UrlValidator | None = None, scoring: PerfScoringConfig | None = None) -> None:
        self._validator = validator or UrlValidator()
        self._scoring = scoring or DEFAULT_SCORING

    async def analyze(self, *, url: str, scan_id: str | None = None, on_progress: ProgressFn | None = None) -> PerfResult:
        await _emit(on_progress, 96, "Performance analysis")
        try:
            snapshot = await asyncio.to_thread(self._analyze_sync, url)
        except ScanError as exc:
            if exc.code in {"WEBSITE_UNREACHABLE", "RENDER_FAILED"}:
                raise ScanError("PERF_FAILED", "The website could not be rendered for performance analysis.") from exc
            raise
        return analyze_snapshot(snapshot, self._scoring)

    def analyze_html(
        self,
        html: str,
        page_url: str = "https://example.com/",
        *,
        extra_routes: dict | None = None,
        document_headers: dict | None = None,
        document_delay_ms: int = 0,
        viewport_name: str = "desktop",
    ) -> PerfResult:
        collector = PerformanceCollector(
            html=html,
            page_url=page_url,
            extra_routes=extra_routes,
            document_headers=document_headers,
            document_delay_ms=document_delay_ms,
        )
        with UIUXBrowser(self._validator) as browser:
            snapshot = browser.measure(
                collector,
                html=html,
                viewport_name=viewport_name,
                page_url=page_url,
                wait_after_load_ms=WAIT_AFTER_LOAD_MS,
            )
        return analyze_snapshot(snapshot, self._scoring)

    def _analyze_sync(self, url: str) -> PerformanceSnapshot:
        collector = PerformanceCollector(page_url=url)
        with UIUXBrowser(self._validator) as browser:
            return browser.measure(
                collector,
                url=url,
                viewport_name="desktop",
                wait_after_load_ms=WAIT_AFTER_LOAD_MS,
            )


async def _emit(on_progress: ProgressFn | None, progress: int, step: str) -> None:
    if on_progress is None:
        return
    maybe = on_progress(progress, step)
    if maybe is not None:
        await maybe
