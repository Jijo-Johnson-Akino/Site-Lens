from __future__ import annotations

from backend.analyzers.trust.checks._util import site_page_id, site_url, trust_check
from backend.analyzers.trust.context import SiteTrustContext


def run_site(site: SiteTrustContext):
    url = site_url(site)
    page_id = site_page_id(site)
    checks = []
    if site.addresses:
        checks.append(
            trust_check(
                check_id="trust.business.address.detected",
                name="Business address",
                group="business",
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
        checks.append(
            trust_check(
                check_id="trust.business.address.detected",
                name="Business address",
                group="business",
                status="not_applicable",
                severity="info",
                message="No business address was detected within the crawled pages. A physical address is not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )
    if site.hours:
        checks.append(
            trust_check(
                check_id="trust.business.hours.detected",
                name="Business hours",
                group="business",
                status="pass",
                severity="info",
                message="Business hours detected.",
                page_url=url,
                page_id=page_id,
                detected=site.hours[0],
                evidence={"hours": site.hours[:4]},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.business.hours.detected",
                name="Business hours",
                group="business",
                status="not_applicable",
                severity="info",
                message="No business hours were detected. Hours are not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )
    if site.identifiers:
        checks.append(
            trust_check(
                check_id="trust.business.identifier.detected",
                name="Business identifier",
                group="business",
                status="pass",
                severity="info",
                message="A business identifier was detected in page content.",
                page_url=url,
                page_id=page_id,
                detected=site.identifiers[0],
                evidence={"identifiers": site.identifiers[:4]},
                details={"verified": False},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.business.identifier.detected",
                name="Business identifier",
                group="business",
                status="not_applicable",
                severity="info",
                message="No business registration identifier was detected in crawled content.",
                page_url=url,
                page_id=page_id,
            )
        )
    return checks
