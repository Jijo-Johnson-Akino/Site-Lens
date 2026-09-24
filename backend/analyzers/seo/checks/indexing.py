from __future__ import annotations

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, Indexability, make_check


def run(ctx: SeoContext) -> list[CheckResult]:
    page = ctx.final_url or ctx.page_url
    robots = ctx.html.get("robots_meta")
    header = ctx.x_robots_tag
    meta = _robots_meta(robots, bool(ctx.html.get("robots_meta_present")), page)
    xrobots = _x_robots(header, page)
    summary = _summary(robots, header, page)
    return [meta, xrobots, summary]


def indexability_of(ctx: SeoContext) -> Indexability:
    reason = _block_reason(ctx.html.get("robots_meta"), ctx.x_robots_tag)
    if reason:
        return Indexability(indexable=False, reason=reason)
    return Indexability(indexable=True, reason=None)


def _tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {part.strip().lower() for part in value.replace(";", ",").split(",") if part.strip()}


def _block_reason(robots_meta: str | None, x_robots: str | None) -> str | None:
    tokens = _tokens(robots_meta) | _tokens(x_robots)
    if "none" in tokens or "noindex" in tokens:
        return "noindex directive detected"
    return None


def _robots_meta(robots: str | None, present: bool, page: str) -> CheckResult:
    why = "A robots meta tag can allow or prevent indexing. noindex is sometimes intentional and is not automatically a bug."
    if not present:
        return make_check(
            check_id="SEO-INDEX-001",
            name="Robots meta",
            group="indexability",
            status="pass",
            severity="high",
            message="No robots meta tag was found. Crawlers typically treat the page as indexable unless another directive says otherwise.",
            why=why,
            detected="No <meta name=\"robots\"> element.",
            page_url=page,
        )
    tokens = _tokens(robots)
    if "noindex" in tokens or "none" in tokens:
        return make_check(
            check_id="SEO-INDEX-001",
            name="Robots meta",
            group="indexability",
            status="warning",
            severity="high",
            message="Page contains a noindex directive.",
            recommendation="Keep noindex only if this page should stay out of search results.",
            why=why,
            detected=robots,
            page_url=page,
        )
    if "nofollow" in tokens:
        return make_check(
            check_id="SEO-INDEX-001",
            name="Robots meta",
            group="indexability",
            status="warning",
            severity="medium",
            message="The robots meta tag contains nofollow.",
            recommendation="Use nofollow only if links on this page should not be followed by crawlers.",
            why=why,
            detected=robots,
            page_url=page,
        )
    return make_check(
        check_id="SEO-INDEX-001",
        name="Robots meta",
        group="indexability",
        status="pass",
        severity="high",
        message="The robots meta tag does not include noindex.",
        why=why,
        detected=robots,
        page_url=page,
    )


def _x_robots(header: str | None, page: str) -> CheckResult:
    why = "X-Robots-Tag in the HTTP response can allow or prevent indexing independently of the HTML."
    if not header:
        return make_check(
            check_id="SEO-INDEX-002",
            name="X-Robots-Tag",
            group="indexability",
            status="pass",
            severity="high",
            message="No X-Robots-Tag header was present.",
            why=why,
            detected="Header absent.",
            page_url=page,
        )
    tokens = _tokens(header)
    flagged = [token for token in ("noindex", "nofollow", "none") if token in tokens]
    if flagged:
        return make_check(
            check_id="SEO-INDEX-002",
            name="X-Robots-Tag",
            group="indexability",
            status="warning",
            severity="high",
            message="The X-Robots-Tag header contains a restrictive directive.",
            recommendation="Keep these directives only if they match the intended indexing policy.",
            why=why,
            detected=header,
            page_url=page,
        )
    return make_check(
        check_id="SEO-INDEX-002",
        name="X-Robots-Tag",
        group="indexability",
        status="pass",
        severity="high",
        message="The X-Robots-Tag header does not include noindex, nofollow, or none.",
        why=why,
        detected=header,
        page_url=page,
    )


def _summary(robots: str | None, header: str | None, page: str) -> CheckResult:
    reason = _block_reason(robots, header)
    if reason:
        return make_check(
            check_id="SEO-INDEX-003",
            name="Indexability summary",
            group="indexability",
            status="warning",
            severity="high",
            message="This page currently looks non-indexable.",
            recommendation="Confirm that blocking indexing is intentional for this URL.",
            why="Indexability is inferred from robots meta and X-Robots-Tag directives collected during the scan.",
            detected=reason,
            page_url=page,
        )
    return make_check(
        check_id="SEO-INDEX-003",
        name="Indexability summary",
        group="indexability",
        status="pass",
        severity="high",
        message="No noindex directive was detected on this page.",
        why="Indexability is inferred from robots meta and X-Robots-Tag directives collected during the scan.",
        detected="indexable",
        page_url=page,
    )
