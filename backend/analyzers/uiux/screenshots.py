"""Bounded homepage screenshots. Never expose filesystem paths."""

from __future__ import annotations

from typing import Any

from backend.analyzers.uiux.config import MAX_SCREENSHOT_HEIGHT


def capture_screenshot(page: Any, max_height: int = MAX_SCREENSHOT_HEIGHT) -> bytes:
    scroll_height = page.evaluate(
        """() => Math.max(document.documentElement.scrollHeight || 0, document.body ? document.body.scrollHeight : 0)"""
    )
    try:
        height = int(scroll_height or 0)
    except (TypeError, ValueError):
        height = 0
    if 0 < height <= max_height:
        return page.screenshot(full_page=True, type="png", timeout=15_000)
    return page.screenshot(full_page=False, type="png", timeout=15_000)
