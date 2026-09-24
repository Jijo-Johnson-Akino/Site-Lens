from __future__ import annotations

from pathlib import Path

import pytest

from backend.analyzers.uiux.config import VIEWPORTS
from backend.errors import ScanError
from backend.services.url_validator import UrlValidator
from backend.tests.uiux_helpers import load_uiux_fixture


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as playwright:
            return Path(playwright.chromium.executable_path).exists()
    except Exception:
        return False


HAS_CHROMIUM = _chromium_available()


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_playwright_fixtures_overflow_images_nav_and_overlap() -> None:
    from backend.analyzers.uiux.analyzer import analyze_snapshots
    from backend.analyzers.uiux.browser import UIUXBrowser

    with UIUXBrowser() as browser:
        good, good_png = browser.capture_html(load_uiux_fixture("responsive_good.html"), "mobile")
        overflow, overflow_png = browser.capture_html(load_uiux_fixture("horizontal_overflow.html"), "mobile")
        broken, _ = browser.capture_html(load_uiux_fixture("broken_image.html"), "desktop")
        overlap, _ = browser.capture_html(load_uiux_fixture("overlapping_elements.html"), "desktop")
        nav, _ = browser.capture_html(load_uiux_fixture("mobile_nav.html"), "mobile")
        desktop, desktop_png = browser.capture_html(load_uiux_fixture("responsive_good.html"), "desktop")
        tablet, tablet_png = browser.capture_html(load_uiux_fixture("responsive_good.html"), "tablet")

    assert good.viewport["name"] == "mobile"
    assert good.viewport["width"] == VIEWPORTS["mobile"]["width"]
    assert good.layout["horizontal_overflow"] is False
    assert good.navigation.get("exists") is True
    assert good_png and good_png[:8] == b"\x89PNG\r\n\x1a\n"
    assert desktop.viewport["width"] == 1440
    assert tablet.viewport["width"] == 768
    assert desktop_png and tablet_png
    assert overflow_png

    assert overflow.layout["horizontal_overflow"] is True
    assert overflow.layout["overflow_px"] > 8
    assert any("hero" in str(item.get("selector")) for item in overflow.overflowing_elements) or overflow.layout["overflow_px"] > 100

    assert any(item.get("broken") for item in broken.images)

    overlap_result = analyze_snapshots([overlap])
    overlap_check = next(check for check in overlap_result.checks if check.check_id == "UX-LAYOUT-002")
    assert overlap_check.status in {"warning", "pass"}

    assert nav.navigation.get("overflow") or nav.layout.get("horizontal_overflow")


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_browser_cleanup_after_failure() -> None:
    from backend.analyzers.uiux.browser import UIUXBrowser

    browser = UIUXBrowser(UrlValidator())
    browser.launch()
    assert browser._browser is not None
    with pytest.raises(ScanError):
        browser.capture_url("http://127.0.0.1", "mobile")
    browser.close()
    assert browser._browser is None
    assert browser._playwright is None
