"""Normalize text and compare pages with hashing and Jaccard shingles."""

from __future__ import annotations

import hashlib
import re

from backend.analyzers.content.config import MAX_SIMILARITY_TEXT_LENGTH

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_text(value: str | None, limit: int = MAX_SIMILARITY_TEXT_LENGTH) -> str:
    cleaned = _WS.sub(" ", (value or "").lower()).strip()
    return cleaned[:limit]


def fingerprint(value: str | None) -> str:
    return hashlib.sha256(normalize_text(value).encode("utf-8")).hexdigest()


def tokens(value: str | None) -> list[str]:
    cleaned = _PUNCT.sub(" ", normalize_text(value))
    return [part for part in cleaned.split() if part]


def shingles(value: str | None, size: int = 3) -> set[tuple[str, ...]]:
    words = tokens(value)
    if len(words) < size:
        return {(word,) for word in words}
    return {tuple(words[index : index + size]) for index in range(len(words) - size + 1)}


def jaccard(left: set, right: set) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    union = len(left | right)
    if union <= 0:
        return 0.0
    return len(left & right) / union


def similarity(left: str | None, right: str | None) -> float:
    return jaccard(shingles(left), shingles(right))
