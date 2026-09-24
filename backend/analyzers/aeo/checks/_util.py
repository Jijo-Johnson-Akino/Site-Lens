from __future__ import annotations

import re
import unicodedata

from backend.analyzers.aeo.context import AeoContext
from backend.parser.structured_data import ARTICLE_TYPES, IDENTITY_TYPES, ORG_TYPES, RELEVANT_TYPES

QUESTION_START = re.compile(
    r"^(what|why|how|when|where|who|which|can|does|do|is|are|should|will)\b",
    re.I,
)
DEFINITION_RE = re.compile(
    r"\b(.{2,60}?)\s+(is|are|refers to|means|helps|provides)\b",
    re.I,
)
ABOUT_HREF = re.compile(r"(about|about-us|who-we-are|our-story|company|team)", re.I)
ABOUT_TEXT = re.compile(r"\b(about us|about|who we are|our story|company)\b", re.I)
CONTACT_HREF = re.compile(r"(contact|support|help)", re.I)
FAQ_TEXT = re.compile(r"\b(faq|faqs|frequently asked questions)\b", re.I)
STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "for",
    "to",
    "in",
    "on",
    "official",
    "home",
    "homepage",
    "website",
    "site",
    "welcome",
}


def page_url(ctx: AeoContext) -> str:
    return ctx.final_url or ctx.page_url


def is_english(language: str | None) -> bool:
    if not language:
        return True
    return language.lower().startswith("en")


def language_of(ctx: AeoContext) -> str | None:
    return ctx.html.get("language")


def json_ld(ctx: AeoContext) -> dict:
    return ctx.html.get("json_ld") or {"script_count": 0, "parse_errors": 0, "valid": False, "entities": [], "types": []}


def entities(ctx: AeoContext) -> list[dict]:
    return json_ld(ctx).get("entities") or []


def types_present(ctx: AeoContext) -> set[str]:
    return set(json_ld(ctx).get("types") or [])


def entities_of(ctx: AeoContext, wanted: set[str]) -> list[dict]:
    found: list[dict] = []
    for entity in entities(ctx):
        if wanted.intersection(entity.get("types") or []):
            found.append(entity)
    return found


def looks_like_article(ctx: AeoContext) -> bool:
    html = ctx.html
    if ARTICLE_TYPES.intersection(types_present(ctx)):
        return True
    semantic = html.get("semantic") or {}
    if semantic.get("article") and (html.get("time_values") or html.get("byline") or html.get("author_rel")):
        return True
    path = (ctx.final_url or ctx.page_url).lower()
    if any(part in path for part in ("/blog", "/article", "/news", "/post/")):
        return True
    return False


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    folded = unicodedata.normalize("NFKD", value)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^a-z0-9\s]", " ", folded.lower())
    return " ".join(cleaned.split())


def name_tokens(value: str | None) -> set[str]:
    return {token for token in normalize_name(value).split() if token and token not in STOPWORDS}


def brand_from_title(title: str | None) -> str | None:
    if not title:
        return None
    for separator in (" | ", " – ", " — ", " - "):
        if separator in title:
            left, right = title.split(separator, 1)
            candidate = left.strip() if len(left.strip()) <= len(right.strip()) else right.strip()
            if 1 < len(candidate) <= 80:
                return candidate
    return title.strip()


def extracted_names(ctx: AeoContext) -> dict[str, str]:
    html = ctx.html
    names: dict[str, str] = {}
    h1s = html.get("h1s") or []
    first_h1 = next((item.get("text") for item in h1s if item.get("text")), None)
    title_brand = brand_from_title(html.get("title"))
    if title_brand:
        names["title"] = title_brand
    if first_h1:
        names["h1"] = first_h1
    if html.get("header_identity"):
        names["header"] = html["header_identity"]
    if html.get("og_site_name"):
        names["og_site_name"] = html["og_site_name"]
    if html.get("application_name"):
        names["application_name"] = html["application_name"]
    for entity in entities_of(ctx, IDENTITY_TYPES):
        if entity.get("name"):
            kind = "schema"
            types = entity.get("types") or []
            if "WebSite" in types:
                kind = "website_schema"
            elif ORG_TYPES.intersection(types):
                kind = "organization_schema"
            elif "Person" in types:
                kind = "person_schema"
            names[kind] = entity["name"]
    return names


def primary_name(ctx: AeoContext) -> str | None:
    names = extracted_names(ctx)
    for key in ("organization_schema", "website_schema", "og_site_name", "header", "h1", "title", "person_schema", "application_name"):
        if names.get(key):
            return names[key]
    return next(iter(names.values()), None)


def first_description(ctx: AeoContext) -> str | None:
    html = ctx.html
    for entity in entities_of(ctx, IDENTITY_TYPES):
        if entity.get("description") and len(entity["description"]) >= 40:
            return entity["description"]
    meta = html.get("meta_description")
    if meta and len(meta) >= 40:
        return meta
    og = html.get("og_description")
    if og and len(og) >= 40:
        return og
    h1 = next((item.get("text") for item in (html.get("h1s") or []) if item.get("text")), "")
    for paragraph in html.get("paragraphs") or []:
        if len(paragraph) >= 40 and (not h1 or h1.lower() not in paragraph.lower() or len(paragraph) > len(h1) + 20):
            return paragraph
    visible = html.get("visible_text") or ""
    if len(visible) >= 80:
        return visible[:240]
    return None


__all__ = [
    "ABOUT_HREF",
    "ABOUT_TEXT",
    "ARTICLE_TYPES",
    "CONTACT_HREF",
    "DEFINITION_RE",
    "FAQ_TEXT",
    "IDENTITY_TYPES",
    "ORG_TYPES",
    "QUESTION_START",
    "RELEVANT_TYPES",
    "brand_from_title",
    "entities",
    "entities_of",
    "extracted_names",
    "first_description",
    "is_english",
    "json_ld",
    "language_of",
    "looks_like_article",
    "name_tokens",
    "normalize_name",
    "page_url",
    "primary_name",
    "types_present",
]
