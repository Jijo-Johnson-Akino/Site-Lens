"""Mobile Playwright session using the shared Phase 6 UIUXBrowser."""

from __future__ import annotations

import logging
from typing import Any

from backend.analyzers.mobile.config import (
    DEVICE_SCALE_FACTOR,
    MOBILE_USER_AGENT,
    PRIMARY_VIEWPORT,
    SCROLL_STEPS,
)
from backend.analyzers.mobile.measurements import OVERFLOW_JS, measurement_script, normalize_snapshot
from backend.analyzers.mobile.models import MobileSnapshot
from backend.analyzers.mobile.navigation import probe_menu
from backend.analyzers.uiux.browser import UIUXBrowser
from backend.analyzers.uiux.screenshots import capture_screenshot

logger = logging.getLogger("sitebench.mobile")


def run_mobile_session(
    browser: UIUXBrowser,
    *,
    size: dict[str, int] | None = None,
    viewport_name: str = "mobile",
    url: str | None = None,
    html: str | None = None,
    page_url: str = "https://example.com/",
    capture_shots: bool = True,
    interact_menu: bool = True,
) -> dict[str, Any]:
    viewport = dict(size or PRIMARY_VIEWPORT)

    def inspector(page: Any, final_url: str) -> dict[str, Any]:
        raw = page.evaluate(measurement_script()) or {}
        nav_probe: dict[str, Any] = {}
        if interact_menu:
            try:
                nav_probe = probe_menu(page, raw.get("navigation") or {})
            except Exception:
                logger.info("mobile_menu_probe_failed")
                nav_probe = {"menu_tested": False, "reason": "interaction_failed"}
        scroll = _bounded_scroll(page)
        shots: dict[str, bytes | None] = {"viewport": None, "full": None}
        if capture_shots:
            try:
                shots["viewport"] = page.screenshot(full_page=False, type="png", timeout=15_000)
            except Exception:
                logger.exception("mobile_viewport_screenshot_failed")
            try:
                shots["full"] = capture_screenshot(page)
            except Exception:
                logger.exception("mobile_full_screenshot_failed")
        env_live = _environment(page, browser, viewport)
        snapshot = normalize_snapshot(
            raw,
            viewport_name=viewport_name,
            width=viewport["width"],
            height=viewport["height"],
            url=url or page_url,
            final_url=final_url,
        )
        nav = dict(snapshot.navigation)
        nav.update(nav_probe)
        snapshot = snapshot.model_copy(update={"navigation": nav, "scroll": scroll, "environment": {**snapshot.environment, **env_live}})
        return {"snapshot": snapshot, "shots": shots, "environment": env_live, "final_url": final_url}

    return browser.inspect(
        inspector,
        url=url,
        html=html,
        viewport_name=viewport_name,
        page_url=page_url,
        mobile_emulation=True,
        viewport_size=viewport,
        user_agent=MOBILE_USER_AGENT,
        device_scale_factor=DEVICE_SCALE_FACTOR,
    )


def _bounded_scroll(page: Any) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    try:
        initial = page.evaluate(OVERFLOW_JS) or {}
        samples.append({"step": 0, **initial})
        steps = max(0, min(int(SCROLL_STEPS), 4))
        for index in range(1, steps + 1):
            page.evaluate("() => window.scrollBy(0, window.innerHeight)")
            page.wait_for_timeout(120)
            samples.append({"step": index, **(page.evaluate(OVERFLOW_JS) or {})})
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(80)
    except Exception:
        logger.info("mobile_scroll_probe_failed")
        return {"samples": samples, "horizontal_overflow_on_scroll": None}
    overflow = any(int(item.get("overflow_px") or 0) > 2 for item in samples)
    return {"samples": samples, "horizontal_overflow_on_scroll": overflow}


def _environment(page: Any, browser: UIUXBrowser, viewport: dict[str, int]) -> dict[str, Any]:
    touch = None
    dpr = None
    ua = None
    inner_w = None
    inner_h = None
    try:
        touch = page.evaluate("() => ('ontouchstart' in window) || ((navigator.maxTouchPoints || 0) > 0)")
        dpr = page.evaluate("() => window.devicePixelRatio")
        ua = page.evaluate("() => navigator.userAgent")
        inner_w = page.evaluate("() => window.innerWidth")
        inner_h = page.evaluate("() => window.innerHeight")
    except Exception:
        pass
    version = None
    try:
        version = getattr(browser._browser, "version", None)
    except Exception:
        version = None
    category = "mobile"
    if isinstance(ua, str) and "mobile" not in ua.lower() and "android" not in ua.lower() and "iphone" not in ua.lower():
        category = "desktop"
    return {
        "browser": "chromium",
        "browser_version": version,
        "device_profile": "mobile",
        "viewport": {"width": viewport["width"], "height": viewport["height"]},
        "inner_width": inner_w,
        "inner_height": inner_h,
        "touch_enabled": bool(touch) if touch is not None else None,
        "device_scale_factor": dpr,
        "user_agent_category": category,
        "is_mobile_emulation": True,
    }


def snapshot_from_session(payload: dict[str, Any]) -> MobileSnapshot:
    snapshot = payload.get("snapshot")
    if isinstance(snapshot, MobileSnapshot):
        return snapshot
    return MobileSnapshot.model_validate(snapshot or {})
