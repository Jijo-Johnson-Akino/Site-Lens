from __future__ import annotations

from urllib.parse import urljoin, urlparse

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, make_check


def run(ctx: SeoContext) -> list[CheckResult]:
    page = ctx.final_url or ctx.page_url
    canonical = ctx.html.get("canonical")
    raw = canonical.strip() if isinstance(canonical, str) else ""
    exists = _exists(raw, page)
    validity = _validity(raw, page)
    consistency = _consistency(raw, ctx.final_url, page)
    return [exists, validity, consistency]


def _exists(raw: str, page: str) -> CheckResult:
    why = "A canonical URL tells search engines which URL should be treated as the primary version of the page."
    if not raw:
        return make_check(
            check_id="SEO-CAN-001",
            name="Canonical exists",
            group="canonical",
            status="fail",
            severity="high",
            message="No canonical link was found.",
            recommendation="Add a <link rel=\"canonical\"> element that points to the preferred URL for this page.",
            why=why,
            detected="No rel=canonical link was found.",
            page_url=page,
        )
    return make_check(
        check_id="SEO-CAN-001",
        name="Canonical exists",
        group="canonical",
        status="pass",
        severity="high",
        message="The page contains a canonical link.",
        why=why,
        detected=raw,
        page_url=page,
    )


def _validity(raw: str, page: str) -> CheckResult:
    why = "Canonical URLs should resolve to a well-formed http(s) location so crawlers can interpret them."
    if not raw:
        return make_check(
            check_id="SEO-CAN-002",
            name="Canonical URL validity",
            group="canonical",
            status="not_applicable",
            severity="high",
            message="Canonical URL validity was not evaluated because no canonical was found.",
            page_url=page,
        )
    parsed = urlparse(raw)
    if " " in raw or raw in {":", "/", "//"}:
        return make_check(
            check_id="SEO-CAN-002",
            name="Canonical URL validity",
            group="canonical",
            status="fail",
            severity="high",
            message="The canonical URL appears malformed.",
            recommendation="Use a well-formed absolute URL, typically with an https scheme and hostname.",
            why=why,
            detected=raw,
            page_url=page,
        )
    if not parsed.scheme:
        return make_check(
            check_id="SEO-CAN-002",
            name="Canonical URL validity",
            group="canonical",
            status="warning",
            severity="medium",
            message="The canonical URL is relative. Absolute URLs are usually easier for crawlers to interpret.",
            recommendation="Prefer an absolute canonical URL with an https scheme and hostname.",
            why=why,
            detected=raw,
            page_url=page,
        )
    if parsed.scheme not in {"http", "https"}:
        return make_check(
            check_id="SEO-CAN-002",
            name="Canonical URL validity",
            group="canonical",
            status="fail",
            severity="high",
            message="The canonical URL does not use an http or https scheme.",
            recommendation="Use an https URL as the canonical address.",
            why=why,
            detected=raw,
            page_url=page,
        )
    if not parsed.hostname:
        return make_check(
            check_id="SEO-CAN-002",
            name="Canonical URL validity",
            group="canonical",
            status="fail",
            severity="high",
            message="The canonical URL is missing a hostname.",
            recommendation="Include a valid hostname in the canonical URL.",
            why=why,
            detected=raw,
            page_url=page,
        )
    return make_check(
        check_id="SEO-CAN-002",
        name="Canonical URL validity",
        group="canonical",
        status="pass",
        severity="high",
        message="The canonical URL is a well-formed absolute URL.",
        why=why,
        detected=raw,
        page_url=page,
    )


def _normalize(url: str) -> tuple[str, str, str]:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return parsed.scheme.lower(), host, path


def _consistency(raw: str, final_url: str, page: str) -> CheckResult:
    why = "A canonical that points to a different host or path than the final URL can be intentional, but unexpected mismatches are worth reviewing."
    if not raw:
        return make_check(
            check_id="SEO-CAN-003",
            name="Canonical consistency",
            group="canonical",
            status="not_applicable",
            severity="medium",
            message="Canonical consistency was not evaluated because no canonical was found.",
            page_url=page,
        )
    absolute = urljoin(final_url, raw)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return make_check(
            check_id="SEO-CAN-003",
            name="Canonical consistency",
            group="canonical",
            status="not_applicable",
            severity="medium",
            message="Canonical consistency was not evaluated because the canonical URL is not a usable http(s) address.",
            page_url=page,
        )
    if _normalize(absolute) == _normalize(final_url):
        return make_check(
            check_id="SEO-CAN-003",
            name="Canonical consistency",
            group="canonical",
            status="pass",
            severity="medium",
            message="The canonical URL matches the final page URL.",
            why=why,
            detected=f"canonical={absolute}; final={final_url}",
            page_url=page,
        )
    return make_check(
        check_id="SEO-CAN-003",
        name="Canonical consistency",
        group="canonical",
        status="warning",
        severity="medium",
        message="The canonical URL does not match the final page URL. This can be intentional, but it is worth confirming.",
        recommendation="Confirm that the canonical target is the preferred version of this page.",
        why=why,
        detected=f"canonical={absolute}; final={final_url}",
        page_url=page,
    )
