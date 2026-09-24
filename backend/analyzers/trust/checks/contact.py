from __future__ import annotations

from backend.analyzers.trust.checks._util import masked_emails, masked_phones, site_page_id, site_url, trust_check
from backend.analyzers.trust.context import PageTrustContext, SiteTrustContext
from backend.analyzers.trust.extraction import consumer_email, external_email_domain, mask_email, same_site_email


def _has_any_contact(site: SiteTrustContext) -> bool:
    return bool(site.contact_pages or site.emails or site.phones or site.addresses or site.contact_forms)


def run_site(site: SiteTrustContext):
    url = site_url(site)
    page_id = site_page_id(site)
    checks = []
    any_contact = _has_any_contact(site)
    if site.contact_pages:
        checks.append(
            trust_check(
                check_id="trust.contact.page.missing",
                name="Contact page",
                group="contact",
                status="pass",
                severity="info",
                message="Contact page detected within the crawled pages.",
                page_url=site.contact_pages[0].get("url") or url,
                page_id=site.contact_pages[0].get("page_id") or page_id,
                detected=site.contact_pages[0].get("url"),
                evidence={"pages": [item.get("url") for item in site.contact_pages[:6]]},
            )
        )
    elif any_contact:
        checks.append(
            trust_check(
                check_id="trust.contact.page.missing",
                name="Contact page",
                group="contact",
                status="pass",
                severity="info",
                message="No dedicated contact page was detected within the crawled pages, but other contact methods were observed.",
                page_url=url,
                page_id=page_id,
                evidence={"emails": masked_emails(site.emails), "phones": masked_phones(site.phones), "form": site.contact_forms},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.contact.page.missing",
                name="Contact page",
                group="contact",
                status="warning",
                severity="medium",
                message="No dedicated contact page was detected within the crawled pages.",
                page_url=url,
                page_id=page_id,
                recommendation="Provide a crawlable contact destination or another visible contact method.",
                why="Contactability is reported from pages in the SiteLens crawl. Missing detection is not proof that contact information does not exist.",
            )
        )

    if site.emails:
        sample = site.emails[0]
        external = external_email_domain(site.host, sample)
        aligned = same_site_email(site.host, sample)
        if external:
            message = "Contact email uses an external domain."
            if consumer_email(sample):
                message = "Contact email uses an external domain."
            checks.append(
                trust_check(
                    check_id="trust.contact.email.present",
                    name="Contact email",
                    group="contact",
                    status="pass",
                    severity="info",
                    message=message,
                    page_url=site.email_pages.get(sample, url),
                    page_id=page_id,
                    detected=mask_email(sample),
                    evidence={"emails": masked_emails(site.emails), "same_site": aligned},
                    details={"external_domain": True},
                )
            )
        else:
            checks.append(
                trust_check(
                    check_id="trust.contact.email.present",
                    name="Contact email",
                    group="contact",
                    status="pass",
                    severity="info",
                    message="Contact email detected.",
                    page_url=site.email_pages.get(sample, url),
                    page_id=page_id,
                    detected=mask_email(sample),
                    evidence={"emails": masked_emails(site.emails), "same_site": aligned},
                )
            )
    elif any_contact:
        checks.append(
            trust_check(
                check_id="trust.contact.email.missing",
                name="Contact email",
                group="contact",
                status="not_applicable",
                severity="info",
                message="A contact email was not required because other contact methods were detected.",
                page_url=url,
                page_id=page_id,
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.contact.email.missing",
                name="Contact email",
                group="contact",
                status="not_applicable",
                severity="info",
                message="No contact email was detected within the crawled pages.",
                page_url=url,
                page_id=page_id,
            )
        )

    if site.phones:
        checks.append(
            trust_check(
                check_id="trust.contact.phone.present",
                name="Contact phone",
                group="contact",
                status="pass",
                severity="info",
                message="Phone number detected.",
                page_url=url,
                page_id=page_id,
                detected=masked_phones(site.phones)[0],
                evidence={"phones": masked_phones(site.phones)},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.contact.phone.missing",
                name="Contact phone",
                group="contact",
                status="not_applicable",
                severity="info",
                message="No phone number was detected within the crawled pages. A phone number is not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )

    if site.addresses:
        checks.append(
            trust_check(
                check_id="trust.contact.address.present",
                name="Contact address",
                group="contact",
                status="pass",
                severity="info",
                message="Business address detected.",
                page_url=url,
                page_id=page_id,
                detected=site.addresses[0][:120],
                evidence={"address": site.addresses[0][:160]},
            )
        )
    else:
        local = "LocalBusiness" in site.schema_types
        checks.append(
            trust_check(
                check_id="trust.contact.address.missing",
                name="Contact address",
                group="contact",
                status="warning" if local else "not_applicable",
                severity="low" if local else "info",
                message=(
                    "LocalBusiness structured data was detected without a visible address in the crawled pages."
                    if local
                    else "No physical address was detected within the crawled pages. A physical address is not required for every website type."
                ),
                page_url=url,
                page_id=page_id,
            )
        )

    if site.contact_forms:
        checks.append(
            trust_check(
                check_id="trust.contact.form.present",
                name="Contact form",
                group="contact",
                status="pass",
                severity="info",
                message="Contact form detected.",
                page_url=url,
                page_id=page_id,
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.contact.form.present",
                name="Contact form",
                group="contact",
                status="not_applicable",
                severity="info",
                message="No contact form was detected within the crawled pages. A form is not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )

    if site.social_profiles:
        platforms = sorted({item.get("platform") or "" for item in site.social_profiles if item.get("platform")})
        checks.append(
            trust_check(
                check_id="trust.contact.social.detected",
                name="Social profiles",
                group="contact",
                status="pass",
                severity="info",
                message="Social profile links detected.",
                page_url=url,
                page_id=page_id,
                detected=", ".join(platforms[:6]),
                evidence={"platforms": platforms[:8]},
            )
        )
    return checks


def run_page(ctx: PageTrustContext):
    if ctx.page_type != "contact":
        return []
    contact = ctx.signals.get("contact") or {}
    methods = []
    if contact.get("emails"):
        methods.append("email")
    if contact.get("phones"):
        methods.append("phone")
    if contact.get("has_address") or contact.get("address_text"):
        methods.append("address")
    if contact.get("form"):
        methods.append("form")
    if methods:
        return [
            trust_check(
                check_id="trust.contact.page.methods",
                name="Contact page methods",
                group="contact",
                status="pass",
                severity="info",
                message="Contact methods detected on the contact page.",
                page_url=ctx.url,
                page_id=ctx.page.id,
                detected=", ".join(methods),
                evidence={"methods": methods, "emails": masked_emails(list(contact.get("emails") or []))},
            )
        ]
    return [
        trust_check(
            check_id="trust.contact.page.methods",
            name="Contact page methods",
            group="contact",
            status="warning",
            severity="low",
            message="A contact page was detected, but no email, phone, address, or form was observed on that page.",
            page_url=ctx.url,
            page_id=ctx.page.id,
            recommendation="Add at least one visible contact method on the contact page.",
            why="The page was classified as a contact page from URL or page-type signals.",
        )
    ]
