"""Deterministic UI/UX results for tests that must not launch Chromium."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.analyzers.uiux.analyzer import ProgressFn, analyze_snapshots
from backend.analyzers.uiux.config import VIEWPORTS
from backend.analyzers.uiux.models import ScreenshotMeta, UiuxResult, ViewportSnapshot
from backend.store.screenshots import InMemoryScreenshotStore, ScreenshotRepository

# 1x1 PNG
MINIMAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def snapshot_from_parts(
    viewport: str,
    *,
    url: str = "https://example.com/",
    overflow: bool = False,
    overflow_px: int = 0,
    overflowing: list | None = None,
    fixed_width: list | None = None,
    nav_exists: bool = True,
    nav_visible: bool = True,
    nav_links: int = 5,
    nav_overflow: bool = False,
    menu_button: str | None = None,
    logo: dict | None = None,
    h1_visible: bool = True,
    headings: list | None = None,
    buttons: list | None = None,
    links: list | None = None,
    cta: dict | None = None,
    forms: list | None = None,
    images: list | None = None,
    overlays: list | None = None,
    overlapping: list | None = None,
    offscreen: list | None = None,
    small_text: list | None = None,
    clipped_text: list | None = None,
    empty_sections: list | None = None,
    main_visible: bool = True,
    ready_state: str = "complete",
    extra: dict | None = None,
) -> ViewportSnapshot:
    size = VIEWPORTS[viewport]
    heading_list = headings
    if heading_list is None:
        heading_list = (
            [{"selector": "h1", "text": "Home", "visible": h1_visible, "in_viewport": h1_visible}]
            if h1_visible or headings is not None
            else []
        )
        if not h1_visible and headings is None:
            heading_list = [{"selector": "h1", "text": "Home", "visible": False, "in_viewport": False}]
    button_list = buttons if buttons is not None else [{"selector": "a.cta", "text": "Get Started", "empty": False, "disabled": False, "visible": True, "in_viewport": True, "clipped": False, "overflow_px": 0, "pointer_events": "auto", "width": 160, "height": 44}]
    link_list = links if links is not None else [{"selector": "a.nav", "text": "About", "href": "/about", "visible": True, "in_viewport": True, "clipped": False}]
    cta_data = cta if cta is not None else {
        "exists": True,
        "selector": "a.cta",
        "text": "Get Started",
        "visible": True,
        "in_viewport": True,
        "clipped": False,
        "overflow_px": 0,
    }
    data = {
        "viewport": {"name": viewport, "width": size["width"], "height": size["height"]},
        "page": {"url": url, "final_url": url, "ready_state": ready_state},
        "layout": {
            "scroll_width": size["width"] + (overflow_px if overflow else 0),
            "scroll_height": size["height"],
            "viewport_width": size["width"],
            "viewport_height": size["height"],
            "horizontal_overflow": overflow,
            "overflow_px": overflow_px if overflow else 0,
        },
        "navigation": {
            "exists": nav_exists,
            "has_nav_element": nav_exists,
            "visible": nav_visible,
            "links": nav_links,
            "overflow": nav_overflow,
            "overflow_px": 48 if nav_overflow else 0,
            "overflow_selector": "nav a" if nav_overflow else None,
            "menu_button": menu_button,
            "logo": logo if logo is not None else {"exists": True, "selector": "a.logo", "href": "/", "visible": True},
        },
        "content": {"h1": len(heading_list), "h1_visible": any(item.get("visible") for item in heading_list), "paragraphs": 4},
        "interactive": {"buttons": len(button_list), "links": max(len(link_list), nav_links), "forms": len(forms or [])},
        "typography": {"small_count": len(small_text or []), "clipped_count": len(clipped_text or [])},
        "images": images or [],
        "forms": forms or [],
        "overlays": overlays or [],
        "overflowing_elements": overflowing or [],
        "fixed_width_elements": fixed_width or [],
        "overlapping_pairs": overlapping or [],
        "clipped_text": clipped_text or [],
        "small_text": small_text or [],
        "empty_sections": empty_sections or [],
        "offscreen_critical": offscreen or [],
        "cta": cta_data,
        "main": {"exists": True, "visible": main_visible, "selector": "main"},
        "load": {"ready_state": ready_state, "main_visible": main_visible},
        "buttons": button_list,
        "links": link_list,
        "headings": heading_list,
        "disabled_primary": [item for item in button_list if item.get("disabled")],
    }
    if extra:
        data.update(extra)
    return ViewportSnapshot.model_validate(data)


def good_snapshots(url: str = "https://example.com/") -> list[ViewportSnapshot]:
    return [snapshot_from_parts(name, url=url) for name in VIEWPORTS]


class StubUiuxAnalyzer:
    def __init__(self, screenshot_store: ScreenshotRepository | None = None) -> None:
        self._screenshots = screenshot_store or InMemoryScreenshotStore()

    async def analyze(self, *, url: str, scan_id: str, on_progress: ProgressFn | None = None) -> UiuxResult:
        if on_progress:
            maybe = on_progress(75, "Rendering website")
            if maybe is not None:
                await maybe
        snapshots = good_snapshots(url)
        created = datetime.now(timezone.utc).isoformat()
        metas: list[ScreenshotMeta] = []
        for name, size in VIEWPORTS.items():
            self._screenshots.put(scan_id, name, MINIMAL_PNG)
            metas.append(
                ScreenshotMeta(
                    viewport=name,
                    width=size["width"],
                    height=size["height"],
                    url=f"/api/scans/{scan_id}/uiux/screenshots/{name}",
                    created_at=created,
                )
            )
        if on_progress:
            maybe = on_progress(82, "UI/UX analysis")
            if maybe is not None:
                await maybe
        result = analyze_snapshots(snapshots, metas)
        if on_progress:
            maybe = on_progress(88, "Capturing screenshots")
            if maybe is not None:
                await maybe
        return result
