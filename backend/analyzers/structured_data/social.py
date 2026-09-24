"""Open Graph and Twitter/X metadata extraction. Not Schema.org."""

from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import Tag

from backend.analyzers.structured_data.models import SocialMeta

OG_KEYS = ("og:title", "og:description", "og:image", "og:url", "og:type", "og:site_name")
TW_KEYS = ("twitter:card", "twitter:title", "twitter:description", "twitter:image", "twitter:site")


def _meta_key(tag: Tag) -> str | None:
    key = tag.get("property") or tag.get("name")
    if isinstance(key, list):
        key = key[0] if key else None
    if not isinstance(key, str):
        return None
    return key.strip().lower() or None


def _meta_content(tag: Tag) -> str | None:
    value = tag.get("content")
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, str):
        return None
    return value.strip() or None


def parse_social(html_source: str) -> tuple[SocialMeta, SocialMeta]:
    soup = BeautifulSoup(html_source or "", "html.parser")
    og_values: dict[str, list[str]] = {key: [] for key in OG_KEYS}
    tw_values: dict[str, list[str]] = {key: [] for key in TW_KEYS}
    for tag in soup.find_all("meta"):
        if not isinstance(tag, Tag):
            continue
        key = _meta_key(tag)
        if not key:
            continue
        content = _meta_content(tag)
        if key in og_values:
            og_values[key].append(content or "")
        if key in tw_values:
            tw_values[key].append(content or "")
    return _pack(og_values), _pack(tw_values)


def _pack(groups: dict[str, list[str]]) -> SocialMeta:
    properties: dict[str, str] = {}
    duplicates: list[str] = []
    empty: list[str] = []
    for key, values in groups.items():
        if not values:
            continue
        first = next((item for item in values if item), "")
        if first:
            properties[key] = first[:300]
        if any(not item for item in values):
            empty.append(key)
        if len([item for item in values if item]) > 1:
            duplicates.append(key)
    return SocialMeta(properties=properties, duplicates=duplicates, empty=empty)
