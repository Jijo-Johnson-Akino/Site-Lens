"""Shared URL identity for crawler, pages, and issues. Does not fetch."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

SKIP_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".bmp",
    ".tif",
    ".tiff",
    ".avif",
    ".mp4",
    ".webm",
    ".mov",
    ".avi",
    ".mkv",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".css",
    ".js",
    ".mjs",
    ".map",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".rar",
    ".7z",
    ".exe",
    ".dmg",
    ".iso",
    ".bin",
    ".apk",
    ".xml",
    ".json",
    ".csv",
}

SKIP_SCHEMES = {"mailto", "tel", "javascript", "data", "blob", "file", "ftp"}


def normalize_page_url(url: str | None, fallback: str | None = None) -> str:
    """Normalize a page URL for identity.

    - lowercase hostname
    - drop fragments
    - empty path becomes ``/``
    - trailing slash is stripped except for the site root
    - query string is kept
    - scheme is lowercased; missing scheme defaults to https
    """
    raw = (url or "").strip() or (fallback or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = f"https://{raw}"
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return raw.split("#", 1)[0].rstrip()
    scheme = (parsed.scheme or "https").lower()
    if scheme not in {"http", "https"}:
        scheme = "https"
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return raw.split("#", 1)[0]
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = host
    if port and port not in (80, 443):
        netloc = f"{host}:{port}"
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def hostname_of(url: str | None) -> str:
    if not url:
        return ""
    try:
        return (urlsplit(url if "://" in url else f"https://{url}").hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def same_site(url: str | None, seed_url: str | None) -> bool:
    left = hostname_of(url)
    right = hostname_of(seed_url)
    return bool(left) and left == right


def url_path(url: str | None) -> str:
    """Return the URL path only. This is not crawl depth."""
    normalized = normalize_page_url(url)
    if not normalized:
        return "/"
    try:
        path = urlsplit(normalized).path or "/"
    except ValueError:
        return "/"
    return path or "/"


def url_path_depth(url: str | None) -> int:
    """Count path segments. Independent from crawler discovery depth."""
    path = url_path(url)
    if path == "/":
        return 0
    return len([segment for segment in path.split("/") if segment])


def is_skippable_resource(url: str | None) -> bool:
    if not url:
        return True
    raw = url.strip()
    lowered = raw.lower()
    if any(lowered.startswith(f"{scheme}:") for scheme in SKIP_SCHEMES):
        return True
    try:
        parsed = urlsplit(raw if "://" in raw else f"https://{raw}")
    except ValueError:
        return True
    scheme = (parsed.scheme or "").lower()
    if scheme in SKIP_SCHEMES:
        return True
    path = (parsed.path or "").lower()
    if path.endswith("/"):
        path = path[:-1]
    for ext in SKIP_EXTENSIONS:
        if path.endswith(ext):
            return True
    return False
