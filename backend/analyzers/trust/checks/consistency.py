from __future__ import annotations

from backend.analyzers.trust.checks._util import first_name, names_consistent, site_page_id, site_url, trust_check
from backend.analyzers.trust.context import SiteTrustContext
from backend.analyzers.trust.extraction import email_domain, mask_email, same_site_email


def run_site(site: SiteTrustContext):
    url = site_url(site)
    page_id = site_page_id(site)
    checks = []
    visible = first_name(site, "visible", "og", "header", "h1")
    schema = first_name(site, "schema", "organization_schema")
    footer = site.org_names.get("footer")
    about = site.org_names.get("about")
    overlap = names_consistent(visible, schema)
    if visible and footer and overlap is not False:
        footer_overlap = names_consistent(visible, footer)
        if footer_overlap is False:
            overlap = False
    if about and visible:
        about_overlap = names_consistent(visible, about)
        if about_overlap is False:
            overlap = False
    if overlap is True or (visible and schema and overlap is True):
        checks.append(
            trust_check(
                check_id="trust.consistency.organization_name",
                name="Organization name consistency",
                group="consistency",
                status="pass",
                severity="info",
                message="Visible organization name and schema name are consistent.",
                page_url=url,
                page_id=page_id,
                detected=visible or schema,
                evidence={"visible": visible, "schema": schema, "footer": footer, "about": about},
            )
        )
    elif overlap is False:
        checks.append(
            trust_check(
                check_id="trust.consistency.organization_name",
                name="Organization name consistency",
                group="consistency",
                status="warning",
                severity="low",
                message="Potential entity-name inconsistency detected.",
                page_url=url,
                page_id=page_id,
                recommendation="Review visible brand names, footer identity, and Organization structured data for consistent naming.",
                why="SiteLens compared observable strings. It does not determine which name is correct.",
                evidence={"visible": visible, "schema": schema, "footer": footer, "about": about},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.consistency.organization_name",
                name="Organization name consistency",
                group="consistency",
                status="not_applicable",
                severity="info",
                message="Organization names could not be compared because multiple independent values were not available.",
                page_url=url,
                page_id=page_id,
                evidence={"visible": visible, "schema": schema, "footer": footer, "about": about},
            )
        )

    emails = site.emails
    if len(emails) >= 2:
        domains = {email_domain(item) for item in emails if email_domain(item)}
        if len(domains) > 1:
            checks.append(
                trust_check(
                    check_id="trust.consistency.contact_information",
                    name="Contact information consistency",
                    group="consistency",
                    status="warning",
                    severity="low",
                    message="Potential contact-information inconsistency detected.",
                    page_url=url,
                    page_id=page_id,
                    recommendation="Review published contact emails so visitors see a consistent contact path.",
                    why="Different email domains were observed across crawled pages. This is not a fraud determination.",
                    evidence={"emails": [mask_email(item) for item in emails[:6]]},
                )
            )
        else:
            checks.append(
                trust_check(
                    check_id="trust.consistency.contact_information",
                    name="Contact information consistency",
                    group="consistency",
                    status="pass",
                    severity="info",
                    message="Published contact emails are consistent across crawled pages.",
                    page_url=url,
                    page_id=page_id,
                    evidence={"emails": [mask_email(item) for item in emails[:6]]},
                )
            )
    elif emails:
        sample = emails[0]
        aligned = same_site_email(site.host, sample)
        checks.append(
            trust_check(
                check_id="trust.consistency.contact_information",
                name="Contact information consistency",
                group="consistency",
                status="pass",
                severity="info",
                message=(
                    "Contact email domain matches the website domain."
                    if aligned
                    else "A single contact email was detected; no cross-page contact conflict was observed."
                ),
                page_url=url,
                page_id=page_id,
                detected=mask_email(sample),
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.consistency.contact_information",
                name="Contact information consistency",
                group="consistency",
                status="not_applicable",
                severity="info",
                message="Contact-information consistency could not be compared because multiple contact values were not available.",
                page_url=url,
                page_id=page_id,
            )
        )
    return checks
