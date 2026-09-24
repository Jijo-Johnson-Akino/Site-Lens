from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from backend.analyzers.mobile.browser import run_mobile_session
from backend.analyzers.mobile.checks import CHECK_RUNNERS
from backend.analyzers.mobile.config import (
    COMPACT_VIEWPORT,
    DEFAULT_SCORING,
    DEVICE_SCALE_FACTOR,
    LIMITATIONS,
    PRIMARY_VIEWPORT,
    MobileScoringConfig,
)
from backend.analyzers.mobile.models import (
    CheckResult,
    MobileEnvironment,
    MobilePageInfo,
    MobileResult,
    MobileSnapshot,
    ScreenshotMeta,
)
from backend.analyzers.mobile.scoring import (
    apply_weights,
    category_cards,
    category_scores,
    collect_issues,
    narrative_summary,
    overall_score,
    overview_cards,
    severity_counts,
    summarize,
)
from backend.analyzers.mobile.screenshots import (
    COMPACT_FULL_KEY,
    COMPACT_KEY,
    PRIMARY_FULL_KEY,
    PRIMARY_KEY,
    screenshot_url,
)
from backend.analyzers.uiux.browser import UIUXBrowser
from backend.errors import ScanError
from backend.services.url_validator import UrlValidator
from backend.store.screenshots import InMemoryScreenshotStore, ScreenshotRepository

logger = logging.getLogger("sitebench.mobile")

ProgressFn = Callable[[int, str], Awaitable[None] | None]


def collect_checks(snapshot: MobileSnapshot) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for runner in CHECK_RUNNERS:
        checks.extend(runner(snapshot))
    return checks


