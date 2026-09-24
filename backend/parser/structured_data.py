"""Shared JSON-LD extraction. Used by AEO (and any later structured-data module)."""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

RELEVANT_TYPES = {
    "Organization",
    "LocalBusiness",
    "Corporation",
    "Person",
    "WebSite",
    "WebPage",
    "Article",
    "BlogPosting",
    "Product",
    "Service",
    "FAQPage",
    "BreadcrumbList",
}

ORG_TYPES = {"Organization", "LocalBusiness", "Corporation"}
ARTICLE_TYPES = {"Article", "BlogPosting", "NewsArticle", "TechArticle"}
IDENTITY_TYPES = ORG_TYPES | {"Person", "WebSite"}


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, dict):
        return _as_str(value.get("name") or value.get("@id") or value.get("url") or value.get("text"))
    if isinstance(value, list) and value:
        return _as_str(value[0])
    return str(value).strip() or None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in (_as_str(part) for part in value) if item]
    item = _as_str(value)
    return [item] if item else []


def _types(node: dict) -> list[str]:
    raw = node.get("@type")
    if raw is None:
        return []
    values = raw if isinstance(raw, list) else [raw]
    cleaned: list[str] = []
    for item in values:
        text = str(item).strip()
        if "/" in text:
            text = text.rsplit("/", 1)[-1]
        if text:
            cleaned.append(text)
    return cleaned


def _logo(value: Any) -> str | None:
    if isinstance(value, dict):
        return _as_str(value.get("url") or value.get("contentUrl") or value.get("@id"))
    return _as_str(value)


def _author_name(value: Any) -> str | None:
    if isinstance(value, dict):
        return _as_str(value.get("name"))
    if isinstance(value, list) and value:
        return _author_name(value[0])
    return _as_str(value)


def _entity(node: dict) -> dict:
    types = _types(node)
    return {
        "types": types,
        "name": _as_str(node.get("name") or node.get("legalName") or node.get("headline")),
        "headline": _as_str(node.get("headline")),
        "url": _as_str(node.get("url")),
        "logo": _logo(node.get("logo")),
        "description": _as_str(node.get("description")),
        "sameAs": _as_list(node.get("sameAs")),
        "contactPoint": bool(node.get("contactPoint")),
        "author": _author_name(node.get("author")),
        "creator": _author_name(node.get("creator")),
        "datePublished": _as_str(node.get("datePublished")),
        "dateModified": _as_str(node.get("dateModified")),
        "telephone": _as_str(node.get("telephone")),
        "email": _as_str(node.get("email")),
        "address": bool(node.get("address")),
    }


def _collect(node: Any, entities: list[dict]) -> None:
    if isinstance(node, list):
        for item in node:
            _collect(item, entities)
        return
    if not isinstance(node, dict):
        return
    if "@graph" in node:
        _collect(node.get("@graph"), entities)
    if _types(node):
        entities.append(_entity(node))
    author = node.get("author") or node.get("creator")
    if isinstance(author, dict) and _types(author):
        entities.append(_entity(author))
    elif isinstance(author, list):
        for item in author:
            if isinstance(item, dict) and _types(item):
                entities.append(_entity(item))


def json_ld_script_texts(soup: BeautifulSoup) -> list[str]:
    """Return raw text of application/ld+json scripts, including empty/malformed ones."""
    texts: list[str] = []
    for script in soup.find_all("script"):
        if not isinstance(script, Tag):
            continue
        script_type = (script.get("type") or "")
        if isinstance(script_type, list):
            script_type = script_type[0] if script_type else ""
        if str(script_type).strip().lower() != "application/ld+json":
            continue
        raw = script.string if script.string is not None else script.get_text()
        texts.append(str(raw) if raw is not None else "")
    return texts


def schema_type_names(node: dict) -> list[str]:
    return _types(node)


def node_text(value: Any) -> str | None:
    return _as_str(value)


def node_text_list(value: Any) -> list[str]:
    return _as_list(value)


def extract_json_ld(soup: BeautifulSoup) -> dict:
    """Parse application/ld+json scripts. Does not validate against schema.org."""
    entities: list[dict] = []
    parse_errors = 0
    scripts = json_ld_script_texts(soup)
    script_count = len(scripts)
    for raw in scripts:
        if not raw or not str(raw).strip():
            parse_errors += 1
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        _collect(payload, entities)

    types: list[str] = []
    seen: set[str] = set()
    for entity in entities:
        for item in entity.get("types") or []:
            if item not in seen:
                seen.add(item)
                types.append(item)

    return {
        "script_count": script_count,
        "parse_errors": parse_errors,
        "valid": bool(entities),
        "entities": entities,
        "types": types,
    }
