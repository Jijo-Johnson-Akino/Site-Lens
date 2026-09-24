from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from backend.analyzers.uiux.browser import UIUXBrowser
from backend.analyzers.uiux.checks import CHECK_RUNNERS
from backend.analyzers.uiux.config import (
    MAX_PAGES,
    MAX_SCREENSHOTS,
    DEFAULT_SCORING,
    UIUXScoringConfig,
    enabled_viewports,
)
from backend.analyzers.uiux.models import (
    CheckResult,
    ScreenshotMeta,
    UiuxPageInfo,
    UiuxResult,
    ViewportResult,
    ViewportSnapshot,
)
from backend.analyzers.uiux.scoring import (
    apply_weights,
    category_scores,
    collect_issues,
    narrative_summary,
    overall_score,
    summarize,
    viewport_score,
)
from backend.services.url_validator import UrlValidator
from backend.store.screenshots import InMemoryScreenshotStore, ScreenshotRepository

ProgressFn = Callable[[int, str], Awaitable[None] | None]


def collect_checks(snapshot: ViewportSnapshot) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for runner in CHECK_RUNNERS:
        checks.extend(runner(snapshot))
    return checks


def analyze_snapshots(
    snapshots: list[ViewportSnapshot],
    screenshots: list[ScreenshotMeta] | None = None,
    config: UIUXScoringConfig | None = None,
) -> UiuxResult:
    scoring = config or DEFAULT_SCORING
    checks = apply_weights([check for snapshot in snapshots for check in collect_checks(snapshot)], scoring)
    categories = category_scores(checks, scoring)
    score = overall_score(checks, scoring)
    viewports: dict[str, ViewportResult] = {}
    for snapshot in snapshots:
        name = str(snapshot.viewport.get("name") or "desktop")
        vp_checks = [check for check in checks if check.viewport == name]
        viewports[name] = ViewportResult(
            score=viewport_score(vp_checks, scoring),
            width=int(snapshot.viewport.get("width") or 0),
            height=int(snapshot.viewport.get("height") or 0),
            summary=summarize(vp_checks),
            layout={
                "scroll_width": snapshot.layout.get("scroll_width"),
                "viewport_width": snapshot.layout.get("viewport_width"),
                "horizontal_overflow": snapshot.layout.get("horizontal_overflow"),
                "overflow_px": snapshot.layout.get("overflow_px"),
            },
            navigation={
                "exists": snapshot.navigation.get("exists"),
                "visible": snapshot.navigation.get("visible"),
                "links": snapshot.navigation.get("links"),
            },
            content={
                "h1": snapshot.content.get("h1"),
                "h1_visible": snapshot.content.get("h1_visible"),
                "paragraphs": snapshot.content.get("paragraphs"),
            },
            interactive={
                "buttons": snapshot.interactive.get("buttons"),
                "links": snapshot.interactive.get("links"),
                "forms": snapshot.interactive.get("forms"),
            },
            cta=dict(snapshot.cta or {}),
            forms=list(snapshot.forms or [])[:12],
            overlays=list(snapshot.overlays or [])[:8],
            buttons=list(snapshot.buttons or [])[:40],
            links=list(snapshot.links or [])[:40],
            headings=list(snapshot.headings or [])[:8],
        )
    first = snapshots[0] if snapshots else None
    page_url = str((first.page.get("url") if first else "") or "")
    final_url = str((first.page.get("final_url") if first else "") or page_url)
    return UiuxResult(
        score=score,
        summary=summarize(checks),
        narrative=narrative_summary(score, checks),
        categories=categories,
        viewports=viewports,
        screenshots=screenshots or [],
        checks=checks,
        issues=collect_issues(checks),
        page=UiuxPageInfo(analyzed_url=page_url, final_url=final_url),
    )


class PlaywrightUiuxAnalyzer:
    def __init__(
        self,
        validator: UrlValidator | None = None,
        screenshot_store: ScreenshotRepository | None = None,
        scoring: UIUXScoringConfig | None = None,
    ) -> None:
        self._validator = validator or UrlValidator()
        self._screenshots = screenshot_store or InMemoryScreenshotStore()
        self._scoring = scoring or DEFAULT_SCORING

    async def analyze(
        self,
        *,
        url: str,
        scan_id: str,
        on_progress: ProgressFn | None = None,
    ) -> UiuxResult:
        await _emit(on_progress, 75, "Rendering website")
        result = await asyncio.to_thread(self._analyze_sync, url, scan_id)
        await _emit(on_progress, 82, "UI/UX analysis")
        await _emit(on_progress, 88, "Capturing screenshots")
        return result

    def _analyze_sync(self, url: str, scan_id: str) -> UiuxResult:
        snapshots: list[ViewportSnapshot] = []
        metas: list[ScreenshotMeta] = []
        created = datetime.now(timezone.utc).isoformat()
        viewports = enabled_viewports()
        pages = [url][:MAX_PAGES]
        screenshot_budget = MAX_SCREENSHOTS
        with UIUXBrowser(self._validator) as browser:
            for page_url in pages:
                for name, size in viewports.items():
                    snapshot, png = browser.capture_url(page_url, name)
                    snapshots.append(snapshot)
                    if png and screenshot_budget > 0:
                        self._screenshots.put(scan_id, name, png)
                        screenshot_budget -= 1
                        metas.append(
                            ScreenshotMeta(
                                viewport=name,
                                width=int(size["width"]),
                                height=int(size["height"]),
                                url=f"/api/scans/{scan_id}/uiux/screenshots/{name}",
                                created_at=created,
                            )
                        )
        return analyze_snapshots(snapshots, metas, self._scoring)


async def _emit(on_progress: ProgressFn | None, progress: int, step: str) -> None:
    if on_progress is None:
        return
    maybe = on_progress(progress, step)
    if maybe is not None:
        await maybe
