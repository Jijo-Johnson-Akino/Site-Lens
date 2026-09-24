"""Fill page records from already-fetched HTML using existing extract/classify helpers."""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from backend.analyzers.content.extract import extract_page
from backend.analyzers.content.page_type import classify_page
from backend.pages.config import PAGE_TYPE_LABELS
from backend.pages.models import PageRecord
from backend.services.url_identity import same_site

logger = logging.getLogger("sitebench.pages")


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def indexable_from_directives(robots_meta: str | None, x_robots: str | None) -> bool | None:
    tokens: set[str] = set()
    for raw in (robots_meta, x_robots):
        if not raw:
            continue
        for part in str(raw).replace(";", ",").split(","):
            token = part.strip().lower()
            if token:
                tokens.add(token)
    if not tokens:
        return None
    if "none" in tokens or "noindex" in tokens:
        return False
    return True


def apply_html(
    record: PageRecord,
    *,
    html_source: str,
    html_data: dict,
    page_url: str,
    x_robots_tag: str | None = None,
) -> PageRecord:
    record.title = _clean_text(html_data.get("title"))
    record.meta_description = _clean_text(html_data.get("meta_description"))
    h1s = html_data.get("h1s") or []
    first_h1 = next((item.get("text") for item in h1s if item.get("text")), None)
    record.h1 = _clean_text(first_h1)
    record.h1_count = html_data.get("h1_count")
    record.h2_count = html_data.get("h2_count")
    record.canonical_url = _clean_text(html_data.get("canonical"))
    robots = _clean_text(html_data.get("robots_meta"))
    header = _clean_text(x_robots_tag)
    if robots and header:
        record.robots_directive = f"{robots}; {header}"
    else:
        record.robots_directive = robots or header
    record.indexable = indexable_from_directives(robots, header)
    record.language = _clean_text(html_data.get("language"))
    record.image_count = html_data.get("image_count")
    paragraphs = html_data.get("paragraphs") or []
    lists = html_data.get("lists") or []
    record.paragraph_count = len(paragraphs)
    record.list_count = len(lists)
    headings = []
    for item in html_data.get("headings") or []:
        text = _clean_text(item.get("text") if isinstance(item, dict) else None)
        level = item.get("level") if isinstance(item, dict) else None
        if isinstance(level, int):
            headings.append({"level": level, "text": text})
        if len(headings) >= 20:
            break
    record.headings = headings
    json_ld = html_data.get("json_ld") or {}
    types = json_ld.get("types") if isinstance(json_ld, dict) else None
    record.schema_types = [str(item) for item in types][:20] if isinstance(types, list) else []

    internal = 0
    external = 0
    for link in html_data.get("links") or []:
        href = (link.get("href") or "").strip() if isinstance(link, dict) else ""
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(page_url, href)
        if same_site(absolute, page_url):
            internal += 1
        else:
            external += 1
    record.internal_link_count = internal
    record.external_link_count = external

    try:
        from backend.analyzers.cro.extraction import extract_signals

        record.cro_signals = extract_signals(html_source, page_url)
    except Exception:
        logger.info("page_cro_extract_failed url=%s", record.normalized_url)
        record.cro_signals = {}

    try:
        from backend.analyzers.trust.extraction import extract_signals as extract_trust_signals

        record.trust_signals = extract_trust_signals(html_source, page_url, parsed=html_data)
    except Exception:
        logger.info("page_trust_extract_failed url=%s", record.normalized_url)
        record.trust_signals = {}

    try:
        extracted = extract_page(html_source, page_url, parsed=html_data)
        classified = classify_page(extracted)
        record.word_count = extracted.word_count
        record.page_type = classified.type
        record.page_type_label = PAGE_TYPE_LABELS.get(classified.type, "Unknown")
        record.page_type_confidence = classified.confidence
        if not record.schema_types:
            record.schema_types = list(extracted.schema_types)[:20]
    except Exception:
        logger.info("page_classify_failed url=%s", record.normalized_url)
        record.page_type = "unknown"
        record.page_type_label = "Unknown"
        record.page_type_confidence = None
        if record.word_count is None:
            visible = html_data.get("visible_text") or ""
            words = [part for part in str(visible).split() if part]
            record.word_count = len(words) if words else 0
    return record
