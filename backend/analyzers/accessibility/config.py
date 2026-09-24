"""Configurable accessibility scoring and axe timeouts."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
AXE_BUNDLE = VENDOR_DIR / "axe.min.js"
AXE_TAGS = ("wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa")
AXE_TIMEOUT_MS = int(os.getenv("SITEBENCH_A11Y_AXE_TIMEOUT_MS", "25000"))
KEYBOARD_TAB_LIMIT = int(os.getenv("SITEBENCH_A11Y_TAB_LIMIT", "12"))

DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "document": 0.05,
    "landmarks": 0.10,
    "headings": 0.08,
    "images": 0.10,
    "links": 0.08,
    "controls": 0.10,
    "forms": 0.12,
    "aria": 0.12,
    "keyboard": 0.10,
    "tables": 0.05,
    "media": 0.03,
    "contrast": 0.05,
    "other": 0.02,
}

DEFAULT_CHECK_WEIGHTS: dict[str, int] = {
    "A11Y-DOC-001": 10,
    "A11Y-DOC-002": 8,
    "A11Y-DOC-003": 6,
    "A11Y-DOC-004": 2,
    "A11Y-LAND-001": 10,
    "A11Y-LAND-002": 7,
    "A11Y-LAND-003": 6,
    "A11Y-LAND-004": 4,
    "A11Y-HEAD-001": 7,
    "A11Y-HEAD-002": 6,
    "A11Y-HEAD-003": 4,
    "A11Y-HEAD-004": 3,
    "A11Y-IMG-001": 12,
    "A11Y-IMG-002": 4,
    "A11Y-IMG-003": 6,
    "A11Y-IMG-004": 6,
    "A11Y-LINK-001": 10,
    "A11Y-LINK-002": 3,
    "A11Y-CTRL-001": 12,
    "A11Y-FORM-001": 12,
    "A11Y-FORM-002": 4,
    "A11Y-FORM-003": 6,
    "A11Y-ARIA-001": 10,
    "A11Y-ARIA-002": 8,
    "A11Y-ARIA-003": 10,
    "A11Y-ID-001": 8,
    "A11Y-FOCUS-001": 6,
    "A11Y-FOCUS-002": 8,
    "A11Y-KEY-001": 8,
    "A11Y-TABLE-001": 7,
    "A11Y-TABLE-002": 2,
    "A11Y-IFRAME-001": 7,
    "A11Y-DIALOG-001": 6,
    "A11Y-MEDIA-001": 4,
    "A11Y-MEDIA-002": 4,
    "A11Y-CONTRAST-001": 10,
    "A11Y-VIEW-001": 4,
    "A11Y-LIVE-001": 3,
}

IMPACT_SEVERITY = {
    "critical": "critical",
    "serious": "high",
    "moderate": "medium",
    "minor": "low",
}

LIMITATIONS = [
    "Automated testing cannot detect every accessibility issue.",
    "Passing these checks does not guarantee WCAG or legal compliance.",
    "Manual keyboard and assistive technology testing may still be required.",
]


@dataclass(frozen=True)
class A11yScoringConfig:
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    check_weights: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CHECK_WEIGHTS))

    def weight_for(self, check_id: str) -> int:
        if check_id in self.check_weights:
            return self.check_weights[check_id]
        if check_id.startswith("A11Y-AXE-"):
            return 4
        return 1


DEFAULT_SCORING = A11yScoringConfig()
