from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString
from bs4.element import Tag

from backend.parser.structured_data import extract_json_ld

HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
SEMANTIC_TAGS = ("header", "nav", "main", "article", "section", "aside", "footer")
SKIP_TEXT_TAGS = {"script", "style", "noscript", "template"}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)


def _attr(tag: Tag | None, name: str) -> str | None:
    if tag is None:
        return None
    value = tag.get(name)
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _rel_values(tag: Tag) -> list[str]:
    rel = tag.get("rel") or []
    if isinstance(rel, str):
        return [part.lower() for part in rel.split()]
    return [str(item).lower() for item in rel]


def _meta_map(soup: BeautifulSoup) -> dict[str, str]:
    values: dict[str, str] = {}
    for meta in soup.find_all("meta"):
        if not isinstance(meta, Tag):
            continue
        key = _attr(meta, "name") or _attr(meta, "property") or _attr(meta, "http-equiv")
        content = _attr(meta, "content")
        if key and content and key.lower() not in values:
            values[key.lower()] = content
    return values


def _meta_named(soup: BeautifulSoup, name: str) -> tuple[bool, str | None]:
    target = name.lower()
    for meta in soup.find_all("meta"):
        if not isinstance(meta, Tag):
            continue
        key = _attr(meta, "name")
        if key and key.lower() == target:
            raw = meta.get("content")
            if not isinstance(raw, str):
                return True, None
            text = raw.strip()
            return True, text or None
    return False, None


def _is_hidden(tag: Tag) -> bool:
    style = (tag.get("style") or "")
    if isinstance(style, list):
        style = " ".join(str(part) for part in style)
    compact = str(style).lower().replace(" ", "")
    hidden_attr = tag.get("hidden") is not None
    return hidden_attr or "display:none" in compact or "visibility:hidden" in compact


def _visible_text(root: Tag | BeautifulSoup, limit: int = 8000) -> str:
    parts: list[str] = []
    length = 0
    for node in root.descendants:
        if not isinstance(node, NavigableString):
            continue
        ancestor = node.parent
        skip = False
        while isinstance(ancestor, Tag):
            if ancestor.name in SKIP_TEXT_TAGS or _is_hidden(ancestor):
                skip = True
                break
            ancestor = ancestor.parent
        if skip:
            continue
        text = str(node).strip()
        if not text:
            continue
        parts.append(text)
        length += len(text)
        if length >= limit:
            break
    return " ".join(parts)[:limit]


def _hidden_text(soup: BeautifulSoup, limit: int = 4000) -> str:
    parts: list[str] = []
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag) or not _is_hidden(tag):
            continue
        text = tag.get_text(" ", strip=True)
        if text:
            parts.append(text)
        if sum(len(part) for part in parts) >= limit:
            break
    return " ".join(parts)[:limit]


def _heading_blocks(soup: BeautifulSoup) -> list[dict]:
    blocks: list[dict] = []
    for heading in soup.find_all(HEADING_TAGS):
        if not isinstance(heading, Tag):
            continue
        texts: list[str] = []
        media = 0
        controls = 0
        for sib in heading.next_siblings:
            if isinstance(sib, NavigableString):
                snippet = str(sib).strip()
                if snippet:
                    texts.append(snippet)
                continue
            if not isinstance(sib, Tag):
                continue
            if sib.name in HEADING_TAGS:
                break
            if sib.name in SKIP_TEXT_TAGS:
                continue
            if sib.name in {"img", "svg", "picture", "video", "canvas"} or sib.find(["img", "svg", "picture", "video"]):
                media += 1
            if sib.name in {"button", "input"} or (sib.name == "a" and len(sib.get_text(" ", strip=True)) < 48):
                controls += 1
            snippet = sib.get_text(" ", strip=True)
            if snippet:
                texts.append(snippet)
        following = " ".join(texts)
        blocks.append(
            {
                "level": int(heading.name[1]),
                "text": heading.get_text(" ", strip=True),
                "following_text": following[:500],
                "following_length": len(following),
                "media_count": media,
                "control_count": controls,
            }
        )
    return blocks


def _header_identity(soup: BeautifulSoup) -> str | None:
    header = soup.find("header")
    scope = header if isinstance(header, Tag) else soup
    for image in scope.find_all("img"):
        if not isinstance(image, Tag):
            continue
        alt = _attr(image, "alt")
        if alt and len(alt) <= 80:
            return alt
    if isinstance(header, Tag):
        link = header.find("a")
        if isinstance(link, Tag):
            text = link.get_text(" ", strip=True)
            if text and len(text) <= 80:
                return text
    return None


