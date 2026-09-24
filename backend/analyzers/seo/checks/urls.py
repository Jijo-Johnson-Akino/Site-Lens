from __future__ import annotations

from urllib.parse import parse_qsl, urlparse, unquote

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, make_check


def run(ctx: SeoContext) -> list[CheckResult]:
    page = ctx.final_url or ctx.page_url
    parsed = urlparse(page)
    return [_https(parsed, page), _readability(parsed, page), _fragments(parsed, page)]


def _https(parsed, page: str) -> CheckResult:
    why = "HTTPS protects the connection between the browser and the site. Search engines treat it as a basic technical signal."
    if parsed.scheme == "https":
        return make_check(
            check_id="SEO-URL-001",
            name="HTTPS",
            group="technical",
            status="pass",
            severity="critical",
            message="The final URL uses HTTPS.",
            why=why,
            detected=page,
            page_url=page,
        )
    return make_check(
        check_id="SEO-URL-001",
        name="HTTPS",
        group="technical",
        status="fail",
        severity="critical",
        message="The final URL does not use HTTPS.",
        recommendation="Serve the page over HTTPS.",
        why=why,
        detected=page,
        page_url=page,
    )


def _readability(parsed, page: str) -> CheckResult:
    why = "Readable URLs are easier for people to interpret. There is no single required URL length."
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    encoded = page.count("%")
    decoded_path = unquote(parsed.path or "")
    issues: list[str] = []
    if len(page) > 180:
        issues.append("very long URL")
    if len(query_params) >= 5:
        issues.append("excessive query parameters")
    if encoded >= 4 and decoded_path != (parsed.path or ""):
        issues.append("heavily encoded path")
    if issues:
        return make_check(
            check_id="SEO-URL-002",
            name="URL readability",
            group="technical",
            status="warning",
            severity="low",
            message="The URL has patterns that may be harder for people to read.",
            recommendation="Consider a shorter, more descriptive path where it is practical. This is not a ranking requirement.",
            why=why,
            detected=", ".join(issues) + f" ({len(page)} characters, {len(query_params)} query parameter(s)).",
            page_url=page,
        )
    return make_check(
        check_id="SEO-URL-002",
        name="URL readability",
        group="technical",
        status="pass",
        severity="low",
        message="The URL does not show obviously unreadable patterns.",
        why=why,
        detected=f"{len(page)} characters, {len(query_params)} query parameter(s).",
        page_url=page,
    )


def _fragments(parsed, page: str) -> CheckResult:
    why = "URL fragments are not sent to the server and usually do not identify a distinct indexable URL."
    if parsed.fragment:
        return make_check(
            check_id="SEO-URL-003",
            name="URL fragments",
            group="technical",
            status="warning",
            severity="low",
            message="The final URL includes a fragment identifier.",
            recommendation="Use a fragment-free URL as the canonical address unless the fragment is required for in-page navigation only.",
            why=why,
            detected=f"#{parsed.fragment}",
            page_url=page,
        )
    return make_check(
        check_id="SEO-URL-003",
        name="URL fragments",
        group="technical",
        status="pass",
        severity="low",
        message="The final URL does not include a fragment identifier.",
        why=why,
        page_url=page,
    )
