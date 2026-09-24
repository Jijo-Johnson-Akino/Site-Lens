"""Format checks for URLs, @id, sameAs, and @context. No outbound fetches."""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit

from backend.analyzers.structured_data.models import JsonLdBlock, SchemaEntity

ALLOWED_SCHEMES = {"http", "https", "mailto", "tel", ""}


def is_url_like(value: str | None, base_url: str) -> bool:
    if not value or not str(value).strip():
        return False
    text = str(value).strip()
    if text.startswith("#") and len(text) > 1:
        return True
    if " " in text and not text.startswith("http"):
        return False
    parsed = urlsplit(urljoin(base_url, text))
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False
    if parsed.scheme.lower() in {"mailto", "tel"}:
        return bool(parsed.path)
    return bool(parsed.netloc or parsed.path)


def invalid_urls(entity: SchemaEntity, base_url: str) -> list[tuple[str, str]]:
    bad: list[tuple[str, str]] = []
    if entity.id and not is_url_like(entity.id, base_url) and not entity.id.startswith("_:"):
        bad.append(("@id", entity.id))
    for key in ("url", "image", "logo"):
        value = entity.properties.get(key)
        if value and not is_url_like(value, base_url):
            bad.append((key, value))
    same = entity.properties.get("sameAs")
    if same:
        for part in [item.strip() for item in same.split(",") if item.strip()]:
            if not is_url_like(part, base_url):
                bad.append(("sameAs", part))
    return bad


def same_as_issues(entity: SchemaEntity) -> list[str]:
    raw = entity.properties.get("sameAs")
    if not raw:
        return []
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    issues = []
    seen = set()
    for part in parts:
        key = part.lower()
        if key in seen:
            issues.append(f"duplicate {part}")
        seen.add(key)
    return issues


def context_kind(block: JsonLdBlock) -> str:
    ctx = (block.context or "").lower()
    if not ctx:
        return "missing"
    if "schema.org" in ctx:
        if ctx.startswith("http://schema.org"):
            return "http"
        return "schema"
    return "other"