def parse_html(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    html_tag = soup.find("html")
    title_tag = soup.find("title")
    metas = _meta_map(soup)

    canonical = None
    favicon = False
    stylesheet_count = 0
    for link in soup.find_all("link"):
        if not isinstance(link, Tag):
            continue
        rels = _rel_values(link)
        if "canonical" in rels and canonical is None:
            canonical = _attr(link, "href")
        if any(rel in {"icon", "shortcut icon", "apple-touch-icon"} for rel in rels):
            favicon = True
        if "stylesheet" in rels:
            stylesheet_count += 1

    h1s: list[dict] = []
    for heading in soup.find_all("h1"):
        text = heading.get_text(" ", strip=True)
        h1s.append({"text": text, "empty": not text})

    outline: list[int] = []
    headings: list[dict] = []
    for heading in soup.find_all(HEADING_TAGS):
        level = int(heading.name[1])
        outline.append(level)
        headings.append({"level": level, "text": heading.get_text(" ", strip=True)})

    images: list[dict] = []
    for image in soup.find_all("img"):
        if not isinstance(image, Tag):
            continue
        has_alt = image.has_attr("alt")
        alt = image.get("alt")
        alt_text = alt if isinstance(alt, str) else ""
        images.append(
            {
                "has_alt": has_alt,
                "alt": alt_text,
                "empty_alt": has_alt and alt_text.strip() == "",
                "loading": (_attr(image, "loading") or "").lower() or None,
                "has_title": bool(_attr(image, "title")),
            }
        )

    links: list[dict] = []
    for anchor in soup.find_all("a"):
        if not isinstance(anchor, Tag):
            continue
        href = anchor.get("href")
        href_text = href.strip() if isinstance(href, str) else ""
        links.append(
            {
                "href": href_text,
                "text": anchor.get_text(" ", strip=True),
                "has_href": anchor.has_attr("href"),
                "rel": " ".join(_rel_values(anchor)) or None,
            }
        )

    paragraphs = [tag.get_text(" ", strip=True) for tag in soup.find_all("p")]
    paragraphs = [text for text in paragraphs if text][:40]

    lists: list[dict] = []
    for listing in soup.find_all(["ul", "ol"]):
        if not isinstance(listing, Tag):
            continue
        if listing.find_parent(["nav", "header", "footer"]):
            continue
        items = [item.get_text(" ", strip=True) for item in listing.find_all("li", recursive=False)]
        items = [item for item in items if item]
        if items:
            lists.append({"type": listing.name, "count": len(items), "items": items[:8]})

    title = title_tag.get_text(" ", strip=True) if title_tag else None
    language = _attr(html_tag if isinstance(html_tag, Tag) else None, "lang")
    if language:
        language = language.split("-", 1)[0].lower()
    description_present, description = _meta_named(soup, "description")
    robots_present, robots_meta = _meta_named(soup, "robots")

    visible = _visible_text(soup)
    hidden = _hidden_text(soup)
    html_length = len(html)
    text_length = len(visible)
    text_nodes = [text for text in soup.stripped_strings if text]
    span_count = len(soup.find_all("span"))
    tag_count = len(soup.find_all(True))

    byline = None
    for tag in soup.find_all(True, class_=True):
        classes = " ".join(tag.get("class") or []).lower()
        if "byline" in classes or "author" in classes or "written-by" in classes:
            text = tag.get_text(" ", strip=True)
            if text and 2 < len(text) < 120:
                byline = text
                break
    author_rel = None
    for anchor in soup.find_all("a"):
        if not isinstance(anchor, Tag):
            continue
        if "author" in _rel_values(anchor):
            author_rel = anchor.get_text(" ", strip=True) or None
            break

    time_values = []
    for time_tag in soup.find_all("time"):
        if not isinstance(time_tag, Tag):
            continue
        value = _attr(time_tag, "datetime") or time_tag.get_text(" ", strip=True)
        if value:
            time_values.append(value)

    emails = EMAIL_RE.findall(visible)
    tel_links = [item["href"] for item in links if item["href"].lower().startswith("tel:")]
    mailto_links = [item["href"] for item in links if item["href"].lower().startswith("mailto:")]

    json_ld = extract_json_ld(soup)
    semantic = {name: len(soup.find_all(name)) for name in SEMANTIC_TAGS}
    has_main_role = bool(soup.find(attrs={"role": "main"})) or bool(soup.find(id=["main", "content", "primary"]))

    return {
        "title": title or None,
        "title_present": title_tag is not None,
        "meta_description_present": description_present,
        "meta_description": description,
        "canonical": canonical,
        "language": language,
        "h1_count": len(h1s),
        "h1s": h1s,
        "h2_count": len(soup.find_all("h2")),
        "h3_count": len(soup.find_all("h3")),
        "heading_outline": outline,
        "headings": headings,
        "heading_blocks": _heading_blocks(soup),
        "link_count": len(links),
        "links": links,
        "image_count": len(images),
        "images": images,
        "script_count": len(soup.find_all("script")),
        "stylesheet_count": stylesheet_count,
        "form_count": len(soup.find_all("form")),
        "robots_meta_present": robots_present,
        "robots_meta": robots_meta,
        "viewport": metas.get("viewport"),
        "favicon_declared": favicon,
        "og_title": metas.get("og:title"),
        "og_description": metas.get("og:description"),
        "og_image": metas.get("og:image"),
        "og_site_name": metas.get("og:site_name"),
        "twitter_card": metas.get("twitter:card"),
        "application_name": metas.get("application-name"),
        "paragraphs": paragraphs,
        "lists": lists,
        "table_count": len(soup.find_all("table")),
        "semantic": semantic,
        "has_main_landmark": bool(semantic.get("main")) or has_main_role,
        "header_identity": _header_identity(soup),
        "json_ld": json_ld,
        "visible_text": visible,
        "visible_text_length": text_length,
        "html_length": html_length,
        "text_ratio": (text_length / html_length) if html_length else 0.0,
        "text_node_count": len(text_nodes),
        "tag_count": tag_count,
        "span_count": span_count,
        "hidden_text": hidden,
        "hidden_text_length": len(hidden),
        "byline": byline,
        "author_rel": author_rel,
        "time_values": time_values[:8],
        "emails": emails[:5],
        "tel_links": tel_links[:5],
        "mailto_links": mailto_links[:5],
        "has_address": bool(soup.find("address")),
    }
