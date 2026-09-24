from __future__ import annotations

from backend.analyzers.trust.checks._util import site_page_id, site_url, trust_check
from backend.analyzers.trust.context import SiteTrustContext


def run_site(site: SiteTrustContext):
    url = site_url(site)
    page_id = site_page_id(site)
    if site.about_pages:
        page = site.about_pages[0]
        return [
            trust_check(
                check_id="trust.about.page.missing",
                name="About page",
                group="transparency",
                status="pass",
                severity="info",
                message="About page detected within the crawled pages.",
                page_url=page.get("url") or url,
                page_id=page.get("page_id") or page_id,
                detected=page.get("url"),
                evidence={"pages": [item.get("url") for item in site.about_pages[:6]]},
            )
        ]
    if site.about_links:
        return [
            trust_check(
                check_id="trust.about.page.missing",
                name="About page",
                group="transparency",
                status="pass",
                severity="info",
                message="About link detected. The destination was not present among the crawled pages.",
                page_url=url,
                page_id=page_id,
                detected=site.about_links[0].get("href"),
                evidence={"links": site.about_links[:6]},
            )
        ]
    return [
        trust_check(
            check_id="trust.about.page.missing",
            name="About page",
            group="transparency",
            status="warning",
            severity="low",
            message="No dedicated About page was detected within the crawled pages.",
            page_url=url,
            page_id=page_id,
            recommendation="Add a crawlable About, Company, or Our Story page if that information is intended to be public.",
            why="About-page detection is limited to URLs, titles, and page types observed in the crawl.",
        )
    ]
