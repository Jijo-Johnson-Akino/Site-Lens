"""Viewport, timeout, and scoring constants for the mobile analysis engine."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

PRIMARY_VIEWPORT: dict[str, int] = {"width": 390, "height": 844}
COMPACT_VIEWPORT: dict[str, int] = {"width": 375, "height": 812}
OPTIONAL_VIEWPORT: dict[str, int] = {"width": 412, "height": 915}

DEVICE_SCALE_FACTOR: float = 2.0
MOBILE_USER_AGENT: str = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Mobile Safari/537.36"
)

SCREENSHOT_KEYS: tuple[str, ...] = (
    "mobile_390",
    "mobile_390_full",
    "mobile_375",
    "mobile_375_full",
)

DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "layout": 0.20,
    "overflow": 0.20,
    "navigation": 0.10,
    "typography": 0.10,
    "touch": 0.15,
    "forms": 0.05,
    "images": 0.05,
    "tables": 0.05,
    "overlays": 0.05,
    "visibility": 0.05,
}

# Maps finding groups (15 categories) onto scoring buckets.
GROUP_TO_BUCKET: dict[str, str] = {
    "viewport": "layout",
    "layout": "layout",
    "spacing": "layout",
    "overflow": "overflow",
    "navigation": "navigation",
    "typography": "typography",
    "touch": "touch",
    "forms": "forms",
    "images": "images",
    "media": "images",
    "tables": "tables",
    "sticky": "overlays",
    "overlays": "overlays",
    "visibility": "visibility",
    "cta": "visibility",
}

DEFAULT_CHECK_WEIGHTS: dict[str, int] = {
    "MOBILE-VIEW-001": 10,
    "MOBILE-VIEW-002": 6,
    "MOBILE-VIEW-003": 6,
    "MOBILE-LAYOUT-001": 12,
    "MOBILE-LAYOUT-002": 6,
    "MOBILE-LAYOUT-003": 6,
    "MOBILE-OVERFLOW-001": 16,
    "MOBILE-OVERFLOW-002": 8,
    "MOBILE-NAV-001": 10,
    "MOBILE-NAV-002": 6,
    "MOBILE-NAV-003": 6,
    "MOBILE-NAV-004": 4,
    "MOBILE-TYPE-001": 6,
    "MOBILE-TYPE-002": 6,
    "MOBILE-TYPE-003": 6,
    "MOBILE-TOUCH-001": 10,
    "MOBILE-TOUCH-002": 8,
    "MOBILE-TOUCH-003": 5,
    "MOBILE-FORM-001": 6,
    "MOBILE-FORM-002": 5,
    "MOBILE-FORM-003": 2,
    "MOBILE-IMG-001": 6,
    "MOBILE-IMG-002": 4,
    "MOBILE-IMG-003": 3,
    "MOBILE-TABLE-001": 8,
    "MOBILE-TABLE-002": 4,
    "MOBILE-MEDIA-001": 4,
    "MOBILE-FIXED-001": 5,
    "MOBILE-OVERLAY-001": 6,
    "MOBILE-CONTENT-001": 6,
    "MOBILE-CONTENT-002": 4,
    "MOBILE-CTA-001": 7,
    "MOBILE-CTA-002": 4,
    "MOBILE-SPACE-001": 3,
    "MOBILE-SPACE-002": 2,
}

CATEGORY_LABELS: dict[str, str] = {
    "viewport": "Viewport",
    "layout": "Responsive Layout",
    "overflow": "Horizontal Overflow",
    "navigation": "Mobile Navigation",
    "typography": "Typography",
    "touch": "Touch Targets",
    "forms": "Forms",
    "images": "Images",
    "tables": "Tables",
    "media": "Media",
    "sticky": "Sticky/Fixed Elements",
    "overlays": "Overlays",
    "visibility": "Content Visibility",
    "cta": "CTA Visibility",
    "spacing": "Mobile Spacing",
}

LIMITATIONS: tuple[str, ...] = (
    "This analysis uses Chromium with a mobile viewport, touch enabled, and a mobile user agent. Chromium's is_mobile flag is not used because it can expand the layout viewport and hide overflow.",
    "The touch-target baseline is a configurable measurement (approximately 44×44 CSS pixels), not a legal requirement.",
    "Menu interaction is attempted only when a control appears non-destructive. Forms are never submitted.",
    "Horizontal overflow uses a 2px tolerance to reduce rounding noise from browser layout.",
    "These descriptions refer only to the automated mobile scan, not mobile-friendliness certification.",
    "Performance vitals such as LCP, CLS, and INP are reported by the Performance analyzer, not this mobile layout scan.",
)


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


OVERFLOW_TOLERANCE_PX: int = _int_env("SITEBENCH_MOBILE_OVERFLOW_TOLERANCE_PX", 2)
MIN_FONT_WARN_PX: float = _float_env("SITEBENCH_MOBILE_MIN_FONT_WARN_PX", 12.0)
MIN_FONT_HIGH_PX: float = _float_env("SITEBENCH_MOBILE_MIN_FONT_HIGH_PX", 10.0)
TOUCH_BASELINE_PX: int = _int_env("SITEBENCH_MOBILE_TOUCH_BASELINE_PX", 44)
TOUCH_SMALL_PX: int = _int_env("SITEBENCH_MOBILE_TOUCH_SMALL_PX", 32)
TOUCH_GAP_PX: int = _int_env("SITEBENCH_MOBILE_TOUCH_GAP_PX", 8)
EDGE_PADDING_PX: int = _int_env("SITEBENCH_MOBILE_EDGE_PADDING_PX", 8)
OVERLAY_COVERAGE: float = _float_env("SITEBENCH_MOBILE_OVERLAY_COVERAGE", 0.40)
FIXED_COVERAGE: float = _float_env("SITEBENCH_MOBILE_FIXED_COVERAGE", 0.30)
SCROLL_STEPS: int = _int_env("SITEBENCH_MOBILE_SCROLL_STEPS", 3)
MAX_MEASURE_NODES: int = _int_env("SITEBENCH_MOBILE_MAX_MEASURE_NODES", 500)


@dataclass(frozen=True)
class MobileScoringConfig:
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    check_weights: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CHECK_WEIGHTS))
    overflow_tolerance_px: int = OVERFLOW_TOLERANCE_PX
    min_font_warn_px: float = MIN_FONT_WARN_PX
    min_font_high_px: float = MIN_FONT_HIGH_PX
    touch_baseline_px: int = TOUCH_BASELINE_PX
    touch_small_px: int = TOUCH_SMALL_PX
    touch_gap_px: int = TOUCH_GAP_PX
    edge_padding_px: int = EDGE_PADDING_PX
    overlay_coverage: float = OVERLAY_COVERAGE
    fixed_coverage: float = FIXED_COVERAGE

    def weight_for(self, check_id: str) -> int:
        return self.check_weights.get(check_id, 1)

    def bucket_for(self, group: str) -> str:
        return GROUP_TO_BUCKET.get(group, group)


DEFAULT_SCORING = MobileScoringConfig()
