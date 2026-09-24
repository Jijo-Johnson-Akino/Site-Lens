from __future__ import annotations

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, make_check


def run(ctx: SeoContext) -> list[CheckResult]:
    html = ctx.html
    page = ctx.final_url or ctx.page_url
    return [_language(html.get("language"), page), _viewport(html.get("viewport"), page), _favicon(bool(html.get("favicon_declared")), page)]


def _language(language: str | None, page: str) -> CheckResult:
    why = "The html lang attribute helps browsers, assistive technology, and crawlers identify the page language."
    if language:
        return make_check(
            check_id="SEO-HTML-001",
            name="Language attribute",
            group="technical",
            status="pass",
            severity="medium",
            message="The html element declares a language.",
            why=why,
            detected=language,
            page_url=page,
        )
    return make_check(
        check_id="SEO-HTML-001",
        name="Language attribute",
        group="technical",
        status="fail",
        severity="medium",
        message="The html element does not declare a lang attribute.",
        recommendation="Add a lang attribute on the html element, for example lang=\"en\".",
        why=why,
        detected="No lang attribute.",
        page_url=page,
    )


def _viewport(viewport: str | None, page: str) -> CheckResult:
    why = "A viewport meta tag is primarily a mobile/technical concern. It can still affect how the page is presented on small screens."
    if viewport:
        return make_check(
            check_id="SEO-HTML-002",
            name="Viewport",
            group="technical",
            status="pass",
            severity="low",
            message="A viewport meta tag is present.",
            why=why,
            detected=viewport,
            page_url=page,
        )
    return make_check(
        check_id="SEO-HTML-002",
        name="Viewport",
        group="technical",
        status="warning",
        severity="low",
        message="No viewport meta tag was found.",
        recommendation="Add a viewport meta tag if the page is intended to be usable on mobile devices.",
        why=why,
        detected="No <meta name=\"viewport\"> element.",
        page_url=page,
    )


def _favicon(declared: bool, page: str) -> CheckResult:
    why = "A declared favicon helps browsers and some search surfaces identify the site. This check does not request /favicon.ico."
    if declared:
        return make_check(
            check_id="SEO-HTML-003",
            name="Favicon",
            group="technical",
            status="pass",
            severity="low",
            message="A favicon is declared in the HTML.",
            why=why,
            page_url=page,
        )
    return make_check(
        check_id="SEO-HTML-003",
        name="Favicon",
        group="technical",
        status="warning",
        severity="low",
        message="No favicon link was declared in the HTML. A request to /favicon.ico was not made in this phase.",
        recommendation="Declare a favicon with a rel=icon link if you want a consistent site icon.",
        why=why,
        detected="No rel=icon / shortcut icon / apple-touch-icon link.",
        page_url=page,
    )
