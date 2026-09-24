"""Viewport, timeout, and scoring constants for the UI/UX engine."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from backend import config as app_config

VIEWPORTS: dict[str, dict[str, int]] = {
    "desktop": {
        "width": 1440,
        "height": 900,
    },
    "tablet": {
        "width": 768,
        "height": 1024,
    },
    "mobile": {
        "width": 390,
        "height": 844,
    },
}

OPTIONAL_VIEWPORTS: dict[str, dict[str, int]] = {
    "mobile_compact": {
        "width": 375,
        "height": 812,
    },
}

DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "responsive": 0.25,
    "layout": 0.20,
    "navigation": 0.15,
    "interactive": 0.10,
    "typography": 0.10,
    "content": 0.10,
    "forms": 0.05,
    "images": 0.05,
}

DEFAULT_VIEWPORT_WEIGHTS: dict[str, float] = {
    "desktop": 0.40,
    "mobile": 0.40,
    "tablet": 0.20,
    "mobile_compact": 0.0,
}

DEFAULT_CHECK_WEIGHTS: dict[str, int] = {
    "UX-RESP-001": 12,
    "UX-RESP-002": 10,
    "UX-RESP-003": 6,
    "UX-RESP-004": 8,
    "UX-NAV-001": 10,
    "UX-NAV-002": 8,
    "UX-NAV-003": 8,
    "UX-NAV-004": 4,
    "UX-CTA-001": 6,
    "UX-CTA-002": 6,
    "UX-CTA-003": 7,
    "UX-CTA-004": 5,
    "UX-TYPE-001": 6,
    "UX-TYPE-002": 6,
    "UX-TYPE-003": 7,
    "UX-CONTENT-001": 8,
    "UX-CONTENT-002": 3,
    "UX-CONTENT-003": 5,
    "UX-INTERACT-001": 4,
    "UX-INTERACT-002": 4,
    "UX-INTERACT-003": 3,
    "UX-INTERACT-004": 3,
    "UX-FORM-001": 2,
    "UX-FORM-002": 4,
    "UX-FORM-003": 5,
    "UX-IMG-001": 8,
    "UX-IMG-002": 5,
    "UX-IMG-003": 4,
    "UX-LAYOUT-001": 10,
    "UX-LAYOUT-002": 6,
    "UX-LAYOUT-003": 7,
}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


NAVIGATION_TIMEOUT_MS: int = _int_env("SITEBENCH_UIUX_NAV_TIMEOUT_MS", 20_000)
MAX_SCREENSHOT_HEIGHT: int = _int_env("SITEBENCH_UIUX_MAX_SCREENSHOT_HEIGHT", 8_000)
MAX_SCREENSHOTS: int = _int_env("SITEBENCH_UIUX_MAX_SCREENSHOTS", 3)
MAX_PAGES: int = _int_env("SITEBENCH_UIUX_MAX_PAGES", 1)
OVERFLOW_TOLERANCE_PX: int = _int_env("SITEBENCH_UIUX_OVERFLOW_TOLERANCE_PX", 8)
MIN_FONT_PX: float = _float_env("SITEBENCH_UIUX_MIN_FONT_PX", 11.0)
FIXED_WIDTH_RATIO: float = _float_env("SITEBENCH_UIUX_FIXED_WIDTH_RATIO", 1.25)
DISTORTION_RATIO: float = _float_env("SITEBENCH_UIUX_DISTORTION_RATIO", 0.40)
OVERLAY_COVERAGE: float = _float_env("SITEBENCH_UIUX_OVERLAY_COVERAGE", 0.55)
USER_AGENT: str = app_config.USER_AGENT


def all_known_viewports() -> dict[str, dict[str, int]]:
    merged = dict(VIEWPORTS)
    merged.update(OPTIONAL_VIEWPORTS)
    return merged


def enabled_viewports() -> dict[str, dict[str, int]]:
    raw = os.getenv("SITEBENCH_UIUX_VIEWPORTS", "desktop,tablet,mobile")
    names = [part.strip().lower() for part in raw.split(",") if part.strip()]
    known = all_known_viewports()
    selected: dict[str, dict[str, int]] = {}
    for name in names:
        if name in known and name not in selected:
            selected[name] = dict(known[name])
    if not selected:
        return {name: dict(size) for name, size in VIEWPORTS.items()}
    return selected


@dataclass(frozen=True)
class UIUXScoringConfig:
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    check_weights: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CHECK_WEIGHTS))
    viewport_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_VIEWPORT_WEIGHTS))
    overflow_tolerance_px: int = OVERFLOW_TOLERANCE_PX
    min_font_px: float = MIN_FONT_PX
    fixed_width_ratio: float = FIXED_WIDTH_RATIO
    distortion_ratio: float = DISTORTION_RATIO
    overlay_coverage: float = OVERLAY_COVERAGE

    def weight_for(self, check_id: str) -> int:
        return self.check_weights.get(check_id, 1)

    def viewport_weight(self, name: str) -> float:
        return float(self.viewport_weights.get(name, 0.0))


DEFAULT_SCORING = UIUXScoringConfig()
