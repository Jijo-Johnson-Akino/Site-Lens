"""Safe, bounded mobile menu interaction. Never submits forms or triggers account/payment actions."""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.analyzers.mobile.measurements import MENU_AFTER_JS

logger = logging.getLogger("sitebench.mobile")

UNSAFE = re.compile(
    r"\b(delete|remove account|purchase|buy now|pay now|checkout|logout|log out|sign out|unsubscribe|send message)\b",
    re.I,
)


def probe_menu(page: Any, snapshot_nav: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "menu_tested": False,
        "menu_opened": False,
        "menu_closed": False,
        "menu_visible_after_open": None,
        "menu_overflow_after_open": None,
        "reason": None,
    }
    selector = snapshot_nav.get("menu_button")
    if not selector:
        result["reason"] = "no_menu_button"
        return result
    if not snapshot_nav.get("menu_safe", True):
        result["reason"] = "unsafe_control"
        return result
    name = str(snapshot_nav.get("menu_name") or "")
    if UNSAFE.search(name):
        result["reason"] = "unsafe_control"
        return result
    try:
        locator = page.locator(selector).first
        if locator.count() == 0:
            result["reason"] = "selector_not_found"
            return result
        result["menu_tested"] = True
        locator.click(timeout=1500)
        page.wait_for_timeout(350)
        after = page.evaluate(MENU_AFTER_JS) or {}
        result["menu_opened"] = bool(after.get("opened"))
        result["menu_visible_after_open"] = after.get("panel_visible")
        result["menu_overflow_after_open"] = after.get("overflow")
        close_sel = after.get("close_selector")
        if result["menu_opened"] and after.get("close_safe") and close_sel and not UNSAFE.search(str(close_sel)):
            try:
                page.locator(str(close_sel)).first.click(timeout=1000)
                page.wait_for_timeout(200)
                closed = page.evaluate(MENU_AFTER_JS) or {}
                result["menu_closed"] = not bool(closed.get("opened"))
            except Exception:
                result["menu_closed"] = False
        return result
    except Exception:
        logger.info("mobile_menu_interaction_failed")
        result["menu_tested"] = True
        result["reason"] = "interaction_failed"
        return result
