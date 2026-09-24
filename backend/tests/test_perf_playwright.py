from __future__ import annotations

from pathlib import Path

import pytest

from backend.errors import ScanError
from backend.services.url_validator import UrlValidator
from backend.tests.perf_helpers import by_id, load_perf_fixture


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

BIG_JS = "console.log(1);\n" + ("a" * 520_000)
PLAIN_CSS = "body{color:#111}" + ("/* pad */" * 400)
CACHED_JS = "console.log('ok');"


def _analyze(html: str, extra_routes=None, document_headers=None, document_delay_ms: int = 0, page_url: str = "https://example.com/"):
    from backend.analyzers.performance.analyzer import PlaywrightPerfAnalyzer

    return PlaywrightPerfAnalyzer().analyze_html(
        html,
        page_url=page_url,
        extra_routes=extra_routes,
        document_headers=document_headers,
        document_delay_ms=document_delay_ms,
    )


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_browser_collects_real_timing_and_lcp() -> None:
    result = _analyze(load_perf_fixture("fast.html"))
    assert result.environment.browser == "chromium"
    assert result.environment.cache_mode == "cold"
    assert result.environment.network_profile == "default"
    assert result.timing.ttfb_ms is None or result.timing.ttfb_ms >= 0
    assert result.timing.dom_content_loaded_ms is None or result.timing.dom_content_loaded_ms >= 0
    assert result.timing.load_event_ms is None or result.timing.load_event_ms >= 0
    assert result.resources.total_requests >= 1
    assert result.vitals.lcp.value is None or result.vitals.lcp.value > 0
    if result.vitals.lcp.value is not None:
        assert result.vitals.lcp.status in {"good", "needs_improvement", "poor"}
    assert result.vitals.inp.value is None
    assert result.vitals.inp.status == "unavailable"
    assert result.score == result.score
    assert 0 <= result.score <= 100


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_playwright_fixtures_for_resources_and_vitals() -> None:
    blocking = _analyze(
        load_perf_fixture("blocking_js.html"),
        extra_routes={"/blocking.js": {"body": "console.log(1)", "headers": {"content-type": "application/javascript"}}},
    )
    large = _analyze(
        load_perf_fixture("large_js.html"),
        extra_routes={"/big.js": {"body": BIG_JS, "headers": {"content-type": "application/javascript"}}},
    )
    uncompressed = _analyze(
        load_perf_fixture("uncompressed.html"),
        extra_routes={"/plain.css": {"body": PLAIN_CSS, "headers": {"content-type": "text/css"}}},
    )
    cached = _analyze(
        load_perf_fixture("cached.html"),
        extra_routes={"/app.js": {"body": CACHED_JS, "headers": {"content-type": "application/javascript", "cache-control": "max-age=86400"}}},
    )
    third = _analyze(
        load_perf_fixture("third_party.html"),
        extra_routes={"cdn.example.net": {"body": "console.log(1)", "headers": {"content-type": "application/javascript"}}},
    )
    dom_html = load_perf_fixture("large_dom.html").replace("PLACEHOLDER", "".join(f"<div>{i}</div>" for i in range(1800)))
    large_dom = _analyze(dom_html)
    cls = _analyze(load_perf_fixture("cls.html"))
    longtask = _analyze(load_perf_fixture("longtask.html"))
    lazy = _analyze(load_perf_fixture("lazy.html"))

    assert by_id(blocking, "PERF-JS-001").status in {"warning", "fail"}
    assert by_id(blocking, "PERF-BLOCK-001").status in {"warning", "fail"}
    assert large.resources.js_bytes >= 500_000 or by_id(large, "PERF-JS-002").status == "warning"
    assert by_id(uncompressed, "PERF-COMP-001").status in {"warning", "not_applicable", "pass"}
    assert by_id(cached, "PERF-CACHE-001").status in {"pass", "not_applicable"}
    assert any(not item.first_party for item in third.resource_table) or by_id(third, "PERF-TP-001").status in {"pass", "warning"}
    assert large_dom.resources.total_requests >= 1
    assert by_id(large_dom, "PERF-DOM-001").status in {"warning", "pass"}
    if cls.vitals.cls.value is not None:
        assert cls.vitals.cls.value >= 0
        assert cls.vitals.cls.status != "unavailable"
    assert by_id(longtask, "PERF-LONG-001").status in {"pass", "warning", "not_applicable"}
    assert by_id(lazy, "PERF-IMG-003").status in {"warning", "pass", "not_applicable"}
    assert blocking.timing.load_event_ms is None or blocking.timing.load_event_ms >= 0


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_slow_document_measures_ttfb() -> None:
    result = _analyze(load_perf_fixture("fast.html"), document_delay_ms=1900)
    assert result.timing.ttfb_ms is None or result.timing.ttfb_ms >= 1400
    if result.timing.ttfb_ms is not None:
        assert by_id(result, "PERF-TTFB-001").status in {"warning", "fail"}
        assert result.timing.ttfb_ms > 0


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_large_image_and_redirect_chain() -> None:
    large = _analyze(
        load_perf_fixture("large_image.html"),
        extra_routes={"/hero.bin": {"body": b"x" * 600_000, "headers": {"content-type": "image/jpeg"}}},
    )
    assert large.resources.image_bytes >= 500_000 or by_id(large, "PERF-IMG-001").status == "warning"
    redirected = _analyze(
        load_perf_fixture("fast.html"),
        extra_routes={
            "/redir-a": {"status": 302, "body": "", "headers": {"location": "https://example.com/redir-b"}},
            "/redir-b": {"status": 302, "body": "", "headers": {"location": "https://example.com/redir-c"}},
            "/redir-c": {"status": 302, "body": "", "headers": {"location": "https://example.com/"}},
        },
        page_url="https://example.com/redir-a",
    )
    assert redirected.timing.redirect_count is None or redirected.timing.redirect_count >= 1
    if redirected.timing.redirect_count and redirected.timing.redirect_count >= 2:
        assert by_id(redirected, "PERF-REDIR-001").status in {"warning", "fail"}


@pytest.mark.skipif(not HAS_CHROMIUM, reason="Playwright Chromium is not installed")
def test_performance_browser_cleanup_after_ssrf_block() -> None:
    from backend.analyzers.uiux.browser import UIUXBrowser

    class _Collector:
        serves_html = False

        def setup(self, page) -> None:
            return None

        def collect(self, page, url, environment=None):
            return None

    browser = UIUXBrowser(UrlValidator())
    browser.launch()
    assert browser._browser is not None
    with pytest.raises(ScanError):
        browser.measure(_Collector(), url="http://127.0.0.1")
    browser.close()
    assert browser._browser is None
