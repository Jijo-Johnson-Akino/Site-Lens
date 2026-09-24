"""Deterministic visible-content vs schema comparisons. No AI."""

from __future__ import annotations

import re

from backend.analyzers.aeo.checks._util import name_tokens, normalize_name
from backend.analyzers.structured_data.models import SchemaEntity

PRICE_RE = re.compile(r"(?:[$€£]\s?\d[\d,]*(?:\.\d+)?)|(?:\d[\d,]*(?:\.\d+)?\s?(?:usd|eur|gbp))", re.I)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def tokens_overlap(left: str | None, right: str | None) -> bool | None:
    a = name_tokens(left)
    b = name_tokens(right)
    if not a or not b:
        return None
    if a == b:
        return True
    smaller, larger = (a, b) if len(a) <= len(b) else (b, a)
    return smaller.issubset(larger) or len(smaller & larger) / max(len(smaller), 1) >= 0.6


def first_h1(html: dict) -> str | None:
    for item in html.get("h1s") or []:
        text = item.get("text") if isinstance(item, dict) else None
        if text:
            return str(text)
    return None


def visible_blob(html: dict) -> str:
    parts = [
        html.get("title"),
        html.get("og_title"),
        html.get("og_site_name"),
        html.get("byline"),
        html.get("author_rel"),
        first_h1(html),
        html.get("visible_text"),
    ]
    return " ".join(str(part) for part in parts if part)


def name_mismatch(entity: SchemaEntity, html: dict) -> bool | None:
    name = entity.name or entity.properties.get("headline")
    visible = " ".join(filter(None, [html.get("title"), first_h1(html), html.get("og_title"), html.get("og_site_name")]))
    return tokens_overlap(name, visible)


def author_mismatch(entity: SchemaEntity, html: dict) -> bool | None:
    author = entity.properties.get("author") or entity.properties.get("creator")
    visible = " ".join(filter(None, [html.get("byline"), html.get("author_rel")]))
    return tokens_overlap(author, visible)


def date_mismatch(entity: SchemaEntity, html: dict) -> bool | None:
    schema_dates = []
    for key in ("datePublished", "dateModified"):
        value = entity.properties.get(key)
        if value:
            match = DATE_RE.search(value)
            if match:
                schema_dates.append(match.group(0))
    visible_dates = []
    for value in html.get("time_values") or []:
        match = DATE_RE.search(str(value))
        if match:
            visible_dates.append(match.group(0))
    if not schema_dates or not visible_dates:
        return None
    return bool(set(schema_dates).isdisjoint(set(visible_dates)))


def price_mismatch(entity: SchemaEntity, html: dict) -> bool | None:
    schema_price = entity.properties.get("price")
    if not schema_price:
        return None
    schema_digits = re.sub(r"[^\d.]", "", schema_price)
    blob = visible_blob(html)
    visible = PRICE_RE.findall(blob)
    if not visible:
        return None
    visible_digits = {re.sub(r"[^\d.]", "", item) for item in visible}
    if not schema_digits:
        return None
    return schema_digits not in visible_digits
