from __future__ import annotations

from backend.analyzers.structured_data.consistency import tokens_overlap
from backend.analyzers.trust.context import PageTrustContext, SiteTrustContext
from backend.analyzers.trust.extraction import mask_email, mask_phone
from backend.analyzers.trust.models import CheckResult, make_check
from backend.analyzers.uiux.sanitizer import sanitize_selector, sanitize_text


def trust_check(
    *,
    check_id: str,
    name: str,
    group,
    status,
    severity,
    message: str,
    page_url: str,
    page_id: str | None = None,
    recommendation: str | None = None,
    why: str | None = None,
    detected: str | None = None,
    selector: str | None = None,
    evidence: dict | None = None,
    details: dict | None = None,
    affected_element_count: int = 0,
) -> CheckResult:
    return make_check(
        check_id=check_id,
        name=name,
        group=group,
        status=status,
        severity=severity,
        message=message,
        page_url=page_url,
        page_id=page_id,
        recommendation=recommendation,
        why=why,
        detected=sanitize_text(detected, 160) if detected else None,
        selector=sanitize_selector(selector) if selector else None,
        evidence=evidence,
        details=details,
        affected_element_count=affected_element_count,
    )


def site_url(site: SiteTrustContext) -> str:
    return site.seed_url


def site_page_id(site: SiteTrustContext) -> str | None:
    return site.seed_page_id


def names_consistent(left: str | None, right: str | None) -> bool | None:
    return tokens_overlap(left, right)


def first_name(site: SiteTrustContext, *keys: str) -> str | None:
    for key in keys:
        value = site.org_names.get(key)
        if value:
            return value
    return next(iter(site.org_names.values()), None)


def masked_emails(values: list[str]) -> list[str]:
    return [mask_email(item) or item for item in values[:6]]


def masked_phones(values: list[str]) -> list[str]:
    return [mask_phone(item) or item for item in values[:6]]


def page_authors(ctx: PageTrustContext) -> list[str]:
    authorship = (ctx.signals.get("authorship") or {}) if ctx.signals else {}
    values = list(authorship.get("authors") or [])
    values.extend(ctx.content_authors)
    unique: list[str] = []
    seen: set[str] = set()
    for item in values:
        key = str(item).strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(str(item).strip())
    return unique


def page_schema_authors(ctx: PageTrustContext) -> list[str]:
    authorship = (ctx.signals.get("authorship") or {}) if ctx.signals else {}
    values = list(authorship.get("schema_authors") or [])
    for entity in ctx.schema_entities:
        props = entity.get("properties") if isinstance(entity.get("properties"), dict) else {}
        if props.get("author"):
            values.append(str(props["author"]))
        types = entity.get("types") or []
        if "Person" in types and entity.get("name"):
            values.append(str(entity["name"]))
    unique: list[str] = []
    seen: set[str] = set()
    for item in values:
        key = str(item).strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(str(item).strip())
    return unique


def page_dates(ctx: PageTrustContext) -> list[str]:
    authorship = (ctx.signals.get("authorship") or {}) if ctx.signals else {}
    values = list(authorship.get("dates") or [])
    values.extend(ctx.content_dates)
    return list(dict.fromkeys(str(item) for item in values if item))
