from __future__ import annotations

from pathlib import Path

import pytest

from backend.errors import ScanError
from backend.services.url_validator import UrlValidator
from backend.tests.a11y_helpers import by_id, load_a11y_fixture


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


def _analyze_with(browser, html: str):
    from backend.analyzers.accessibility.analyzer import _inspect_page, analyze_snapshot

    snapshot, axe = browser.inspect(
        lambda page, final_url: _inspect_page(page, final_url, "https://example.com/"),
        html=html,
        viewport_name="desktop",
        page_url="https://example.com/",
    )
    return analyze_snapshot(snapshot, axe)


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_axe_runs_and_reports_real_pass_and_violation() -> None:
    from backend.analyzers.uiux.browser import UIUXBrowser

    with UIUXBrowser() as browser:
        accessible = _analyze_with(browser, load_a11y_fixture("accessible.html"))
        contrast = _analyze_with(browser, load_a11y_fixture("contrast.html"))

    assert accessible.tool.name == "axe-core"
    assert accessible.tool.version
    assert accessible.tool.version.startswith("4.")
    assert accessible.tool.axe_passes > 0
    assert accessible.tool.automated is True
    assert "wcag2aa" in accessible.tool.tags
    assert by_id(accessible, "A11Y-DOC-001").status == "pass"
    assert by_id(accessible, "A11Y-FORM-001").status == "pass"
    assert by_id(accessible, "A11Y-CTRL-001").status == "pass"
    assert by_id(accessible, "A11Y-IMG-002").status == "pass"
    assert accessible.score >= 70
    ids = [item.check_id for item in accessible.checks]
    assert len(ids) == len(set(ids))

    contrast_check = by_id(contrast, "A11Y-CONTRAST-001")
    assert contrast_check.status == "fail"
    assert contrast_check.source == "axe"
    assert contrast_check.wcag_reference
    assert contrast.tool.axe_violations >= 1
    assert contrast.score < accessible.score


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_playwright_fixtures_cover_required_cases() -> None:
    from backend.analyzers.uiux.browser import UIUXBrowser

    with UIUXBrowser() as browser:
        missing_lang = _analyze_with(browser, load_a11y_fixture("missing_lang.html"))
        image = _analyze_with(browser, load_a11y_fixture("image_no_alt.html"))
        button = _analyze_with(browser, load_a11y_fixture("empty_button.html"))
        unlabeled = _analyze_with(browser, load_a11y_fixture("input_no_label.html"))
        dupes = _analyze_with(browser, load_a11y_fixture("duplicate_ids.html"))
        aria = _analyze_with(browser, load_a11y_fixture("invalid_aria.html"))
        labeled = _analyze_with(browser, load_a11y_fixture("labeled_form.html"))
        icon = _analyze_with(browser, load_a11y_fixture("icon_button_aria.html"))
        decorative = _analyze_with(browser, load_a11y_fixture("decorative_alt.html"))
        navs = _analyze_with(browser, load_a11y_fixture("unnamed_navs.html"))
        iframe = _analyze_with(browser, load_a11y_fixture("iframe_no_title.html"))
        mains = _analyze_with(browser, load_a11y_fixture("duplicate_main.html"))
        hidden = _analyze_with(browser, load_a11y_fixture("aria_hidden_focusable.html"))
        trap = _analyze_with(browser, load_a11y_fixture("focus_trap.html"))
        french = _analyze_with(browser, load_a11y_fixture("french.html"))

    assert by_id(missing_lang, "A11Y-DOC-001").status in {"fail", "warning"}
    assert by_id(image, "A11Y-IMG-001").status == "fail"
    assert by_id(button, "A11Y-CTRL-001").status == "fail"
    assert by_id(unlabeled, "A11Y-FORM-001").status == "fail"
    assert by_id(dupes, "A11Y-ID-001").status == "fail"
    assert by_id(aria, "A11Y-ARIA-001").status == "fail" or any(
        item.status == "fail" and item.source == "axe" and "aria" in f"{item.check_id}{item.axe_rule_id or ''}".lower()
        for item in aria.checks
    )
    assert by_id(labeled, "A11Y-FORM-001").status == "pass"
    assert by_id(icon, "A11Y-CTRL-001").status == "pass"
    assert by_id(decorative, "A11Y-IMG-001").status == "pass"
    assert by_id(navs, "A11Y-LAND-003").status == "warning"
    assert by_id(iframe, "A11Y-IFRAME-001").status == "fail"
    assert by_id(mains, "A11Y-LAND-002").status in {"fail", "warning"}
    assert by_id(hidden, "A11Y-ARIA-003").status == "fail"
    trap_check = by_id(trap, "A11Y-KEY-001")
    assert trap_check.status in {"fail", "warning", "pass"}
    if trap_check.status == "pass":
        assert "does not prove complete keyboard accessibility" in trap_check.message
    assert by_id(french, "A11Y-DOC-001").status == "pass"
    assert by_id(french, "A11Y-DOC-003").status == "pass"


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_accessibility_browser_cleanup_after_ssrf_block() -> None:
    from backend.analyzers.uiux.browser import UIUXBrowser

    browser = UIUXBrowser(UrlValidator())
    browser.launch()
    assert browser._browser is not None
    with pytest.raises(ScanError):
        browser.inspect(lambda page, url: page.title(), url="http://127.0.0.1")
    browser.close()
    assert browser._browser is None
    assert browser._playwright is None
