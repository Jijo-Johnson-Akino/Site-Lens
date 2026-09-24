from __future__ import annotations

from pathlib import Path

import pytest

from backend.analyzers.mobile.analyzer import PlaywrightMobileAnalyzer
from backend.analyzers.mobile.browser import run_mobile_session
from backend.analyzers.uiux.browser import UIUXBrowser
from backend.tests.mobile_helpers import by_id, load_mobile_fixture


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
def test_playwright_mobile_fixtures_and_measurements() -> None:
    analyzer = PlaywrightMobileAnalyzer()
    good = analyzer.analyze_html(load_mobile_fixture("responsive.html"), capture_shots=True)
    overflow = analyzer.analyze_html(load_mobile_fixture("fixed_width.html"), capture_shots=False)
    image = analyzer.analyze_html(load_mobile_fixture("oversized_image.html"), capture_shots=False)
    wide_table = analyzer.analyze_html(load_mobile_fixture("wide_table.html"), capture_shots=False)
    scroll_table = analyzer.analyze_html(load_mobile_fixture("responsive_table.html"), capture_shots=False)
    menu = analyzer.analyze_html(load_mobile_fixture("mobile_menu.html"), capture_shots=False)
    broken = analyzer.analyze_html(load_mobile_fixture("broken_menu.html"), capture_shots=False)
    small = analyzer.analyze_html(load_mobile_fixture("small_buttons.html"), capture_shots=False)
    touch = analyzer.analyze_html(load_mobile_fixture("proper_touch.html"), capture_shots=False)
    text = analyzer.analyze_html(load_mobile_fixture("small_text.html"), capture_shots=False)
    heading = analyzer.analyze_html(load_mobile_fixture("clipped_heading.html"), capture_shots=False)
    form = analyzer.analyze_html(load_mobile_fixture("wide_form.html"), capture_shots=False)
    banner = analyzer.analyze_html(load_mobile_fixture("fixed_banner.html"), capture_shots=False)
    overlay = analyzer.analyze_html(load_mobile_fixture("large_overlay.html"), capture_shots=False)
    cta = analyzer.analyze_html(load_mobile_fixture("cta_offscreen.html"), capture_shots=False)
    missing = analyzer.analyze_html(load_mobile_fixture("missing_viewport.html"), capture_shots=False)
    viewport = analyzer.analyze_html(load_mobile_fixture("viewport_ok.html"), capture_shots=False)
    fluid = analyzer.analyze_html(load_mobile_fixture("responsive_image.html"), capture_shots=False)

    assert good.environment.browser == "chromium"
    assert good.environment.device_profile == "mobile"
    assert good.viewport["width"] == 390
    assert good.environment.touch_enabled is True
    assert by_id(good, "MOBILE-OVERFLOW-001").status == "pass"
    assert good.screenshots
    assert good.screenshots[0].url.startswith("/api/scans/")
    assert "path" not in good.screenshots[0].model_dump()

    assert overflow.viewport["horizontal_overflow"] is True
    assert (overflow.viewport.get("overflow_px") or 0) > 2
    assert by_id(overflow, "MOBILE-OVERFLOW-001").status in {"warning", "fail"}
    assert by_id(image, "MOBILE-IMG-001").status == "warning"
    assert by_id(wide_table, "MOBILE-TABLE-001").status in {"warning", "fail"}
    assert by_id(scroll_table, "MOBILE-TABLE-001").status == "pass"
    assert menu.navigation.get("mobile_menu_detected") is True
    assert by_id(broken, "MOBILE-NAV-001").status in {"fail", "warning"}
    assert by_id(small, "MOBILE-TOUCH-001").status == "warning"
    assert by_id(touch, "MOBILE-TOUCH-001").status == "pass"
    assert by_id(text, "MOBILE-TYPE-001").status == "warning"
    assert by_id(heading, "MOBILE-CONTENT-001").status == "warning" or by_id(heading, "MOBILE-TYPE-002").status == "warning"
    assert by_id(form, "MOBILE-FORM-001").status == "warning"
    assert by_id(banner, "MOBILE-FIXED-001").status == "warning" or by_id(overlay, "MOBILE-OVERLAY-001").status == "warning"
    assert by_id(overlay, "MOBILE-OVERLAY-001").status == "warning"
    assert by_id(cta, "MOBILE-CTA-001").status == "warning"
    assert by_id(missing, "MOBILE-VIEW-001").status == "fail"
    assert by_id(viewport, "MOBILE-VIEW-001").status == "pass"
    assert by_id(fluid, "MOBILE-IMG-001").status == "pass"


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_playwright_mobile_integration_measures_and_screenshots() -> None:
    html = load_mobile_fixture("responsive.html")
    with UIUXBrowser() as browser:
        payload = run_mobile_session(
            browser,
            html=html,
            page_url="https://example.com/",
            capture_shots=True,
            interact_menu=False,
        )
    snapshot = payload["snapshot"]
    shots = payload["shots"]
    env = payload["environment"]
    assert snapshot.viewport.get("width") == 390
    assert snapshot.layout.get("viewport_width") == 390
    assert snapshot.layout.get("document_width") is not None
    assert env.get("touch_enabled") is True
    interactive = snapshot.touch_targets.get("interactive_elements") or 0
    assert interactive >= 1
    png = shots.get("viewport")
    assert png and png[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_mobile_browser_cleanup_after_blocked_url() -> None:
    from backend.errors import ScanError
    from backend.services.url_validator import UrlValidator

    browser = UIUXBrowser(UrlValidator())
    browser.launch()
    assert browser._browser is not None
    with pytest.raises(ScanError):
        run_mobile_session(browser, url="http://127.0.0.1", capture_shots=False)
    browser.close()
    assert browser._browser is None
    assert browser._playwright is None
