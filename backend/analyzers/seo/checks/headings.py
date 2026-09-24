from __future__ import annotations

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, make_check


def run(ctx: SeoContext) -> list[CheckResult]:
    html = ctx.html
    page = ctx.final_url or ctx.page_url
    h1s = html.get("h1s") or []
    outline = html.get("heading_outline") or []
    h2_count = int(html.get("h2_count") or 0)
    return [
        _h1_exists(h1s, page),
        _multiple_h1(h1s, page),
        _empty_h1(h1s, page),
        _h2_structure(h2_count, page),
        _hierarchy(outline, page),
    ]


def _h1_exists(h1s: list[dict], page: str) -> CheckResult:
    why = "An H1 heading helps people and crawlers understand the main topic of the page."
    filled = [item for item in h1s if not item.get("empty")]
    if not filled:
        return make_check(
            check_id="SEO-H1-001",
            name="H1 exists",
            group="headings",
            status="fail",
            severity="high",
            message="The page does not contain a non-empty H1 heading.",
            recommendation="Add one clear H1 that describes the main topic of the page.",
            why=why,
            detected="No non-empty H1 elements were found.",
            page_url=page,
        )
    return make_check(
        check_id="SEO-H1-001",
        name="H1 exists",
        group="headings",
        status="pass",
        severity="high",
        message="The page contains an H1 heading.",
        why=why,
        detected=filled[0].get("text"),
        page_url=page,
    )


def _multiple_h1(h1s: list[dict], page: str) -> CheckResult:
    count = len(h1s)
    why = "HTML allows more than one H1. Multiple H1s are not automatically an SEO failure, but the page hierarchy should stay clear."
    if count > 1:
        texts = ", ".join((item.get("text") or "(empty)") for item in h1s[:5])
        return make_check(
            check_id="SEO-H1-002",
            name="Multiple H1 elements",
            group="headings",
            status="warning",
            severity="medium",
            message="Multiple H1 elements were detected. Review whether they represent a clear page hierarchy.",
            recommendation="Review the heading structure so the main topic of the page is obvious.",
            why=why,
            detected=f"{count} H1 elements: {texts}",
            page_url=page,
        )
    return make_check(
        check_id="SEO-H1-002",
        name="Multiple H1 elements",
        group="headings",
        status="pass",
        severity="medium",
        message="The page does not contain multiple H1 elements.",
        why=why,
        detected=f"{count} H1 element(s).",
        page_url=page,
    )


def _empty_h1(h1s: list[dict], page: str) -> CheckResult:
    if not h1s:
        return make_check(
            check_id="SEO-H1-003",
            name="Empty H1",
            group="headings",
            status="not_applicable",
            severity="medium",
            message="Empty H1 elements were not evaluated because no H1 was found.",
            page_url=page,
        )
    empty = [item for item in h1s if item.get("empty")]
    if empty:
        return make_check(
            check_id="SEO-H1-003",
            name="Empty H1",
            group="headings",
            status="fail",
            severity="medium",
            message="One or more H1 elements are empty.",
            recommendation="Give each H1 visible text that describes the section or page.",
            why="Empty headings add structure without communicating a topic.",
            detected=f"{len(empty)} empty H1 element(s).",
            page_url=page,
        )
    return make_check(
        check_id="SEO-H1-003",
        name="Empty H1",
        group="headings",
        status="pass",
        severity="medium",
        message="H1 elements contain text.",
        why="Empty headings add structure without communicating a topic.",
        page_url=page,
    )


def _h2_structure(h2_count: int, page: str) -> CheckResult:
    why = "H2 headings are a useful way to organize sections. Pages without H2s are not automatically failing SEO."
    if h2_count == 0:
        return make_check(
            check_id="SEO-H2-001",
            name="H2 structure",
            group="headings",
            status="warning",
            severity="info",
            message="No H2 headings were found. This is an observation, not an automatic failure.",
            recommendation="Consider using H2 headings if the page has distinct sections.",
            why=why,
            detected="0 H2 elements.",
            page_url=page,
        )
    return make_check(
        check_id="SEO-H2-001",
        name="H2 structure",
        group="headings",
        status="pass",
        severity="info",
        message="The page contains H2 headings.",
        why=why,
        detected=f"{h2_count} H2 element(s).",
        page_url=page,
    )


def _hierarchy(outline: list[int], page: str) -> CheckResult:
    why = "Large heading jumps (for example H1 to H4) can make the page outline harder to follow. Minor skips are not treated as SEO failures."
    jumps = []
    previous = None
    for level in outline:
        if previous is not None and level - previous >= 2:
            jumps.append(f"H{previous} → H{level}")
        previous = level
    if jumps:
        return make_check(
            check_id="SEO-HEAD-001",
            name="Heading hierarchy",
            group="headings",
            status="warning",
            severity="low",
            message="The heading outline skips intermediate levels in a way that may be harder to follow.",
            recommendation="Review whether the heading levels match the visual structure of the page.",
            why=why,
            detected="; ".join(jumps),
            page_url=page,
        )
    return make_check(
        check_id="SEO-HEAD-001",
        name="Heading hierarchy",
        group="headings",
        status="pass",
        severity="low",
        message="No large heading-level jumps were detected.",
        why=why,
        detected=", ".join(f"H{level}" for level in outline) or "No headings.",
        page_url=page,
    )
