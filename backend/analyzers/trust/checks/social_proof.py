from __future__ import annotations

from backend.analyzers.trust.checks._util import site_page_id, site_url, trust_check
from backend.analyzers.trust.context import SiteTrustContext


def _first(pages, key: str) -> dict | None:
    for page in pages:
        block = ((page.signals.get("social_proof") or {}).get(key) or {})
        if block.get("detected") or block.get("potential"):
            return {"page": page, "block": block}
    return None


def run_site(site: SiteTrustContext):
    url = site_url(site)
    page_id = site_page_id(site)
    checks = []

    testi = _first(site.pages, "testimonials")
    if testi and testi["block"].get("detected"):
        page = testi["page"]
        count = int(testi["block"].get("count") or 0)
        checks.append(
            trust_check(
                check_id="trust.social_proof.testimonial.detected",
                name="Testimonials",
                group="social_proof",
                status="pass",
                severity="info",
                message="Customer testimonial section detected.",
                page_url=page.url,
                page_id=page.page.id,
                detected=testi["block"].get("heading") or f"{count} testimonial blocks",
                evidence={"count": count, "heading": testi["block"].get("heading")},
            )
        )
    elif testi and testi["block"].get("potential"):
        page = testi["page"]
        checks.append(
            trust_check(
                check_id="trust.social_proof.testimonial.detected",
                name="Testimonials",
                group="social_proof",
                status="pass",
                severity="info",
                message="Potential testimonial section detected.",
                page_url=page.url,
                page_id=page.page.id,
                evidence={"potential": True, "heading": testi["block"].get("heading")},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.social_proof.testimonial.detected",
                name="Testimonials",
                group="social_proof",
                status="not_applicable",
                severity="info",
                message="No testimonial section was detected. Testimonials are not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )

    reviews = _first(site.pages, "reviews")
    if reviews and reviews["block"].get("detected"):
        page = reviews["page"]
        schema = bool(reviews["block"].get("schema"))
        message = "Review markup detected." if schema else "Customer review signals detected."
        checks.append(
            trust_check(
                check_id="trust.social_proof.reviews.detected",
                name="Reviews",
                group="social_proof",
                status="pass",
                severity="info",
                message=message,
                page_url=page.url,
                page_id=page.page.id,
                evidence={"schema": schema},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.social_proof.reviews.detected",
                name="Reviews",
                group="social_proof",
                status="not_applicable",
                severity="info",
                message="No review signals were detected. Reviews are not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )

    cases = _first(site.pages, "case_studies")
    if cases and cases["block"].get("detected"):
        page = cases["page"]
        checks.append(
            trust_check(
                check_id="trust.social_proof.case_study.detected",
                name="Case studies",
                group="social_proof",
                status="pass",
                severity="info",
                message="Case study or customer-story signals detected.",
                page_url=page.url,
                page_id=page.page.id,
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.social_proof.case_study.detected",
                name="Case studies",
                group="social_proof",
                status="not_applicable",
                severity="info",
                message="No case-study signals were detected. Case studies are not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )

    logos = _first(site.pages, "client_logos")
    if logos and logos["block"].get("detected"):
        page = logos["page"]
        count = int(logos["block"].get("count") or 0)
        checks.append(
            trust_check(
                check_id="trust.social_proof.client_logos.detected",
                name="Client logos",
                group="social_proof",
                status="pass",
                severity="info",
                message="Customer logo section detected.",
                page_url=page.url,
                page_id=page.page.id,
                detected=logos["block"].get("heading") or f"{count} images",
                evidence={"count": count, "heading": logos["block"].get("heading")},
            )
        )
    elif logos and logos["block"].get("potential"):
        page = logos["page"]
        checks.append(
            trust_check(
                check_id="trust.social_proof.client_logos.detected",
                name="Client logos",
                group="social_proof",
                status="pass",
                severity="info",
                message="Potential customer logo section detected.",
                page_url=page.url,
                page_id=page.page.id,
                evidence={"potential": True, "heading": logos["block"].get("heading"), "count": logos["block"].get("count")},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.social_proof.client_logos.detected",
                name="Client logos",
                group="social_proof",
                status="not_applicable",
                severity="info",
                message="No customer logo section was detected. Client logos are not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )

    for page in site.pages:
        claims = (page.signals.get("social_proof") or {}).get("user_claims") or []
        if claims:
            checks.append(
                trust_check(
                    check_id="trust.social_proof.customer_claim.detected",
                    name="Customer claim",
                    group="social_proof",
                    status="pass",
                    severity="info",
                    message=f"Customer claim detected: '{claims[0]}'.",
                    page_url=page.url,
                    page_id=page.page.id,
                    detected=claims[0],
                    evidence={"claims": claims[:3]},
                )
            )
            break
    return checks
