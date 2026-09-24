from __future__ import annotations

from backend.analyzers.trust.checks._util import site_page_id, site_url, trust_check
from backend.analyzers.trust.context import SiteTrustContext


def run_site(site: SiteTrustContext):
    url = site_url(site)
    page_id = site_page_id(site)
    certs: list[str] = []
    awards: list[str] = []
    cert_page = url
    award_page = url
    cert_id = page_id
    award_id = page_id
    for page in site.pages:
        cred = page.signals.get("credentials") or {}
        proof = page.signals.get("social_proof") or {}
        cert_block = cred.get("certifications") or {}
        award_block = cred.get("awards") or proof.get("awards") or {}
        if cert_block.get("detected"):
            certs.extend(cert_block.get("labels") or ["Certification badge"])
            cert_page = page.url
            cert_id = page.page.id
        if award_block.get("detected"):
            awards.extend(award_block.get("labels") or ["Award badge"])
            award_page = page.url
            award_id = page.page.id

    checks = []
    if certs:
        checks.append(
            trust_check(
                check_id="trust.credentials.certification.detected",
                name="Certifications",
                group="credentials",
                status="pass",
                severity="info",
                message="A certification badge was detected.",
                page_url=cert_page,
                page_id=cert_id,
                detected=certs[0],
                evidence={"labels": certs[:6]},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.credentials.certification.detected",
                name="Certifications",
                group="credentials",
                status="not_applicable",
                severity="info",
                message="No certification badges were detected. Certifications are not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )
    if awards:
        checks.append(
            trust_check(
                check_id="trust.credentials.award.detected",
                name="Awards",
                group="credentials",
                status="pass",
                severity="info",
                message="An award signal was detected.",
                page_url=award_page,
                page_id=award_id,
                detected=awards[0],
                evidence={"labels": awards[:6]},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.credentials.award.detected",
                name="Awards",
                group="credentials",
                status="not_applicable",
                severity="info",
                message="No award signals were detected. Awards are not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )
    return checks
