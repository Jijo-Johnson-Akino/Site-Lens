from __future__ import annotations

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, make_check


def run(ctx: SeoContext) -> list[CheckResult]:
    page = ctx.final_url or ctx.page_url
    probe = ctx.sitemap or {}
    exists = bool(probe.get("exists"))
    status = probe.get("status_code")
    body = probe.get("body") if isinstance(probe.get("body"), str) else None
    return [_exists(exists, status, page), _accessible(exists, status, page), _format(exists, body, page)]


def _exists(exists: bool, status: int | None, page: str) -> CheckResult:
    why = "A sitemap can help crawlers discover URLs. This check only looks at /sitemap.xml from the scan engine."
    if exists:
        return make_check(
            check_id="SEO-SITEMAP-001",
            name="Sitemap exists",
            group="robots_sitemap",
            status="pass",
            severity="medium",
            message="A sitemap.xml response was found at the site origin.",
            why=why,
            detected=f"HTTP {status}",
            page_url=page,
        )
    return make_check(
        check_id="SEO-SITEMAP-001",
        name="Sitemap exists",
        group="robots_sitemap",
        status="fail",
        severity="medium",
        message="No sitemap.xml file was found at the site origin.",
        recommendation="Publish a sitemap if you want to help crawlers discover URLs. The sitemap may still exist at another path declared in robots.txt.",
        why=why,
        detected=f"HTTP {status}" if status is not None else "Request failed.",
        page_url=page,
    )


def _accessible(exists: bool, status: int | None, page: str) -> CheckResult:
    why = "A sitemap is only useful to crawlers if it is reachable."
    if status is None:
        return make_check(
            check_id="SEO-SITEMAP-002",
            name="Sitemap accessible",
            group="robots_sitemap",
            status="fail",
            severity="medium",
            message="sitemap.xml could not be requested.",
            why=why,
            detected="No HTTP status.",
            page_url=page,
        )
    if exists and status == 200:
        return make_check(
            check_id="SEO-SITEMAP-002",
            name="Sitemap accessible",
            group="robots_sitemap",
            status="pass",
            severity="medium",
            message="sitemap.xml returned HTTP 200.",
            why=why,
            detected="HTTP 200",
            page_url=page,
        )
    if status >= 500 or status in {401, 403}:
        return make_check(
            check_id="SEO-SITEMAP-002",
            name="Sitemap accessible",
            group="robots_sitemap",
            status="warning",
            severity="medium",
            message="sitemap.xml was not successfully readable.",
            why=why,
            detected=f"HTTP {status}",
            page_url=page,
        )
    return make_check(
        check_id="SEO-SITEMAP-002",
        name="Sitemap accessible",
        group="robots_sitemap",
        status="not_applicable",
        severity="medium",
        message="Accessibility is already reflected by the missing sitemap result.",
        detected=f"HTTP {status}",
        page_url=page,
    )


def _format(exists: bool, body: str | None, page: str) -> CheckResult:
    why = "This is a lightweight XML sniff, not a full sitemap crawl."
    if not exists or body is None:
        return make_check(
            check_id="SEO-SITEMAP-003",
            name="Sitemap format",
            group="robots_sitemap",
            status="not_applicable",
            severity="low",
            message="Sitemap format was not evaluated because the file was not retrieved.",
            page_url=page,
        )
    lowered = body.strip().lower()
    if not lowered:
        return make_check(
            check_id="SEO-SITEMAP-003",
            name="Sitemap format",
            group="robots_sitemap",
            status="fail",
            severity="medium",
            message="The sitemap response was empty.",
            why=why,
            detected="Empty body.",
            page_url=page,
        )
    if "<html" in lowered or "<!doctype html" in lowered:
        return make_check(
            check_id="SEO-SITEMAP-003",
            name="Sitemap format",
            group="robots_sitemap",
            status="fail",
            severity="medium",
            message="sitemap.xml appears to contain HTML instead of sitemap XML.",
            recommendation="Serve a sitemap document (urlset or sitemapindex), not an HTML page.",
            why=why,
            detected="HTML markup was detected in the response body.",
            page_url=page,
        )
    if "<urlset" in lowered or "<sitemapindex" in lowered:
        return make_check(
            check_id="SEO-SITEMAP-003",
            name="Sitemap format",
            group="robots_sitemap",
            status="pass",
            severity="low",
            message="The response looks like XML sitemap content.",
            why=why,
            page_url=page,
        )
    return make_check(
        check_id="SEO-SITEMAP-003",
        name="Sitemap format",
        group="robots_sitemap",
        status="warning",
        severity="low",
        message="The sitemap response does not look like a standard XML sitemap.",
        recommendation="Use a urlset or sitemapindex document if this URL is meant to be a sitemap.",
        why=why,
        page_url=page,
    )
