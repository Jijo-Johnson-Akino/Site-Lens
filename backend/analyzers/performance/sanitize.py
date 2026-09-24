"""Sanitize performance URLs and classify first vs third party."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend.analyzers.uiux.sanitizer import sanitize_text

SENSITIVE_QUERY = {
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "auth",
    "authorization",
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "session",
    "sid",
    "key",
    "cookie",
    "bearer",
}

MULTI_TLD = {"co.uk", "com.au", "co.jp", "com.br", "co.in", "com.mx", "co.nz", "com.sg"}
HEADER_ALLOW = {
    "content-type",
    "content-encoding",
    "cache-control",
    "etag",
    "last-modified",
    "expires",
    "age",
    "content-length",
    "vary",
}


def registrable_domain(host: str | None) -> str:
    if not host:
        return ""
    lowered = host.strip(".").lower()
    if lowered.startswith("["):
        return lowered
    try:
        return str(ipaddress.ip_address(lowered))
    except ValueError:
        pass
    parts = lowered.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_TLD:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return lowered


def first_party(resource_url: str, page_url: str) -> bool:
    resource_host = urlsplit(resource_url).hostname
    page_host = urlsplit(page_url).hostname
    if not resource_host or not page_host:
        return True
    return registrable_domain(resource_host) == registrable_domain(page_host)


def sanitize_url(url: str | None, limit: int = 180) -> str:
    if not url:
        return ""
    parsed = urlsplit(url)
    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in SENSITIVE_QUERY or re.search(r"(token|secret|auth|key|session)", key, re.I):
            continue
        query_pairs.append((key, value))
    cleaned = urlunsplit((parsed.scheme, parsed.netloc, parsed.path[:160], urlencode(query_pairs)[:80], ""))
    return sanitize_text(cleaned, limit) or cleaned[:limit]


def pick_headers(headers: dict | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in (headers or {}).items():
        lowered = str(key).lower()
        if lowered in HEADER_ALLOW:
            out[lowered] = str(value)[:160]
    return out
