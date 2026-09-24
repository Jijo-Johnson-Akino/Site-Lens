"""Deterministic mobile results for API tests that must not launch Chromium."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.analyzers.mobile.analyzer import ProgressFn, analyze_snapshot
from backend.analyzers.mobile.config import PRIMARY_VIEWPORT
from backend.analyzers.mobile.models import MobileResult, MobileSnapshot, ScreenshotMeta
from backend.analyzers.mobile.screenshots import PRIMARY_FULL_KEY, PRIMARY_KEY, screenshot_url
from backend.analyzers.uiux.stub import MINIMAL_PNG
from backend.store.screenshots import InMemoryScreenshotStore, ScreenshotRepository


def snapshot_from_parts(
    *,
    url: str = "https://example.com/",
    width: int = 390,
    height: int = 844,
    overflow: bool = False,
    overflow_px: int = 0,
    overflowing: list | None = None,
    viewport_present: bool = True,
    viewport_content: str = "width=device-width, initial-scale=1",
    nav_exists: bool = True,
    nav_visible: bool = True,
    menu_button: str | None = None,
    menu_opened: bool = False,
    menu_tested: bool = False,
    menu_named: bool = True,
    nav_overflow: bool = False,
    touch_items: list | None = None,
    interactive_elements: int | None = None,
    forms: list | None = None,
    images: list | None = None,
    tables: list | None = None,
    media: list | None = None,
    overlays: list | None = None,
    sticky: list | None = None,
    small_text: list | None = None,
    clipped_text: list | None = None,
    overflowing_headings: list | None = None,
    headings: list | None = None,
    cta: dict | None = None,
    main_visible: bool = True,
    h1_clipped: bool = False,
    min_width_elements: list | None = None,
    clipped_containers: list | None = None,
    offscreen: list | None = None,
    spacing: dict | None = None,
    touch_enabled: bool = True,
    extra: dict | None = None,
) -> MobileSnapshot:
    size_w = width
    layout_width = size_w + (overflow_px if overflow else 0)
    heading_list = headings
    if heading_list is None:
        heading_list = [
            {
                "selector": "h1",
                "text": "Welcome",
                "visible": True,
                "in_viewport": not h1_clipped,
                "clipped": h1_clipped,
                "overflow_px": 40 if h1_clipped else 0,
            }
        ]
    cta_data = cta if cta is not None else {
        "exists": True,
        "selector": "a.cta",
        "text": "Get Started",
        "visible": True,
        "in_viewport": True,
        "clipped": False,
        "overflow_px": 0,
        "width": 160,
        "height": 44,
        "min_dim": 44,
    }
    items = touch_items if touch_items is not None else [
        {"selector": "a.cta", "width": 160, "height": 44, "min_dim": 44, "below_baseline": False, "very_small": False, "in_paragraph": False}
    ]
    data = {
        "viewport": {"name": "mobile", "width": width, "height": height},
        "page": {"url": url, "final_url": url, "ready_state": "complete"},
        "environment": {
            "browser": "chromium",
            "device_profile": "mobile",
            "viewport": {"width": width, "height": height},
            "touch_enabled": touch_enabled,
            "device_scale_factor": 2,
            "user_agent_category": "mobile",
            "is_mobile_emulation": True,
        },
        "layout": {
            "scroll_width": layout_width,
            "document_width": layout_width,
            "body_scroll_width": layout_width,
            "viewport_width": size_w,
            "viewport_height": height,
            "horizontal_overflow": overflow,
            "overflow_px": overflow_px if overflow else 0,
        },
        "viewport_meta": {
            "present": viewport_present,
            "content": viewport_content if viewport_present else None,
            "width": "device-width" if viewport_present else None,
            "device_width": viewport_present and "device-width" in (viewport_content or ""),
            "zoom_restricted": viewport_present and ("user-scalable=no" in (viewport_content or "") or "maximum-scale=1" in (viewport_content or "")),
            "fixed_width": viewport_present and "width=320" in (viewport_content or ""),
        },
        "navigation": {
            "exists": nav_exists,
            "visible": nav_visible,
            "links": 4 if nav_exists else 0,
            "overflow": nav_overflow,
            "menu_button": menu_button,
            "menu_named": menu_named,
            "menu_name": "Menu" if menu_named else "",
            "menu_safe": True,
            "menu_tested": menu_tested,
            "menu_opened": menu_opened,
        },
        "overflowing_elements": overflowing or [],
        "min_width_elements": min_width_elements or [],
        "clipped_containers": clipped_containers or [],
        "offscreen_critical": offscreen or [],
        "small_text": small_text or [],
        "clipped_text": clipped_text or [],
        "overflowing_headings": overflowing_headings or [],
        "headings": heading_list,
        "touch_targets": {
            "interactive_elements": interactive_elements if interactive_elements is not None else len(items),
            "below_baseline": sum(1 for item in items if item.get("below_baseline")),
            "very_small": sum(1 for item in items if item.get("very_small")),
            "items": [item for item in items if item.get("below_baseline")],
            "close_pairs": [],
        },
        "forms": forms or [],
        "images": images or [],
        "tables": tables or [],
        "media": media or [],
        "overlays": overlays or [],
        "sticky_elements": sticky or [],
        "cta": cta_data,
        "content": {
            "h1": len(heading_list),
            "h1_visible": True,
            "h1_in_viewport": not h1_clipped,
            "h1_clipped": h1_clipped,
            "main_visible": main_visible,
            "main_selector": "main",
        },
        "spacing": spacing or {"edge_text": [], "excessive_padding": []},
        "scroll": {"horizontal_overflow_on_scroll": overflow},
    }
    if extra:
        data.update(extra)
    return MobileSnapshot.model_validate(data)


class StubMobileAnalyzer:
    def __init__(self, screenshot_store: ScreenshotRepository | None = None) -> None:
        self._screenshots = screenshot_store or InMemoryScreenshotStore()

    async def analyze(self, *, url: str, scan_id: str, on_progress: ProgressFn | None = None) -> MobileResult:
        if on_progress:
            maybe = on_progress(99, "Mobile Analysis")
            if maybe is not None:
                await maybe
        created = datetime.now(timezone.utc).isoformat()
        self._screenshots.put(scan_id, PRIMARY_KEY, MINIMAL_PNG)
        self._screenshots.put(scan_id, PRIMARY_FULL_KEY, MINIMAL_PNG)
        metas = [
            ScreenshotMeta(
                viewport=PRIMARY_KEY,
                width=PRIMARY_VIEWPORT["width"],
                height=PRIMARY_VIEWPORT["height"],
                url=screenshot_url(scan_id, PRIMARY_KEY),
                created_at=created,
                kind="viewport",
            ),
            ScreenshotMeta(
                viewport=PRIMARY_FULL_KEY,
                width=PRIMARY_VIEWPORT["width"],
                height=PRIMARY_VIEWPORT["height"],
                url=screenshot_url(scan_id, PRIMARY_FULL_KEY),
                created_at=created,
                kind="full",
            ),
        ]
        return analyze_snapshot(snapshot_from_parts(url=url), screenshots=metas)
