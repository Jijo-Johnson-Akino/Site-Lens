"""Explicit related-issue relationships. Different issue types are not merged."""

from __future__ import annotations

RELATED_KEYS: dict[str, tuple[str, ...]] = {
    "mobile.horizontal_overflow": ("mobile.image.overflow",),
    "mobile.image.overflow": ("mobile.horizontal_overflow",),
    "accessibility.form.label.missing": ("uiux.form.usability",),
    "uiux.form.usability": ("accessibility.form.label.missing",),
    "content.head.001": ("seo.head.001", "seo.head.002"),
    "cro.cta.primary.not_visible": ("cro.mobile.cta.not_visible",),
    "cro.mobile.cta.not_visible": ("cro.cta.primary.not_visible",),
}


def related_keys_for(issue_key: str) -> tuple[str, ...]:
    return RELATED_KEYS.get(issue_key, ())
