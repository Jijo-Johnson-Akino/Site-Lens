from __future__ import annotations

from backend.analyzers.trust.checks._util import (
    names_consistent,
    page_authors,
    page_dates,
    page_schema_authors,
    site_page_id,
    site_url,
    trust_check,
)
from backend.analyzers.trust.config import ARTICLE_PAGE_TYPES
from backend.analyzers.trust.context import PageTrustContext, SiteTrustContext


def run_site(site: SiteTrustContext):
    if not site.has_articles:
        return [
            trust_check(
                check_id="trust.authorship.author.missing",
                name="Article authorship",
                group="authorship",
                status="not_applicable",
                severity="info",
                message="No article pages were detected in the crawled set, so authorship checks were not applied.",
                page_url=site_url(site),
                page_id=site_page_id(site),
            )
        ]
    return []


def run_page(ctx: PageTrustContext):
    if ctx.page_type not in ARTICLE_PAGE_TYPES:
        return []
    checks = []
    authors = page_authors(ctx)
    schema_authors = page_schema_authors(ctx)
    dates = page_dates(ctx)
    if authors:
        checks.append(
            trust_check(
                check_id="trust.authorship.author.missing",
                name="Author information",
                group="authorship",
                status="pass",
                severity="info",
                message="Author information detected.",
                page_url=ctx.url,
                page_id=ctx.page.id,
                detected=authors[0],
                evidence={"authors": authors[:4], "schema_authors": schema_authors[:4]},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.authorship.author.missing",
                name="Author information",
                group="authorship",
                status="warning",
                severity="low",
                message="Author information was not detected on this article page.",
                page_url=ctx.url,
                page_id=ctx.page.id,
                recommendation="Add a visible author name and, where applicable, Person structured data.",
                why="Authorship is reported from visible bylines and reused structured-data/content signals. Missing detection is not a judgment of the article's accuracy.",
            )
        )

    if dates:
        latest = dates[0]
        checks.append(
            trust_check(
                check_id="trust.authorship.date.missing",
                name="Publication date",
                group="authorship",
                status="pass",
                severity="info",
                message=f"Publication or update date detected: {latest}.",
                page_url=ctx.url,
                page_id=ctx.page.id,
                detected=latest,
                evidence={"dates": dates[:6]},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.authorship.date.missing",
                name="Publication date",
                group="authorship",
                status="warning",
                severity="low",
                message="No publication or modification date was detected on this article page.",
                page_url=ctx.url,
                page_id=ctx.page.id,
                recommendation="Add a visible publication or last-updated date on article pages.",
            )
        )

    visible = authors[0] if authors else None
    schema = schema_authors[0] if schema_authors else None
    overlap = names_consistent(visible, schema)
    if overlap is True:
        checks.append(
            trust_check(
                check_id="trust.authorship.inconsistent",
                name="Author consistency",
                group="authorship",
                status="pass",
                severity="info",
                message="Visible author and schema author are consistent.",
                page_url=ctx.url,
                page_id=ctx.page.id,
                detected=visible,
                evidence={"visible": visible, "schema": schema},
            )
        )
        checks.append(
            trust_check(
                check_id="trust.consistency.author_information",
                name="Author information consistency",
                group="consistency",
                status="pass",
                severity="info",
                message="Visible author and schema author are consistent.",
                page_url=ctx.url,
                page_id=ctx.page.id,
                detected=visible,
                evidence={"visible": visible, "schema": schema},
            )
        )
    elif overlap is False:
        checks.append(
            trust_check(
                check_id="trust.authorship.inconsistent",
                name="Author consistency",
                group="authorship",
                status="warning",
                severity="low",
                message="Potential author information inconsistency detected.",
                page_url=ctx.url,
                page_id=ctx.page.id,
                recommendation="Review the visible byline and author structured data so they refer to the same published name.",
                why="SiteLens compared observable strings. It does not determine which value is correct or whether identity fraud occurred.",
                evidence={"visible": visible, "schema": schema},
            )
        )
        checks.append(
            trust_check(
                check_id="trust.consistency.author_information",
                name="Author information consistency",
                group="consistency",
                status="warning",
                severity="low",
                message="Potential author information inconsistency detected.",
                page_url=ctx.url,
                page_id=ctx.page.id,
                evidence={"visible": visible, "schema": schema},
            )
        )
    else:
        checks.append(
            trust_check(
                check_id="trust.authorship.inconsistent",
                name="Author consistency",
                group="authorship",
                status="not_applicable",
                severity="info",
                message="Author consistency could not be compared because visible author or schema author was unavailable.",
                page_url=ctx.url,
                page_id=ctx.page.id,
            )
        )

    citations = (ctx.signals.get("transparency") or {}).get("citations")
    if citations:
        checks.append(
            trust_check(
                check_id="trust.authorship.citation.detected",
                name="Content credibility signals",
                group="authorship",
                status="pass",
                severity="info",
                message="Reference, source, or editorial signals detected.",
                page_url=ctx.url,
                page_id=ctx.page.id,
            )
        )
    return checks
