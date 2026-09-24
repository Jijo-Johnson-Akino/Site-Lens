from __future__ import annotations

from urllib.parse import urljoin, urlparse

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, make_check

WEAK_TEXT = {"click here", "read more", "here", "link", "more", "learn more", "click"}


def run(ctx: SeoContext) -> list[CheckResult]:
    page = ctx.final_url or ctx.page_url
    anchors = ctx.html.get("links") or []
    classified = [_classify(anchor, page) for anchor in anchors]
    return [
        _internal(classified, page),
        _external(classified, page),
        _empty(classified, page),
        _fragments(classified, page),
        _descriptive(classified, page),
    ]


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _classify(anchor: dict, page: str) -> dict:
    href = (anchor.get("href") or "").strip()
    text = " ".join((anchor.get("text") or "").split())
    has_href = bool(anchor.get("has_href"))
    kind = "other"
    if not has_href or href == "" or href.lower().startswith(("javascript:", "data:")):
        kind = "empty"
    elif href == "#" or href.startswith("#"):
        kind = "fragment"
    elif href.lower().startswith(("mailto:", "tel:")):
        kind = "other"
    else:
        absolute = urljoin(page, href)
        parsed = urlparse(absolute)
        if parsed.scheme in {"http", "https"} and parsed.hostname:
            kind = "internal" if _host(absolute) == _host(page) else "external"
        else:
            kind = "empty"
    return {"kind": kind, "href": href, "text": text}


def _internal(classified: list[dict], page: str) -> CheckResult:
    count = sum(1 for item in classified if item["kind"] == "internal")
    why = "Internal links help people and crawlers move between pages on the same site."
    if count == 0:
        return make_check(
            check_id="SEO-LINK-001",
            name="Internal links",
            group="links",
            status="warning",
            severity="medium",
            message="No internal links were found on the homepage.",
            recommendation="Link to important pages on the same site where it is useful.",
            why=why,
            detected="0 internal links.",
            page_url=page,
        )
    return make_check(
        check_id="SEO-LINK-001",
        name="Internal links",
        group="links",
        status="pass",
        severity="medium",
        message=f"{count} internal link(s) were found.",
        why=why,
        detected=str(count),
        page_url=page,
    )


def _external(classified: list[dict], page: str) -> CheckResult:
    count = sum(1 for item in classified if item["kind"] == "external")
    why = "External links are neither required nor harmful by themselves. This is a count, not a ranking verdict."
    return make_check(
        check_id="SEO-LINK-002",
        name="External links",
        group="links",
        status="pass",
        severity="info",
        message=f"{count} external link(s) were found.",
        why=why,
        detected=str(count),
        page_url=page,
    )


def _empty(classified: list[dict], page: str) -> CheckResult:
    empty = [item for item in classified if item["kind"] == "empty"]
    why = "Empty or invalid href values do not lead anywhere useful."
    if empty:
        return make_check(
            check_id="SEO-LINK-003",
            name="Empty links",
            group="links",
            status="fail",
            severity="medium",
            message=f"{len(empty)} link(s) have an empty or invalid href.",
            recommendation="Give every link a usable destination, or remove the anchor if it is not a link.",
            why=why,
            detected=f"{len(empty)} empty/invalid href value(s).",
            page_url=page,
        )
    return make_check(
        check_id="SEO-LINK-003",
        name="Empty links",
        group="links",
        status="pass",
        severity="medium",
        message="No empty or invalid href values were found.",
        why=why,
        page_url=page,
    )


def _fragments(classified: list[dict], page: str) -> CheckResult:
    fragments = [item for item in classified if item["kind"] == "fragment"]
    why = "Fragment-only links such as href=\"#\" often act as placeholders rather than real destinations."
    if fragments:
        return make_check(
            check_id="SEO-LINK-004",
            name="Fragment-only links",
            group="links",
            status="warning",
            severity="low",
            message=f"{len(fragments)} fragment-only link(s) were found.",
            recommendation="Point placeholder links to real destinations, or use a button if the control is not navigation.",
            why=why,
            detected=f"{len(fragments)} href=\"#\" (or fragment-only) link(s).",
            page_url=page,
        )
    return make_check(
        check_id="SEO-LINK-004",
        name="Fragment-only links",
        group="links",
        status="pass",
        severity="low",
        message="No fragment-only links were found.",
        why=why,
        page_url=page,
    )


def _descriptive(classified: list[dict], page: str) -> CheckResult:
    weak = [
        item
        for item in classified
        if item["kind"] in {"internal", "external", "fragment"} and item["text"].lower() in WEAK_TEXT
    ]
    why = "Non-descriptive link text such as “click here” is less useful for people and for understanding the destination. This is an observation, not a critical SEO failure."
    if weak:
        samples = ", ".join(sorted({item["text"] for item in weak}))
        return make_check(
            check_id="SEO-LINK-005",
            name="Descriptive link text",
            group="links",
            status="warning",
            severity="low",
            message=f"{len(weak)} link(s) use generic text that does not describe the destination.",
            recommendation="Use link text that names the destination or action. This helps people and is not treated as a ranking penalty here.",
            why=why,
            detected=samples,
            page_url=page,
        )
    return make_check(
        check_id="SEO-LINK-005",
        name="Descriptive link text",
        group="links",
        status="pass",
        severity="low",
        message="No obviously generic link text such as “click here” was found.",
        why=why,
        page_url=page,
    )
