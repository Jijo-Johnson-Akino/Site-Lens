from __future__ import annotations

from backend.analyzers.trust.checks._util import site_page_id, site_url, trust_check
from backend.analyzers.trust.config import POLICY_LABELS
from backend.analyzers.trust.context import SiteTrustContext


def _present(site: SiteTrustContext, key: str) -> list[dict]:
    return list(site.policies.get(key) or [])


def run_site(site: SiteTrustContext):
    url = site_url(site)
    page_id = site_page_id(site)
    checks = []
    privacy = _present(site, "privacy")
    if privacy:
        checks.append(
            trust_check(
                check_id="trust.policy.privacy.missing",
                name="Privacy policy",
                group="policies",
                status="pass",
                severity="info",
                message="Privacy policy page detected.",
                page_url=privacy[0].get("href") or url,
                page_id=page_id,
                detected=privacy[0].get("href"),
                evidence={"links": privacy[:4]},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.policy.privacy.missing",
                name="Privacy policy",
                group="policies",
                status="warning",
                severity="low",
                message="No privacy policy page was detected within the crawled pages.",
                page_url=url,
                page_id=page_id,
                recommendation="Add a discoverable privacy policy link from the footer or navigation if a privacy policy is published.",
                why="This check reports link and page detection. It does not assess legal compliance.",
            )
        )

    terms = _present(site, "terms")
    if terms:
        checks.append(
            trust_check(
                check_id="trust.policy.terms.missing",
                name="Terms",
                group="policies",
                status="pass",
                severity="info",
                message="Terms page detected.",
                page_url=terms[0].get("href") or url,
                page_id=page_id,
                detected=terms[0].get("href"),
                evidence={"links": terms[:4]},
            )
        )
    elif site.has_product:
        checks.append(
            trust_check(
                check_id="trust.policy.terms.missing",
                name="Terms",
                group="policies",
                status="warning",
                severity="low",
                message="No terms page was detected within the crawled pages.",
                page_url=url,
                page_id=page_id,
                recommendation="Add a discoverable terms link if terms are published for this offer.",
                why="Terms are reported as observed links or pages. This is not legal advice.",
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.policy.terms.missing",
                name="Terms",
                group="policies",
                status="not_applicable",
                severity="info",
                message="A terms page was not required for the detected website type.",
                page_url=url,
                page_id=page_id,
            )
        )

    refund = _present(site, "refund") or _present(site, "return")
    if refund:
        kind = "refund" if _present(site, "refund") else "return"
        checks.append(
            trust_check(
                check_id="trust.policy.refund.missing",
                name="Refund or return policy",
                group="policies",
                status="pass",
                severity="info",
                message=f"{POLICY_LABELS[kind]} detected.",
                page_url=refund[0].get("href") or url,
                page_id=page_id,
                detected=refund[0].get("href"),
            )
        )
    elif site.has_product:
        checks.append(
            trust_check(
                check_id="trust.policy.refund.missing",
                name="Refund or return policy",
                group="policies",
                status="warning",
                severity="low",
                message="No refund or return policy page was detected within the crawled pages.",
                page_url=url,
                page_id=page_id,
                recommendation="If refund or return terms are published, link them from footer or checkout-related pages.",
                why="Policy applicability depends on website type. This is not a legal-compliance finding.",
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.policy.refund.missing",
                name="Refund or return policy",
                group="policies",
                status="not_applicable",
                severity="info",
                message="A refund policy was not required for the detected website type.",
                page_url=url,
                page_id=page_id,
            )
        )

    for key in ("cookie", "shipping", "disclaimer"):
        items = _present(site, key)
        if not items:
            continue
        checks.append(
            trust_check(
                check_id=f"trust.policy.{key}.detected",
                name=POLICY_LABELS[key],
                group="policies",
                status="pass",
                severity="info",
                message=f"{POLICY_LABELS[key]} detected.",
                page_url=items[0].get("href") or url,
                page_id=page_id,
                detected=items[0].get("href"),
            )
        )
    return checks
