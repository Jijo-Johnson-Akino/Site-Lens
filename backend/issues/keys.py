"""Stable issue keys derived from existing analyzer check IDs.

Keys are deterministic and must remain stable across scans. They are not UUIDs.
Unknown check IDs fall back to ``{source}.{slug}`` from the check ID.
"""

from __future__ import annotations

import re

from backend.issues.config import SOURCE_VALUES

# Explicit mappings for well-known checks (including the Phase 12 spec examples).
CHECK_ISSUE_KEYS: dict[str, str] = {
    "SEO-TITLE-001": "seo.title.missing",
    "SEO-META-001": "seo.meta_description.missing",
    "SEO-CAN-001": "seo.canonical.missing",
    "AEO-ENTITY-002": "aeo.entity.organization.missing",
    "UX-NAV-001": "uiux.navigation.missing",
    "UX-FORM-002": "uiux.form.usability",
    "A11Y-FORM-001": "accessibility.form.label.missing",
    "A11Y-CTRL-001": "accessibility.button.name.missing",
    "PERF-JS-002": "performance.javascript.large_payload",
    "PERF-IMG-001": "performance.image.large",
    "CONTENT-DEPTH-001": "content.thin_page",
    "SCHEMA-SYNTAX-001": "structured_data.invalid_jsonld",
    "SCHEMA-ID-002": "structured_data.conflicting_entity",
    "MOBILE-OVERFLOW-001": "mobile.horizontal_overflow",
    "MOBILE-TOUCH-001": "mobile.touch_target.small",
    "MOBILE-IMG-002": "mobile.image.overflow",
}

CHECK_ID_PREFIX = {
    "SEO": "seo",
    "AEO": "aeo",
    "UX": "uiux",
    "A11Y": "accessibility",
    "PERF": "performance",
    "CONTENT": "content",
    "SCHEMA": "structured_data",
    "MOBILE": "mobile",
    "CRO": "cro",
}

_SPLIT = re.compile(r"[-_\s]+")
_SAFE = re.compile(r"[^a-z0-9.]+")


def issue_key_for(source: str, check_id: str | None) -> str:
    """Return a stable issue key for an analyzer check."""
    raw_id = (check_id or "").strip()
    lowered = raw_id.lower()
    source_norm = source if source in SOURCE_VALUES else "unknown"
    if lowered.startswith("cro.") or (source_norm != "unknown" and lowered.startswith(f"{source_norm}.")):
        return lowered
    raw_upper = raw_id.upper()
    if raw_upper in CHECK_ISSUE_KEYS:
        return CHECK_ISSUE_KEYS[raw_upper]
    if not raw_id:
        return f"{source_norm}.unknown"
    parts = [part.lower() for part in _SPLIT.split(raw_upper) if part]
    if parts:
        prefix = parts[0].upper()
        if prefix in CHECK_ID_PREFIX:
            parts = parts[1:]
    slug = ".".join(parts) if parts else "unknown"
    slug = _SAFE.sub("", slug).strip(".") or "unknown"
    return f"{source_norm}.{slug}"
