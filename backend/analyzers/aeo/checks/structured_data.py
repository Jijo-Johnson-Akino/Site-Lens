from __future__ import annotations

from backend.analyzers.aeo.checks._util import entities, json_ld, page_url, types_present
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, make_check
from backend.parser.structured_data import RELEVANT_TYPES

CORE_FIELDS = {
    "Organization": ("name", "url"),
    "LocalBusiness": ("name", "url"),
    "Corporation": ("name", "url"),
    "WebSite": ("name", "url"),
    "Person": ("name",),
    "Article": ("headline", "name", "author", "datePublished"),
    "BlogPosting": ("headline", "name", "author", "datePublished"),
    "Product": ("name",),
    "Service": ("name",),
    "FAQPage": ("name",),
    "WebPage": ("name",),
    "BreadcrumbList": (),
}


def run(ctx: AeoContext) -> list[CheckResult]:
    page = page_url(ctx)
    data = json_ld(ctx)
    return [_json_ld_present(data, page), _relevant(ctx, data, page), _completeness(ctx, data, page)]


def _json_ld_present(data: dict, page: str) -> CheckResult:
    why = "Valid JSON-LD is an explicit machine-readable layer. Invalid JSON is reported without claiming a ranking effect."
    if data.get("valid"):
        extra = f"; {data.get('parse_errors')} additional script(s) failed to parse" if data.get("parse_errors") else ""
        return make_check(
            check_id="AEO-SCHEMA-001",
            name="JSON-LD present",
            group="structured_information",
            status="pass",
            severity="medium",
            message="Valid JSON-LD was detected.",
            why=why,
            detected=f"{data.get('script_count')} script(s); types: {', '.join(data.get('types') or []) or 'untyped'}{extra}",
            page_url=page,
        )
    if int(data.get("script_count") or 0) > 0:
        return make_check(
            check_id="AEO-SCHEMA-001",
            name="JSON-LD present",
            group="structured_information",
            status="fail",
            severity="medium",
            message="JSON-LD script tags were found, but none could be parsed as JSON.",
            recommendation="Fix JSON-LD syntax so the objects can be read.",
            why=why,
            detected=f"{data.get('script_count')} script(s), {data.get('parse_errors')} parse error(s).",
            page_url=page,
        )
    return make_check(
        check_id="AEO-SCHEMA-001",
        name="JSON-LD present",
        group="structured_information",
        status="fail",
        severity="medium",
        message="No JSON-LD was detected.",
        recommendation="Add JSON-LD for the entity the page represents, such as Organization or WebSite.",
        why=why,
        page_url=page,
    )


def _relevant(ctx: AeoContext, data: dict, page: str) -> CheckResult:
    why = "Relevant types include Organization, WebSite, WebPage, Article, Product, Service, FAQPage, BreadcrumbList, Person, and LocalBusiness. Not every page needs every type."
    if not data.get("valid") and not data.get("script_count"):
        return make_check(
            check_id="AEO-SCHEMA-002",
            name="Relevant schema detected",
            group="structured_information",
            status="not_applicable",
            severity="low",
            message="Schema relevance was not evaluated because no JSON-LD was found.",
            why=why,
            page_url=page,
        )
    relevant = sorted(types_present(ctx).intersection(RELEVANT_TYPES))
    other = sorted(types_present(ctx) - RELEVANT_TYPES)
    if relevant:
        return make_check(
            check_id="AEO-SCHEMA-002",
            name="Relevant schema detected",
            group="structured_information",
            status="pass",
            severity="low",
            message="JSON-LD includes types that commonly describe a page or organization.",
            why=why,
            detected=", ".join(relevant),
            page_url=page,
        )
    if other:
        return make_check(
            check_id="AEO-SCHEMA-002",
            name="Relevant schema detected",
            group="structured_information",
            status="warning",
            severity="low",
            message="JSON-LD is present, but none of the common page/entity types were found.",
            recommendation="Add a type that matches the page, such as Organization, WebSite, or Article.",
            why=why,
            detected=", ".join(other),
            page_url=page,
        )
    return make_check(
        check_id="AEO-SCHEMA-002",
        name="Relevant schema detected",
        group="structured_information",
        status="not_applicable",
        severity="low",
        message="Schema relevance was not evaluated because JSON-LD did not yield typed entities.",
        why=why,
        page_url=page,
    )


def _completeness(ctx: AeoContext, data: dict, page: str) -> CheckResult:
    why = "This reports useful properties on detected entities. Missing optional properties do not make the structured data invalid."
    typed = [entity for entity in entities(ctx) if entity.get("types")]
    if not typed:
        return make_check(
            check_id="AEO-SCHEMA-003",
            name="Schema completeness",
            group="structured_information",
            status="not_applicable",
            severity="low",
            message="Schema completeness was not evaluated because no typed JSON-LD entities were found.",
            why=why,
            page_url=page,
        )
    reports = []
    missing_core = False
    for entity in typed[:4]:
        types = entity.get("types") or []
        fields = set()
        for type_name in types:
            fields.update(CORE_FIELDS.get(type_name, ()))
        present = []
        missing = []
        for field in sorted(fields):
            value = entity.get("headline") if field == "headline" else entity.get(field)
            if field == "headline":
                value = entity.get("headline") or entity.get("name")
            if value:
                present.append(field)
            else:
                missing.append(field)
                missing_core = True
        label = "/".join(types)
        reports.append(f"{label}: " + ", ".join(([f"✓ {item}" for item in present] + [f"⚠ {item}" for item in missing]) or ["no core fields listed"]))
    return make_check(
        check_id="AEO-SCHEMA-003",
        name="Schema completeness",
        group="structured_information",
        status="warning" if missing_core else "pass",
        severity="low",
        message="Useful properties on detected entities are listed below. Optional gaps are not treated as invalid JSON-LD.",
        recommendation="Fill in name/url (and author/date for articles) when those facts exist.",
        why=why,
        detected="; ".join(reports),
        page_url=page,
    )
