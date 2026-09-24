"""Extract visible/main content from already-fetched HTML. No extra HTTP."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, NavigableString
from bs4.element import Tag

from backend.analyzers.content.config import DEFAULT_SCORING, ContentScoringConfig
from backend.analyzers.content.similarity import normalize_text
from backend.analyzers.uiux.sanitizer import sanitize_text
from backend.parser.html_parser import SKIP_TEXT_TAGS, _is_hidden, parse_html

HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
BOILER_TAGS = {"nav", "footer", "aside"}
BOILER_HINT = re.compile(r"(cookie|consent|gdpr|onetrust|newsletter-popup|banner)", re.I)
CTA_RE = re.compile(
    r"\b(get started|contact us|book a demo|buy now|sign up|learn more|request quote|subscribe|start free|try free|shop now|download|register|book now|talk to sales)\b",
    re.I,
)
FAQ_RE = re.compile(r"\b(faq|faqs|frequently asked questions)\b", re.I)
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?", re.UNICODE)


def word_count(text: str | None) -> int:
    return len(WORD_RE.findall(text or ""))


def _classes_id(tag: Tag) -> str:
    classes = " ".join(tag.get("class") or [])
    ident = tag.get("id") or ""
    role = tag.get("role") or ""
    return f"{classes} {ident} {role}".lower()


def _is_boilerplate_tag(tag: Tag) -> bool:
    name = (tag.name or "").lower()
    if name in BOILER_TAGS:
        return True
    if name == "header":
        return True
    blob = _classes_id(tag)
    if BOILER_HINT.search(blob):
        return True
    if re.search(r"\b(nav|menu|footer|cookie|consent)\b", blob):
        return True
    return False


def _skip_node(node: NavigableString) -> bool:
    ancestor = node.parent
    while isinstance(ancestor, Tag):
        name = (ancestor.name or "").lower()
        if name in SKIP_TEXT_TAGS or name == "svg":
            return True
        if _is_hidden(ancestor):
            return True
        aria_hidden = ancestor.get("aria-hidden")
        if aria_hidden is True or str(aria_hidden).lower() == "true":
            return True
        ancestor = ancestor.parent
    return False


def _collect_text(root: Tag | BeautifulSoup, *, skip_boilerplate: bool, limit: int) -> str:
    parts: list[str] = []
    length = 0
    for node in root.descendants:
        if not isinstance(node, NavigableString):
            continue
        if _skip_node(node):
            continue
        if skip_boilerplate:
            ancestor = node.parent
            boiler = False
            while isinstance(ancestor, Tag):
                if _is_boilerplate_tag(ancestor):
                    boiler = True
                    break
                ancestor = ancestor.parent
            if boiler:
                continue
        text = str(node).strip()
        if not text:
            continue
        parts.append(text)
        length += len(text)
        if length >= limit:
            break
    return " ".join(parts)[:limit]


def _region_text(soup: BeautifulSoup, names: tuple[str, ...], limit: int) -> str:
    chunks: list[str] = []
    for name in names:
        for tag in soup.find_all(name):
            if not isinstance(tag, Tag):
                continue
            chunks.append(_collect_text(tag, skip_boilerplate=False, limit=limit))
    return " ".join(part for part in chunks if part)[:limit]


@dataclass
class ExtractedPage:
    url: str
    title: str | None
    language: str | None
    truncated: bool
    visible_text: str
    main_text: str
    boilerplate_text: str
    word_count: int
    main_word_count: int
    character_count: int
    paragraphs: list[str]
    headings: list[dict[str, Any]]
    lists: list[dict[str, Any]]
    table_count: int
    section_count: int
    buttons: list[str]
    links: list[dict[str, Any]]
    internal_content_links: int
    author_candidates: list[str]
    dates: list[str]
    cta_labels: list[str]
    faq_detected: bool
    main_detected: bool
    has_form: bool
    image_count: int
    parsed: dict
    schema_types: list[str]


def extract_page(html_source: str, url: str, *, config: ContentScoringConfig = DEFAULT_SCORING, parsed: dict | None = None) -> ExtractedPage:
    source = html_source or ""
    truncated = False
    if len(source) > config.max_content_chars * 4:
        source = source[: config.max_content_chars * 4]
        truncated = True
    soup = BeautifulSoup(source, "html.parser")
    html_data = parsed if parsed is not None else parse_html(source)

    main_root = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
    if not isinstance(main_root, Tag):
        for ident in ("main", "content", "primary", "article"):
            found = soup.find(id=ident) or soup.find(class_=re.compile(rf"\b{ident}\b", re.I))
            if isinstance(found, Tag) and found.name not in BOILER_TAGS:
                main_root = found
                break

    visible = _collect_text(soup, skip_boilerplate=False, limit=config.max_content_chars)
    if len(visible) >= config.max_content_chars:
        truncated = True
    boiler = _region_text(soup, ("nav", "footer", "header", "aside"), config.max_content_chars)
    cookie_bits = []
    for tag in soup.find_all(True):
        if isinstance(tag, Tag) and BOILER_HINT.search(_classes_id(tag)):
            cookie_bits.append(_collect_text(tag, skip_boilerplate=False, limit=2000))
    boiler = (boiler + " " + " ".join(cookie_bits)).strip()[: config.max_content_chars]

    if isinstance(main_root, Tag):
        main_text = _collect_text(main_root, skip_boilerplate=True, limit=config.max_content_chars)
        main_detected = True
    else:
        main_text = _collect_text(soup.body if soup.body else soup, skip_boilerplate=True, limit=config.max_content_chars)
        main_detected = False
    if not (main_text or "").strip():
        main_text = visible

    paragraphs = []
    for tag in soup.find_all("p"):
        if not isinstance(tag, Tag):
            continue
        if tag.find_parent(["nav", "footer", "header"]):
            continue
        parent = tag.parent
        boiler_parent = False
        while isinstance(parent, Tag):
            if _is_boilerplate_tag(parent):
                boiler_parent = True
                break
            parent = parent.parent
        if boiler_parent:
            continue
        text = tag.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)
        if len(paragraphs) >= config.max_paragraphs:
            truncated = True
            break

    headings = []
    for heading in soup.find_all(HEADING_TAGS):
        if not isinstance(heading, Tag):
            continue
        following: list[str] = []
        for sib in heading.next_siblings:
            if isinstance(sib, Tag) and sib.name in HEADING_TAGS:
                break
            if isinstance(sib, NavigableString):
                snippet = str(sib).strip()
                if snippet:
                    following.append(snippet)
                continue
            if isinstance(sib, Tag) and sib.name not in SKIP_TEXT_TAGS:
                snippet = sib.get_text(" ", strip=True)
                if snippet:
                    following.append(snippet)
        text = heading.get_text(" ", strip=True)
        headings.append(
            {
                "level": int(heading.name[1]),
                "text": text,
                "following_text": " ".join(following)[:400],
                "following_words": word_count(" ".join(following)),
                "empty": not text,
            }
        )
        if len(headings) >= config.max_headings:
            truncated = True
            break

    lists = []
    for listing in soup.find_all(["ul", "ol"]):
        if not isinstance(listing, Tag) or listing.find_parent(["nav", "header", "footer"]):
            continue
        items = [item.get_text(" ", strip=True) for item in listing.find_all("li", recursive=False)]
        items = [item for item in items if item]
        if items:
            lists.append({"type": listing.name, "count": len(items)})

    buttons = []
    for tag in soup.find_all(["button", "a", "input"]):
        if not isinstance(tag, Tag):
            continue
        if tag.name == "input" and (tag.get("type") or "").lower() not in {"submit", "button"}:
            continue
        label = tag.get_text(" ", strip=True) or (tag.get("value") if isinstance(tag.get("value"), str) else "") or ""
        label = " ".join(str(label).split())
        if label and len(label) <= 80:
            buttons.append(label)
        if len(buttons) >= 40:
            break

    cta_labels = []
    seen_cta: set[str] = set()
    for label in buttons:
        if CTA_RE.search(label):
            key = label.lower()
            if key not in seen_cta:
                seen_cta.add(key)
                cta_labels.append(label)

    page_host = (urlsplit(url).hostname or "").lower()
    content_links = []
    for anchor in soup.find_all("a"):
        if not isinstance(anchor, Tag):
            continue
        if anchor.find_parent(["nav", "header", "footer"]):
            continue
        href = anchor.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        href = href.strip()
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(url, href)
        host = (urlsplit(absolute).hostname or "").lower()
        internal = bool(page_host) and host == page_host
        text = anchor.get_text(" ", strip=True)
        content_links.append({"href": absolute[:180], "text": text[:80], "internal": internal})

    internal_content_links = sum(1 for item in content_links if item["internal"])

    authors = []
    for key in ("byline", "author_rel"):
        value = html_data.get(key)
        if value:
            authors.append(str(value))
    for entity in (html_data.get("json_ld") or {}).get("entities") or []:
        if entity.get("author"):
            authors.append(entity["author"])
        if "Person" in (entity.get("types") or []) and entity.get("name"):
            authors.append(entity["name"])
    meta_author = None
    for meta in soup.find_all("meta"):
        if not isinstance(meta, Tag):
            continue
        name = (meta.get("name") or meta.get("property") or "")
        if str(name).lower() in {"author", "article:author", "og:article:author"}:
            content = meta.get("content")
            if isinstance(content, str) and content.strip():
                meta_author = content.strip()
    if meta_author:
        authors.append(meta_author)
    unique_authors = []
    seen_auth: set[str] = set()
    for name in authors:
        key = name.strip().lower()
        if key and key not in seen_auth:
            seen_auth.add(key)
            unique_authors.append(name.strip())

    dates = list(html_data.get("time_values") or [])
    for entity in (html_data.get("json_ld") or {}).get("entities") or []:
        if entity.get("datePublished"):
            dates.append(entity["datePublished"])
        if entity.get("dateModified"):
            dates.append(entity["dateModified"])
    for meta in soup.find_all("meta"):
        if not isinstance(meta, Tag):
            continue
        name = str(meta.get("name") or meta.get("property") or "").lower()
        if name in {"article:published_time", "article:modified_time", "og:updated_time", "date", "pubdate"}:
            content = meta.get("content")
            if isinstance(content, str) and content.strip():
                dates.append(content.strip())
    unique_dates = []
    seen_dates: set[str] = set()
    for value in dates:
        key = value.strip()
        if key and key not in seen_dates:
            seen_dates.add(key)
            unique_dates.append(key)

    visible_words = min(word_count(visible), config.max_words)
    main_words = min(word_count(main_text), config.max_words)
    if word_count(visible) > config.max_words or word_count(main_text) > config.max_words:
        truncated = True

    h2 = sum(1 for item in headings if item["level"] == 2)
    sections = max(h2, len(soup.find_all("section")))
    faq = bool(FAQ_RE.search(visible) or "FAQPage" in ((html_data.get("json_ld") or {}).get("types") or []))

    return ExtractedPage(
        url=url,
        title=html_data.get("title"),
        language=html_data.get("language"),
        truncated=truncated,
        visible_text=visible,
        main_text=main_text[: config.max_similarity_chars],
        boilerplate_text=boiler[: config.max_similarity_chars],
        word_count=visible_words,
        main_word_count=main_words,
        character_count=min(len(visible), config.max_content_chars),
        paragraphs=paragraphs,
        headings=headings,
        lists=lists,
        table_count=int(html_data.get("table_count") or len(soup.find_all("table"))),
        section_count=sections,
        buttons=buttons[:20],
        links=content_links[:40],
        internal_content_links=internal_content_links,
        author_candidates=unique_authors[:8],
        dates=unique_dates[:8],
        cta_labels=cta_labels[:8],
        faq_detected=faq,
        main_detected=main_detected and bool(main_text.strip()),
        has_form=int(html_data.get("form_count") or 0) > 0,
        image_count=int(html_data.get("image_count") or 0),
        parsed=html_data,
        schema_types=list((html_data.get("json_ld") or {}).get("types") or []),
    )


def snippet(value: str | None, limit: int = 140) -> str | None:
    return sanitize_text(normalize_text(value), limit)


def repeated_blocks(paragraphs: list[str], headings: list[dict], min_chars: int = 50) -> tuple[int, float, list[str]]:
    counts: dict[str, int] = {}
    samples: list[str] = []
    items = [item for item in paragraphs if len(item) >= min_chars]
    items.extend(heading["text"] for heading in headings if len(heading.get("text") or "") >= min_chars)
    total = len(items)
    if total <= 1:
        return 0, 0.0, []
    for item in items:
        key = normalize_text(item)
        counts[key] = counts.get(key, 0) + 1
    repeated = 0
    for key, count in counts.items():
        if count >= 2:
            repeated += count
            if len(samples) < 3:
                samples.append(snippet(key) or key[:80])
    ratio = repeated / total if total else 0.0
    return repeated, ratio, samples
