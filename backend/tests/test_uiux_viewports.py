from __future__ import annotations

from backend.analyzers.uiux.config import VIEWPORTS, enabled_viewports
from backend.analyzers.uiux.sanitizer import sanitize_selector


def test_default_viewports() -> None:
    assert VIEWPORTS["desktop"] == {"width": 1440, "height": 900}
    assert VIEWPORTS["tablet"] == {"width": 768, "height": 1024}
    assert VIEWPORTS["mobile"] == {"width": 390, "height": 844}
    enabled = enabled_viewports()
    assert list(enabled) == ["desktop", "tablet", "mobile"]


def test_sanitize_strips_sensitive_selectors() -> None:
    assert sanitize_selector("a#user-email-token") == "a"
    assert sanitize_selector("div.hero-container") == "div.hero-container"
    assert sanitize_selector("input#sessionabcdef1234567890") == "input"
