from __future__ import annotations

from backend.analyzers.trust.checks._util import first_name, site_page_id, site_url, trust_check
from backend.analyzers.trust.config import ORG_SCHEMA_TYPES
from backend.analyzers.trust.context import SiteTrustContext


def run_site(site: SiteTrustContext):
    url = site_url(site)
    page_id = site_page_id(site)
    schema_name = first_name(site, "schema", "organization_schema")
    visible = first_name(site, "visible", "og", "header", "footer", "h1")
    types = {str(item) for item in site.schema_types}
    org_schema = bool(ORG_SCHEMA_TYPES & types)
    identified = bool(schema_name or visible or site.about_pages)
    logo_only = site.logo and not identified
    evidence = {
        "schema_name": schema_name,
        "visible_name": visible,
        "logo": site.logo,
        "org_schema": org_schema,
        "schema_types": sorted(ORG_SCHEMA_TYPES & types),
        "about_pages": len(site.about_pages),
    }
    if identified:
        sources = [key for key, value in site.org_names.items() if value]
        return [
            trust_check(
                check_id="trust.identity.organization.missing",
                name="Organization identity",
                group="identity",
                status="pass",
                severity="info",
                message="Organization identity signals detected.",
                page_url=url,
                page_id=page_id,
                detected=schema_name or visible,
                evidence=evidence,
                details={"sources": sources[:8]},
            )
        ]
    if logo_only:
        return [
            trust_check(
                check_id="trust.identity.organization.missing",
                name="Organization identity",
                group="identity",
                status="warning",
                severity="low",
                message="A logo was detected, but organization identity signals are incomplete.",
                page_url=url,
                page_id=page_id,
                recommendation="Add a visible organization name and Organization structured data where that information is public.",
                why="A logo by itself does not fully identify the organization that operates the website.",
                evidence=evidence,
            )
        ]
    return [
        trust_check(
            check_id="trust.identity.organization.missing",
            name="Organization identity",
            group="identity",
            status="warning",
            severity="medium",
            message="Organization identity signals were not detected within the crawled pages.",
            page_url=url,
            page_id=page_id,
            recommendation="Publish a visible organization name, About information, or Organization structured data.",
            why="Visitors use identity signals to understand who operates the website. This is not a legitimacy determination.",
            evidence=evidence,
        )
    ]