def analyze_snapshot(
    snapshot: MobileSnapshot,
    *,
    screenshots: list[ScreenshotMeta] | None = None,
    comparison: dict | None = None,
    limitations: list[str] | None = None,
    config: MobileScoringConfig | None = None,
) -> MobileResult:
    scoring = config or DEFAULT_SCORING
    checks = apply_weights(collect_checks(snapshot), scoring)
    categories = category_scores(checks, scoring)
    score = overall_score(checks, scoring)
    layout = snapshot.layout or {}
    touch = snapshot.touch_targets or {}
    forms = snapshot.forms or []
    images = snapshot.images or []
    tables = snapshot.tables or []
    env_raw = snapshot.environment or {}
    raw_viewport = env_raw.get("viewport") if isinstance(env_raw.get("viewport"), dict) else snapshot.viewport
    environment = MobileEnvironment(
        browser=str(env_raw.get("browser") or "chromium"),
        browser_version=env_raw.get("browser_version"),
        device_profile=str(env_raw.get("device_profile") or "mobile"),
        viewport={
            "width": int((raw_viewport or {}).get("width") or PRIMARY_VIEWPORT["width"]),
            "height": int((raw_viewport or {}).get("height") or PRIMARY_VIEWPORT["height"]),
        },
        touch_enabled=env_raw.get("touch_enabled"),
        device_scale_factor=_float_or_none(env_raw.get("device_scale_factor") or DEVICE_SCALE_FACTOR),
        user_agent_category=str(env_raw.get("user_agent_category") or "mobile"),
        is_mobile_emulation=bool(env_raw.get("is_mobile_emulation", True)),
    )
    overflowing_forms = [item for item in forms if item.get("overflowing") and not item.get("isolated_scroll")]
    overflowing_images = [item for item in images if item.get("overflowing")]
    page_wide_tables = [item for item in tables if item.get("page_wide")]
    isolated_tables = [item for item in tables if item.get("isolated_scroll")]
    notes = list(limitations or LIMITATIONS)
    return MobileResult(
        score=score,
        summary=summarize(checks),
        narrative=narrative_summary(score, checks),
        categories=categories,
        category_cards=category_cards(checks, scoring),
        checks=checks,
        findings=checks,
        issues=collect_issues(checks),
        page=MobilePageInfo(
            analyzed_url=str(snapshot.page.get("url") or ""),
            final_url=str(snapshot.page.get("final_url") or snapshot.page.get("url") or ""),
        ),
        environment=environment,
        viewport={
            "width": snapshot.viewport.get("width"),
            "height": snapshot.viewport.get("height"),
            "document_width": layout.get("document_width") or layout.get("scroll_width"),
            "body_scroll_width": layout.get("body_scroll_width"),
            "horizontal_overflow": bool(layout.get("horizontal_overflow")),
            "overflow_px": layout.get("overflow_px"),
            "meta": snapshot.viewport_meta,
        },
        navigation={
            "mobile_navigation_detected": bool(snapshot.navigation.get("exists")),
            "mobile_menu_detected": bool(snapshot.navigation.get("menu_button")),
            "menu_button_detected": bool(snapshot.navigation.get("menu_button")),
            "mobile_menu_opened": bool(snapshot.navigation.get("menu_opened")),
            "menu_tested": bool(snapshot.navigation.get("menu_tested")),
            "visible": snapshot.navigation.get("visible"),
            "overflow": snapshot.navigation.get("overflow"),
        },
        layout={
            "overflowing_elements": snapshot.overflowing_elements,
            "min_width_elements": snapshot.min_width_elements,
            "clipped_containers": snapshot.clipped_containers,
            "offscreen_critical": snapshot.offscreen_critical,
        },
        typography={
            "small_text_elements": len(snapshot.small_text or []),
            "clipped_text": len(snapshot.clipped_text or []),
            "overflowing_headings": len(snapshot.overflowing_headings or []),
        },
        touch_targets={
            "interactive_elements": touch.get("interactive_elements") or 0,
            "below_baseline": touch.get("below_baseline") or 0,
            "very_small": touch.get("very_small") or 0,
        },
        forms={
            "forms": len(forms),
            "overflowing_forms": len(overflowing_forms),
            "controls_outside_viewport": sum(int(item.get("controls_outside") or 0) for item in forms),
        },
        images={
            "images": len(images),
            "overflowing": len(overflowing_images),
            "oversized": len(overflowing_images),
        },
        tables={
            "tables": len(tables),
            "overflowing": len(page_wide_tables),
            "responsive": len(isolated_tables),
        },
        media={"items": len(snapshot.media or []), "overflowing": sum(1 for item in snapshot.media or [] if item.get("overflowing"))},
        overlays={
            "count": len(snapshot.overlays or []),
            "max_coverage": max((item.get("coverage") or 0) for item in snapshot.overlays or [0]) if snapshot.overlays else 0,
        },
        sticky_elements={
            "count": len(snapshot.sticky_elements or []),
            "max_coverage": max((item.get("coverage") or 0) for item in snapshot.sticky_elements or [0]) if snapshot.sticky_elements else 0,
        },
        screenshots=screenshots or [],
        limitations=notes,
        severity_counts=severity_counts(checks),
        comparison=comparison or snapshot.comparison,
        overview=overview_cards(checks),
        cta=dict(snapshot.cta or {}),
    )


