"""Strip selectors that could leak emails, tokens, or other sensitive fragments."""

from __future__ import annotations

import re

SENSITIVE = re.compile(
    r"(@|token|session|secret|password|passwd|email|auth|bearer|cookie)",
    re.I,
)
LONG_HEX = re.compile(r"[0-9a-f]{16,}", re.I)
UNSAFE_CHARS = re.compile(r"[^\w.#\[\]= \-]", re.I)


def sanitize_selector(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = " ".join(str(value).split())[:80]
    if not trimmed:
        return None
    if SENSITIVE.search(trimmed) or LONG_HEX.search(trimmed):
        tag = re.split(r"[.#\[]", trimmed, maxsplit=1)[0]
        return tag or "element"
    if UNSAFE_CHARS.search(trimmed.replace(">", "")):
        tag = re.split(r"[.#\[]", trimmed, maxsplit=1)[0]
        return tag or "element"
    return trimmed


def sanitize_text(value: str | None, limit: int = 120) -> str | None:
    if not value:
        return None
    cleaned = " ".join(str(value).split())
    if SENSITIVE.search(cleaned):
        return cleaned[:24] + "…"
    if len(cleaned) > limit:
        return cleaned[: limit - 1] + "…"
    return cleaned
