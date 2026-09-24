from __future__ import annotations

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, make_check

ROBOTS_HINTS = ("user-agent", "disallow", "allow", "sitemap", "crawl-delay")


def run(ctx: SeoContext) -> list[CheckResult]:
    page = ctx.final_url or ctx.page_url
    probe = ctx.robots_txt or {}
    exists = bool(probe.get("exists"))
    status = probe.get("status_code")
    body = probe.get("body") if isinstance(probe.get("body"), str) else None
    return [_exists(exists, status, page), _accessible(exists, status, page), _validity(exists, body, page)]


def _exists(exists: bool, status: int | None, page: str) -> CheckResult:
    why = "robots.txt tells crawlers which paths they may request. It is a crawl signal, not a ranking score by itself."
    if exists:
        return make_check(
            check_id="SEO-ROBOTS-001",
            name="robots.txt exists",
            group="robots_sitemap",
            status="pass",
            severity="medium",
            message="A robots.txt file was found at the site origin.",
            why=why,
            detected=f"HTTP {status}",
            page_url=page,
        )
    return make_check(
        check_id="SEO-ROBOTS-001",
        name="robots.txt exists",
        group="robots_sitemap",
        status="fail",
        severity="medium",
        message="No robots.txt file was found at the site origin.",
        recommendation="Publish a robots.txt file if you need to guide crawler access. Missing robots.txt is common and not automatically harmful.",
        why=why,
        detected=f"HTTP {status}" if status is not None else "Request failed.",
        page_url=page,
    )


def _accessible(exists: bool, status: int | None, page: str) -> CheckResult:
    why = "Crawlers can only use robots.txt when the file is reachable with a successful response."
    if status is None:
        return make_check(
            check_id="SEO-ROBOTS-002",
            name="robots.txt accessible",
            group="robots_sitemap",
            status="fail",
            severity="medium",
            message="robots.txt could not be requested.",
            why=why,
            detected="No HTTP status.",
            page_url=page,
        )
    if exists and status == 200:
        return make_check(
            check_id="SEO-ROBOTS-002",
            name="robots.txt accessible",
            group="robots_sitemap",
            status="pass",
            severity="medium",
            message="robots.txt returned HTTP 200.",
            why=why,
            detected="HTTP 200",
            page_url=page,
        )
    if status in {401, 403}:
        return make_check(
            check_id="SEO-ROBOTS-002",
            name="robots.txt accessible",
            group="robots_sitemap",
            status="warning",
            severity="medium",
            message="robots.txt was blocked by HTTP authentication or forbidden status.",
            recommendation="Allow crawlers to read robots.txt if you intend to publish crawl rules.",
            why=why,
            detected=f"HTTP {status}",
            page_url=page,
        )
    if status >= 500:
        return make_check(
            check_id="SEO-ROBOTS-002",
            name="robots.txt accessible",
            group="robots_sitemap",
            status="warning",
            severity="medium",
            message="robots.txt returned a server error.",
            why=why,
            detected=f"HTTP {status}",
            page_url=page,
        )
    return make_check(
        check_id="SEO-ROBOTS-002",
        name="robots.txt accessible",
        group="robots_sitemap",
        status="not_applicable",
        severity="medium",
        message="Accessibility is already reflected by the missing robots.txt result.",
        detected=f"HTTP {status}",
        page_url=page,
    )


def _validity(exists: bool, body: str | None, page: str) -> CheckResult:
    why = "This is a basic sanity check, not a full robots.txt parser."
    if not exists or body is None:
        return make_check(
            check_id="SEO-ROBOTS-003",
            name="robots.txt basic validity",
            group="robots_sitemap",
            status="not_applicable",
            severity="low",
            message="robots.txt content was not evaluated because the file was not retrieved.",
            page_url=page,
        )
    stripped = body.strip()
    lowered = stripped.lower()
    if not stripped:
        return make_check(
            check_id="SEO-ROBOTS-003",
            name="robots.txt basic validity",
            group="robots_sitemap",
            status="warning",
            severity="low",
            message="robots.txt was empty.",
            recommendation="Add at least a User-agent group if you intend to publish crawl rules.",
            why=why,
            detected="Empty body.",
            page_url=page,
        )
    if "<html" in lowered or "<!doctype html" in lowered:
        return make_check(
            check_id="SEO-ROBOTS-003",
            name="robots.txt basic validity",
            group="robots_sitemap",
            status="fail",
            severity="medium",
            message="robots.txt appears to contain HTML instead of robots directives.",
            recommendation="Serve a plain-text robots.txt file rather than an HTML error page.",
            why=why,
            detected="HTML markup was detected in the response body.",
            page_url=page,
        )
    if any(hint in lowered for hint in ROBOTS_HINTS):
        return make_check(
            check_id="SEO-ROBOTS-003",
            name="robots.txt basic validity",
            group="robots_sitemap",
            status="pass",
            severity="low",
            message="robots.txt contains recognizable robots directives.",
            why=why,
            page_url=page,
        )
    return make_check(
        check_id="SEO-ROBOTS-003",
        name="robots.txt basic validity",
        group="robots_sitemap",
        status="warning",
        severity="low",
        message="robots.txt did not contain obvious robots directives.",
        recommendation="Check that the file includes at least a User-agent group.",
        why=why,
        page_url=page,
    )
