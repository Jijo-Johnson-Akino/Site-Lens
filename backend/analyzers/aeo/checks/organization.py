from __future__ import annotations

from backend.analyzers.aeo.checks._util import ABOUT_HREF, ABOUT_TEXT, CONTACT_HREF, entities_of, is_english, language_of, page_url
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, make_check
from backend.parser.structured_data import ORG_TYPES

ORG_FIELDS = ("name", "url", "logo", "description", "sameAs", "contactPoint")


def run(ctx: AeoContext) -> list[CheckResult]:
    page = page_url(ctx)
    english = is_english(language_of(ctx))
    return [_about(ctx, page, english), _contact(ctx, page), _org_properties(ctx, page)]


def _about(ctx: AeoContext, page: str, english: bool) -> CheckResult:
    why = "An About destination or heading helps machines locate organization background. Equivalent non-English labels are not guessed."
    links = ctx.html.get("links") or []
    headings = [item.get("text") or "" for item in (ctx.html.get("headings") or [])]
    href_hit = any(ABOUT_HREF.search(item.get("href") or "") for item in links)
    text_hit = english and (
        any(ABOUT_TEXT.search(item.get("text") or "") for item in links) or any(ABOUT_TEXT.search(text) for text in headings)
    )
    if href_hit or text_hit:
        return make_check(
            check_id="AEO-ORG-001",
            name="About information",
            group="organization_information",
            status="pass",
            severity="medium",
            message="About or company information appears to be linked or headed on the page.",
            why=why,
            detected="About-style href or heading.",
            language_dependent=True,
            page_url=page,
        )
    if not english and not href_hit:
        return make_check(
            check_id="AEO-ORG-001",
            name="About information",
            group="organization_information",
            status="not_applicable",
            severity="medium",
            message="English About-label patterns were not applied because the page language is not English.",
            why=why,
            language_dependent=True,
            page_url=page,
        )
    return make_check(
        check_id="AEO-ORG-001",
        name="About information",
        group="organization_information",
        status="warning",
        severity="medium",
        message="No About, About Us, Who We Are, or Company destination was detected.",
        recommendation="Link to a page that explains the organization, if that content exists.",
        why=why,
        language_dependent=True,
        page_url=page,
    )


def _contact(ctx: AeoContext, page: str) -> CheckResult:
    why = "Email, phone, or a contact page are observable ways to reach the organization. A physical address is not required for every site."
    html = ctx.html
    hits: list[str] = []
    if html.get("emails"):
        hits.append("email")
    if html.get("tel_links"):
        hits.append("telephone link")
    if html.get("mailto_links"):
        hits.append("mailto")
    if html.get("has_address"):
        hits.append("address element")
    if any(CONTACT_HREF.search(item.get("href") or "") for item in (html.get("links") or [])):
        hits.append("contact-style URL")
    orgs = entities_of(ctx, ORG_TYPES)
    if any(entity.get("contactPoint") or entity.get("telephone") or entity.get("email") for entity in orgs):
        hits.append("schema contact")
    if hits:
        return make_check(
            check_id="AEO-ORG-002",
            name="Contact information",
            group="organization_information",
            status="pass",
            severity="medium",
            message="Observable contact information is present.",
            why=why,
            detected=", ".join(hits),
            page_url=page,
        )
    return make_check(
        check_id="AEO-ORG-002",
        name="Contact information",
        group="organization_information",
        status="warning",
        severity="low",
        message="No email, phone, contact URL, or address was detected on this page.",
        recommendation="Provide a contact method that matches how the organization actually wants to be reached. An address is optional.",
        why=why,
        page_url=page,
    )


def _org_properties(ctx: AeoContext, page: str) -> CheckResult:
    why = "Useful Organization properties include name, url, logo, description, sameAs, and contactPoint. Missing optional fields do not make the JSON-LD invalid."
    orgs = entities_of(ctx, ORG_TYPES | {"WebSite"})
    if not orgs:
        return make_check(
            check_id="AEO-ORG-003",
            name="Organization structured information",
            group="organization_information",
            status="not_applicable",
            severity="low",
            message="Organization properties were not evaluated because no Organization/WebSite entity was found.",
            why=why,
            page_url=page,
        )
    entity = orgs[0]
    present = []
    missing = []
    for field in ORG_FIELDS:
        value = entity.get(field)
        ok = bool(value) if field != "sameAs" else bool(value)
        if ok:
            present.append(field)
        else:
            missing.append(field)
    detected_bits = [f"✓ {field}" for field in present] + [f"⚠ {field}" for field in missing]
    if entity.get("name") and (entity.get("url") or entity.get("description")):
        status = "pass" if len(present) >= 3 else "warning"
        return make_check(
            check_id="AEO-ORG-003",
            name="Organization structured information",
            group="organization_information",
            status=status,
            severity="low",
            message="Organization structured data is present; optional properties are reported below.",
            recommendation="Add logo, description, sameAs, or contactPoint when those facts exist. Optional fields are not required for validity.",
            why=why,
            detected="; ".join(detected_bits),
            page_url=page,
        )
    return make_check(
        check_id="AEO-ORG-003",
        name="Organization structured information",
        group="organization_information",
        status="warning",
        severity="medium",
        message="An organization entity was found, but core properties such as name plus url or description are incomplete.",
        recommendation="Include at least name and url or description on the Organization/WebSite object.",
        why=why,
        detected="; ".join(detected_bits),
        page_url=page,
    )
