"""Safe URL discovery from already-fetched HTML and sitemap bodies. No extra HTTP."""

from __future__ import annotations

from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from backend.pages.config import MAX_SITEMAP_URLS
from backend.parser.html_parser import parse_html
from backend.services.url_identity import is_skippable_resource, normalize_page_url, same_site


def hrefs_from_html(html_data: dict) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for link in html_data.get("links") or []:
        if not isinstance(link, dict):
            continue
        href = (link.get("href") or "").strip()
        if not href or href in seen:
            continue
        seen.add(href)
        found.append(href)
    return found


def canonical_from_html(html_data: dict) -> str | None:
    value = html_data.get("canonical")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def parse_sitemap_locs(body: str | None, *, limit: int = MAX_SITEMAP_URLS) -> list[str]:
    if not body or not body.strip():
        return []
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []
    locs: list[str] = []
    seen: set[str] = set()
    for node in root.iter():
        if not str(node.tag).lower().endswith("loc"):
            continue
        text = (node.text or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        locs.append(text)
        if len(locs) >= limit:
            break
    return locs


def resolve_internal_candidates(
    hrefs: list[str],
    *,
    base_url: str,
    seed_url: str,
) -> tuple[list[str], list[str]]:
    internal: list[str] = []
    external: list[str] = []
    seen_internal: set[str] = set()
    seen_external: set[str] = set()
    for href in hrefs:
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue
        absolute = urljoin(base_url, href)
        if is_skippable_resource(absolute):
            continue
        if not same_site(absolute, seed_url):
            key = normalize_page_url(absolute) or absolute
            if key not in seen_external:
                seen_external.add(key)
                external.append(absolute)
            continue
        key = normalize_page_url(absolute)
        if not key or key in seen_internal:
            continue
        seen_internal.add(key)
        internal.append(absolute)
    return internal, external


def discover_from_page(
    html_data: dict,
    *,
    base_url: str,
    seed_url: str,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Return (internal url, method) pairs plus unique external hrefs."""
    candidates: list[tuple[str, str]] = []
    hrefs = hrefs_from_html(html_data)
    internal, external = resolve_internal_candidates(hrefs, base_url=base_url, seed_url=seed_url)
    for url in internal:
        candidates.append((url, "internal_link"))
    canonical = canonical_from_html(html_data)
    if canonical:
        canonical_internal, _ = resolve_internal_candidates(
            [canonical],
            base_url=base_url,
            seed_url=seed_url,
        )
        for url in canonical_internal:
            if normalize_page_url(url) != normalize_page_url(base_url):
                candidates.append((url, "canonical"))
    return candidates, external


def extract_internal_link_edges(
    html_data: dict,
    *,
    base_url: str,
    seed_url: str,
) -> list[dict[str, str | None]]:
    """Per-anchor internal page edges. Does not fetch and does not crawl."""
    source = normalize_page_url(base_url)
    if not source:
        return []
    edges: list[dict[str, str | None]] = []
    for link in html_data.get("links") or []:
        if not isinstance(link, dict):
            continue
        href = (link.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        lowered = href.lower()
        if lowered.startswith(("javascript:", "mailto:", "tel:", "data:", "blob:")):
            continue
        absolute = urljoin(base_url, href)
        if is_skippable_resource(absolute):
            continue
        if not same_site(absolute, seed_url):
            continue
        destination = normalize_page_url(absolute)
        if not destination or destination == source:
            continue
        text = (link.get("text") or "").strip() or None
        rel = (link.get("rel") or "").strip() or None
        edges.append(
            {
                "source_url": source,
                "destination_url": destination,
                "raw_destination": absolute.split("#", 1)[0],
                "anchor_text": text,
                "rel": rel,
            }
        )
    return edges


def html_data_from_source(html: str) -> dict:
    return parse_html(html)
