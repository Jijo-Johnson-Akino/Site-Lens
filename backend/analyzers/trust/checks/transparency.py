from __future__ import annotations

from backend.analyzers.trust.checks._util import site_page_id, site_url, trust_check
from backend.analyzers.trust.context import SiteTrustContext


def run_site(site: SiteTrustContext):
    url = site_url(site)
    page_id = site_page_id(site)
    checks = []
    about = bool(site.about_pages or site.about_links)
    contact = bool(site.contact_pages or site.emails or site.phones or site.contact_forms)
    policies = any(site.policies.values())
    checks.append(
        trust_check(
            check_id="trust.transparency.about.detected",
            name="About transparency",
            group="transparency",
            status="pass" if about else "not_applicable",
            severity="info",
            message="Transparency signal detected." if about else "No About transparency signal was counted beyond page detection.",
            page_url=url,
            page_id=page_id,
        )
    )
    checks.append(
        trust_check(
            check_id="trust.transparency.contact.detected",
            name="Contact transparency",
            group="transparency",
            status="pass" if contact else "not_applicable",
            severity="info",
            message="Transparency signal detected." if contact else "No contact transparency signal was counted beyond contact checks.",
            page_url=url,
            page_id=page_id,
        )
    )
    checks.append(
        trust_check(
            check_id="trust.transparency.policy.detected",
            name="Policy transparency",
            group="transparency",
            status="pass" if policies else "not_applicable",
            severity="info",
            message="Transparency signal detected." if policies else "No policy transparency signal was counted beyond policy checks.",
            page_url=url,
            page_id=page_id,
        )
    )
    years = site.copyright_years
    if years:
        latest = max(years)
        if latest != site.current_year:
            message = f"Copyright year detected: {latest}. Copyright year differs from current year."
        else:
            message = f"Copyright year detected: {latest}."
        checks.append(
            trust_check(
                check_id="trust.transparency.copyright.detected",
                name="Copyright year",
                group="transparency",
                status="pass",
                severity="info",
                message=message,
                page_url=url,
                page_id=page_id,
                detected=str(latest),
                evidence={"years": years, "current_year": site.current_year},
            )
        )
    if site.latest_date:
        checks.append(
            trust_check(
                check_id="trust.transparency.freshness.detected",
                name="Visible update date",
                group="transparency",
                status="pass",
                severity="info",
                message=f"Latest visible update date is {site.latest_date}.",
                page_url=url,
                page_id=page_id,
                detected=site.latest_date,
            )
        )
    if site.footer_present:
        checks.append(
            trust_check(
                check_id="trust.transparency.footer.detected",
                name="Footer identity",
                group="transparency",
                status="pass",
                severity="info",
                message="Footer identity or policy signals detected.",
                page_url=url,
                page_id=page_id,
            )
        )
    if site.citations or site.methodology:
        checks.append(
            trust_check(
                check_id="trust.transparency.credibility.detected",
                name="Content credibility signals",
                group="transparency",
                status="pass",
                severity="info",
                message="Reference, source, methodology, or editorial signals detected.",
                page_url=url,
                page_id=page_id,
                detected="methodology" if site.methodology else "citations",
                evidence={"citations": site.citations, "methodology": site.methodology},
            )
        )
    return checks