class PlaywrightMobileAnalyzer:
    def __init__(
        self,
        validator: UrlValidator | None = None,
        screenshot_store: ScreenshotRepository | None = None,
        scoring: MobileScoringConfig | None = None,
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
    ) -> MobileResult:
        await _emit(on_progress, 99, "Mobile Analysis")
        try:
            return await asyncio.to_thread(self._analyze_sync, url, scan_id, None)
        except ScanError:
            raise
        except Exception as exc:
            raise ScanError("MOBILE_FAILED", "Mobile analysis could not be completed.") from exc

    def analyze_html(self, html: str, *, scan_id: str = "scan_mobile_test", page_url: str = "https://example.com/", capture_shots: bool = True) -> MobileResult:
        return self._analyze_sync(page_url, scan_id, html, capture_shots=capture_shots)

    def _analyze_sync(self, url: str, scan_id: str, html: str | None, capture_shots: bool = True) -> MobileResult:
        limitations = list(LIMITATIONS)
        screenshots: list[ScreenshotMeta] = []
        created = datetime.now(timezone.utc).isoformat()
        comparison = None
        with UIUXBrowser(self._validator) as browser:
            try:
                primary = run_mobile_session(
                    browser,
                    size=PRIMARY_VIEWPORT,
                    viewport_name="mobile",
                    url=None if html is not None else url,
                    html=html,
                    page_url=url,
                    capture_shots=capture_shots,
                )
            except ScanError:
                raise
            except Exception as exc:
                raise ScanError("MOBILE_FAILED", "Unable to open a mobile browser context.") from exc

            snapshot = primary["snapshot"]
            env = primary.get("environment") or {}
            snapshot = snapshot.model_copy(update={"environment": {**snapshot.environment, **env}})
            shots = primary.get("shots") or {}
            screenshots.extend(_store_shots(self._screenshots, scan_id, shots, PRIMARY_KEY, PRIMARY_FULL_KEY, PRIMARY_VIEWPORT, created, limitations))

            try:
                compact = run_mobile_session(
                    browser,
                    size=COMPACT_VIEWPORT,
                    viewport_name="mobile_compact",
                    url=None if html is not None else url,
                    html=html,
                    page_url=url,
                    capture_shots=capture_shots,
                    interact_menu=False,
                )
                compact_snap: MobileSnapshot = compact["snapshot"]
                primary_overflow = bool((snapshot.layout or {}).get("horizontal_overflow"))
                compact_overflow = bool((compact_snap.layout or {}).get("horizontal_overflow"))
                comparison = {
                    "viewport": dict(COMPACT_VIEWPORT),
                    "document_width": (compact_snap.layout or {}).get("document_width"),
                    "horizontal_overflow": compact_overflow,
                    "overflow_appeared": compact_overflow and not primary_overflow,
                }
                compact_shots = compact.get("shots") or {}
                screenshots.extend(
                    _store_shots(
                        self._screenshots,
                        scan_id,
                        compact_shots,
                        COMPACT_KEY,
                        COMPACT_FULL_KEY,
                        COMPACT_VIEWPORT,
                        created,
                        limitations,
                    )
                )
                if comparison["overflow_appeared"]:
                    limitations.append("Horizontal overflow appeared at 375×812 but not at the primary 390×844 viewport.")
            except Exception:
                logger.info("mobile_compact_viewport_failed")
                limitations.append("The optional 375×812 comparison viewport could not be measured.")

        snapshot = snapshot.model_copy(update={"comparison": comparison})
        return analyze_snapshot(snapshot, screenshots=screenshots, comparison=comparison, limitations=limitations, config=self._scoring)


def _store_shots(
    store: ScreenshotRepository,
    scan_id: str,
    shots: dict,
    viewport_key: str,
    full_key: str,
    size: dict[str, int],
    created: str,
    limitations: list[str],
) -> list[ScreenshotMeta]:
    metas: list[ScreenshotMeta] = []
    viewport_png = shots.get("viewport")
    full_png = shots.get("full")
    if viewport_png:
        store.put(scan_id, viewport_key, viewport_png)
        metas.append(
            ScreenshotMeta(
                viewport=viewport_key,
                width=int(size["width"]),
                height=int(size["height"]),
                url=screenshot_url(scan_id, viewport_key),
                created_at=created,
                kind="viewport",
            )
        )
    else:
        limitations.append(f"Viewport screenshot unavailable ({viewport_key.replace('_', ' ')}).")
    if full_png:
        store.put(scan_id, full_key, full_png)
        metas.append(
            ScreenshotMeta(
                viewport=full_key,
                width=int(size["width"]),
                height=int(size["height"]),
                url=screenshot_url(scan_id, full_key),
                created_at=created,
                kind="full",
            )
        )
    return metas


def _float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def _emit(on_progress: ProgressFn | None, progress: int, step: str) -> None:
    if on_progress is None:
        return
    maybe = on_progress(progress, step)
    if maybe is not None:
        await maybe
