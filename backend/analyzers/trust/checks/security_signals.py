from __future__ import annotations

from backend.analyzers.trust.checks._util import site_page_id, site_url, trust_check
from backend.analyzers.trust.context import SiteTrustContext


def run_site(site: SiteTrustContext):
    url = site_url(site)
    page_id = site_page_id(site)
    checks = []
    if site.https:
        checks.append(
            trust_check(
                check_id="trust.security.https.enabled",
                name="HTTPS",
                group="security",
                status="pass",
                severity="info",
                message="HTTPS enabled.",
                page_url=url,
                page_id=page_id,
                detected="https",
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.security.https.enabled",
                name="HTTPS",
                group="security",
                status="warning",
                severity="medium",
                message="HTTPS was not detected for the scanned URL.",
                page_url=url,
                page_id=page_id,
                recommendation="Serve the public website over HTTPS.",
                why="HTTPS is a transport property of the scanned URL. This finding is not a security certification or vulnerability assessment.",
            )
        )

    badges: list[str] = []
    badge_url = url
    badge_id = page_id
    payments: list[str] = []
    pay_url = url
    pay_id = page_id
    wording = False
    for page in site.pages:
        security = page.signals.get("security") or {}
        if security.get("badges"):
            badges.extend(security.get("badges") or [])
            badge_url = page.url
            badge_id = page.page.id
        if security.get("payment_brands"):
            payments.extend(security.get("payment_brands") or [])
            pay_url = page.url
            pay_id = page.page.id
        if security.get("secure_wording"):
            wording = True

    if badges:
        checks.append(
            trust_check(
                check_id="trust.security.badge.detected",
                name="Security badges",
                group="security",
                status="pass",
                severity="info",
                message="Security badge detected.",
                page_url=badge_url,
                page_id=badge_id,
                detected=badges[0],
                evidence={"badges": badges[:6]},
            )
        )
    elif wording:
        checks.append(
            trust_check(
                check_id="trust.security.badge.detected",
                name="Security badges",
                group="security",
                status="pass",
                severity="info",
                message="Security-related wording detected.",
                page_url=url,
                page_id=page_id,
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.security.badge.detected",
                name="Security badges",
                group="security",
                status="not_applicable",
                severity="info",
                message="No security badges were detected. Badges are not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )

    unique_pay = list(dict.fromkeys(payments))
    if unique_pay:
        checks.append(
            trust_check(
                check_id="trust.security.payment_method.detected",
                name="Payment indicators",
                group="security",
                status="pass",
                severity="info",
                message="Payment provider branding detected.",
                page_url=pay_url,
                page_id=pay_id,
                detected=", ".join(unique_pay[:6]),
                evidence={"brands": unique_pay[:8]},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.security.payment_method.detected",
                name="Payment indicators",
                group="security",
                status="not_applicable",
                severity="info",
                message="No payment provider branding was detected. Payment logos are not required for every website type.",
                page_url=url,
                page_id=page_id,
            )
        )
    return checks


def run_page(ctx):
    if ctx.page_type != "login":
        return []
    security = ctx.signals.get("security") or {}
    policies = ctx.signals.get("policies") or {}
    identity = ctx.signals.get("identity") or {}
    wording = bool(security.get("secure_wording"))
    privacy = bool(policies.get("privacy"))
    named = bool(identity.get("visible_name") or identity.get("og_site_name") or identity.get("header_name"))
    evidence = {"secure_wording": wording, "privacy_link": privacy, "organization_name": named}
    if wording:
        return [
            trust_check(
                check_id="trust.security.login.messaging",
                name="Login security messaging",
                group="security",
                status="pass",
                severity="info",
                message="Security-related wording detected on a login or signup page.",
                page_url=ctx.url,
                page_id=ctx.page.id,
                evidence=evidence,
            )
        ]
    return [
        trust_check(
            check_id="trust.security.login.messaging",
            name="Login security messaging",
            group="security",
            status="not_applicable",
            severity="info",
            message="No security-related wording was detected on this login or signup page.",
            page_url=ctx.url,
            page_id=ctx.page.id,
            evidence=evidence,
        )
    ]
