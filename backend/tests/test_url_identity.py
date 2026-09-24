from __future__ import annotations

from backend.services.url_identity import is_skippable_resource, normalize_page_url, same_site, url_path, url_path_depth


def test_normalize_trailing_slash_and_fragment() -> None:
    assert normalize_page_url("https://example.com") == normalize_page_url("https://example.com/")
    assert normalize_page_url("https://EXAMPLE.com/about/#top") == "https://example.com/about"
    assert normalize_page_url("https://example.com/a?q=1#x") == "https://example.com/a?q=1"


def test_normalize_default_ports() -> None:
    assert normalize_page_url("https://example.com:443/about") == "https://example.com/about"
    assert normalize_page_url("http://example.com:80/about") == "http://example.com/about"


def test_same_site_and_resources() -> None:
    assert same_site("https://example.com/about", "https://example.com/")
    assert not same_site("https://other.example/about", "https://example.com/")
    assert is_skippable_resource("https://example.com/logo.png")
    assert is_skippable_resource("https://example.com/app.js")
    assert is_skippable_resource("mailto:hi@example.com")
    assert not is_skippable_resource("https://example.com/about")
    assert not is_skippable_resource("https://example.com/about/")


def test_url_path_depth_is_not_crawl_depth() -> None:
    assert url_path("https://example.com/services/web-development/") == "/services/web-development"
    assert url_path_depth("https://example.com/") == 0
    assert url_path_depth("https://example.com/about") == 1
    assert url_path_depth("https://example.com/services/web-development/") == 2
