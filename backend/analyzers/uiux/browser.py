"""Playwright Chromium session with URL validation and guaranteed cleanup.

The sync Playwright API is used so browser processes work on Windows under
uvicorn, which may run a selector event loop that cannot spawn subprocesses.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.analyzers.uiux.config import (
    MAX_SCREENSHOT_HEIGHT,
    NAVIGATION_TIMEOUT_MS,
    USER_AGENT,
    VIEWPORTS,
    enabled_viewports,
)
from backend.analyzers.uiux.measurements import measurement_script, normalize_snapshot
from backend.analyzers.uiux.models import ViewportSnapshot
from backend.analyzers.uiux.screenshots import capture_screenshot
from backend.errors import ScanError
from backend.services.url_validator import UrlValidator, safe_display_url

logger = logging.getLogger("sitebench.uiux")


class UIUXBrowser:
    def __init__(
        self,
        validator: UrlValidator | None = None,
        *,
        navigation_timeout_ms: int = NAVIGATION_TIMEOUT_MS,
        max_screenshot_height: int = MAX_SCREENSHOT_HEIGHT,
    ) -> None:
        self._validator = validator or UrlValidator()
        self._timeout = navigation_timeout_ms
        self._max_screenshot_height = max_screenshot_height
        self._playwright: Any = None
        self._browser: Any = None

    def __enter__(self) -> "UIUXBrowser":
        self.launch()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def launch(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ScanError("RENDER_FAILED", "Unable to render the website for UI/UX analysis.") from exc
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage"],
            )
        except Exception as exc:
            self.close()
            raise ScanError("RENDER_FAILED", "Unable to render the website for UI/UX analysis.") from exc

    def close(self) -> None:
        browser = self._browser
        playwright = self._playwright
        self._browser = None
        self._playwright = None
        if browser is not None:
            try:
                browser.close()
            except Exception:
                logger.exception("uiux_browser_close_failed")
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                logger.exception("uiux_playwright_stop_failed")

    def _viewport(self, name: str) -> dict[str, int]:
        known = enabled_viewports()
        if name in known:
            return known[name]
        if name in VIEWPORTS:
            return VIEWPORTS[name]
        raise ScanError("INTERNAL_ERROR", "Unable to analyze this website.")

    def capture_url(
        self,
        url: str,
        viewport_name: str,
        *,
        mobile_emulation: bool = False,
        viewport_size: dict[str, int] | None = None,
        user_agent: str | None = None,
        device_scale_factor: float | None = None,
    ) -> tuple[ViewportSnapshot, bytes | None]:
        validated = self._validator.validate(url)
        size = viewport_size or self._viewport(viewport_name)
        return self._run_page(
            viewport_name=viewport_name,
            size=size,
            url=validated,
            html=None,
            mobile_emulation=mobile_emulation,
            user_agent=user_agent,
            device_scale_factor=device_scale_factor,
        )

    def capture_html(
        self,
        html: str,
        viewport_name: str,
        page_url: str = "https://example.com/",
        *,
        mobile_emulation: bool = False,
        viewport_size: dict[str, int] | None = None,
        user_agent: str | None = None,
        device_scale_factor: float | None = None,
    ) -> tuple[ViewportSnapshot, bytes | None]:
        size = viewport_size or self._viewport(viewport_name)
        return self._run_page(
            viewport_name=viewport_name,
            size=size,
            url=page_url,
            html=html,
            mobile_emulation=mobile_emulation,
            user_agent=user_agent,
            device_scale_factor=device_scale_factor,
        )

    def inspect(
        self,
        inspector,
        *,
        url: str | None = None,
        html: str | None = None,
        viewport_name: str = "desktop",
        page_url: str = "https://example.com/",
        mobile_emulation: bool = False,
        viewport_size: dict[str, int] | None = None,
        user_agent: str | None = None,
        device_scale_factor: float | None = None,
    ):
        """Open one homepage, run inspector(page, final_url), then close the page/context."""
        size = viewport_size or self._viewport(viewport_name)
        context = None
        page = None
        try:
            context, page, final_url = self._open_page(
                viewport_name=viewport_name,
                size=size,
                url=url,
                html=html,
                page_url=page_url,
                mobile_emulation=mobile_emulation,
                user_agent=user_agent,
                device_scale_factor=device_scale_factor,
            )
            return inspector(page, final_url)
        finally:
            self._close_page(page, context)

    def measure(
        self,
        collector,
        *,
        url: str | None = None,
        html: str | None = None,
        viewport_name: str = "desktop",
        page_url: str = "https://example.com/",
        wait_after_load_ms: int = 1500,
    ):
        """Fresh cold-cache context. collector.setup(page) runs before navigation."""
        size = self._viewport(viewport_name)
        if self._browser is None:
            self.launch()
        context = None
        page = None
        try:
            context = self._browser.new_context(
                viewport={"width": size["width"], "height": size["height"]},
                user_agent=USER_AGENT,
            )
            context.set_default_navigation_timeout(self._timeout)
            page = context.new_page()
            try:
                session = context.new_cdp_session(page)
                session.send("Network.setCacheDisabled", {"cacheDisabled": True})
            except Exception:
                pass
            if hasattr(collector, "setup"):
                collector.setup(page)
            if html is None:
                if not url:
                    raise ScanError("INVALID_URL", "Please enter a valid website URL.")
                validated = self._validator.validate(url)
                logger.info("perf_navigate host=%s viewport=%s", safe_display_url(validated), viewport_name)
                try:
                    page.goto(validated, wait_until="load", timeout=self._timeout)
                except Exception as exc:
                    raise ScanError("WEBSITE_UNREACHABLE", "The website could not be rendered for performance analysis.") from exc
                final_url = page.url
                self._validator.validate(final_url)
            elif getattr(collector, "serves_html", False):
                target = self._validator.validate(page_url)
                try:
                    page.goto(target, wait_until="load", timeout=self._timeout)
                except Exception as exc:
                    raise ScanError("WEBSITE_UNREACHABLE", "The website could not be rendered for performance analysis.") from exc
                final_url = page.url
            else:
                page.set_content(html, wait_until="load", timeout=self._timeout)
                final_url = page_url
            delay = min(max(int(wait_after_load_ms), 0), 3_000)
            if delay:
                try:
                    page.wait_for_timeout(delay)
                except Exception:
                    pass
            environment = {
                "browser": "chromium",
                "browser_version": getattr(self._browser, "version", None),
                "viewport": {"width": size["width"], "height": size["height"]},
                "viewport_name": viewport_name,
                "network_profile": "default",
                "cpu_throttling": False,
                "cache_enabled": False,
                "cache_mode": "cold",
            }
            return collector.collect(page, final_url, environment=environment)
        except ScanError:
            raise
        except Exception as exc:
            raise ScanError("PERF_FAILED", "Performance analysis could not be completed.") from exc
        finally:
            self._close_page(page, context)

    def _open_page(
        self,
        *,
        viewport_name: str,
        size: dict[str, int],
        url: str | None,
        html: str | None,
        page_url: str,
        mobile_emulation: bool = False,
        user_agent: str | None = None,
        device_scale_factor: float | None = None,
    ):
        if self._browser is None:
            self.launch()
        context_kwargs: dict[str, Any] = {
            "viewport": {"width": size["width"], "height": size["height"]},
            "user_agent": user_agent or USER_AGENT,
        }
        if mobile_emulation:
            # Chromium's is_mobile flag expands the layout viewport to the
            # document width on many pages, which hides horizontal overflow.
            # Touch, DPR, and a mobile UA still provide a realistic mobile context.
            context_kwargs["has_touch"] = True
            context_kwargs["device_scale_factor"] = float(device_scale_factor if device_scale_factor is not None else 2)
        context = self._browser.new_context(**context_kwargs)
        context.set_default_navigation_timeout(self._timeout)
        page = context.new_page()
        if html is None:
            if not url:
                context.close()
                raise ScanError("INVALID_URL", "Please enter a valid website URL.")
            validated = self._validator.validate(url)
            logger.info("uiux_navigate host=%s viewport=%s", safe_display_url(validated), viewport_name)
            try:
                page.goto(validated, wait_until="domcontentloaded", timeout=self._timeout)
            except Exception as exc:
                page.close()
                context.close()
                raise ScanError("WEBSITE_UNREACHABLE", "The website could not be rendered for UI/UX analysis.") from exc
            final_url = page.url
            try:
                self._validator.validate(final_url)
            except ScanError:
                page.close()
                context.close()
                raise
            _wait_usable(page)
            return context, page, final_url
        page.set_content(html, wait_until="load", timeout=self._timeout)
        _wait_usable(page)
        return context, page, page_url

    def _close_page(self, page, context) -> None:
        if page is not None:
            try:
                page.close()
            except Exception:
                logger.exception("uiux_page_close_failed")
        if context is not None:
            try:
                context.close()
            except Exception:
                logger.exception("uiux_context_close_failed")

    def _run_page(
        self,
        *,
        viewport_name: str,
        size: dict[str, int],
        url: str,
        html: str | None,
        mobile_emulation: bool = False,
        user_agent: str | None = None,
        device_scale_factor: float | None = None,
    ) -> tuple[ViewportSnapshot, bytes | None]:
        if self._browser is None:
            self.launch()
        context = None
        page = None
        try:
            context, page, final_url = self._open_page(
                viewport_name=viewport_name,
                size=size,
                url=None if html is not None else url,
                html=html,
                page_url=url,
                mobile_emulation=mobile_emulation,
                user_agent=user_agent,
                device_scale_factor=device_scale_factor,
            )
            raw = page.evaluate(measurement_script())
            snapshot = normalize_snapshot(
                raw or {},
                viewport_name=viewport_name,
                width=size["width"],
                height=size["height"],
                url=url,
                final_url=final_url,
            )
            png: bytes | None = None
            try:
                png = capture_screenshot(page, self._max_screenshot_height)
            except Exception:
                logger.exception("uiux_screenshot_failed viewport=%s", viewport_name)
            return snapshot, png
        finally:
            self._close_page(page, context)


def _wait_usable(page: Any) -> None:
    try:
        page.wait_for_load_state("load", timeout=8_000)
    except Exception:
        pass
    try:
        page.wait_for_load_state("networkidle", timeout=3_000)
    except Exception:
        pass
    try:
        page.wait_for_selector("body", timeout=3_000)
    except Exception:
        pass
