"""Stable page identifiers scoped to a scan."""

from __future__ import annotations

import hashlib


def make_page_id(scan_id: str, normalized_url: str) -> str:
    digest = hashlib.sha256(f"{scan_id}|{normalized_url}".encode("utf-8")).hexdigest()[:24]
    return f"page_{digest}"


def make_link_id(scan_id: str, source_id: str, destination_id: str, anchor: str | None) -> str:
    key = f"{scan_id}|{source_id}|{destination_id}|{(anchor or '').strip().lower()}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"link_{digest}"
