from __future__ import annotations

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, make_check

WEAK_TITLES = {"home", "welcome", "untitled", "page", "index", "new page", "website"}

TITLE_SHORT = 12
TITLE_LONG = 70
META_SHORT = 50
META_LONG = 180


def _url(ctx: SeoContext) -> str:
    return ctx.final_url or ctx.page_url


def run(ctx: SeoContext) -> list[CheckResult]:
    html = ctx.html
    page = _url(ctx)
    title = (html.get("title") or "").strip()
    title_present = bool(html.get("title_present"))
    checks = [_title_exists(title_present, title, page), _title_length(title, page), _duplicate_title(page), _title_quality(title, page)]
    checks.extend(_meta_checks(html, page))
    return checks


def _title_exists(present: bool, title: str, page: str) -> CheckResult:
    if not present or not title:
        why = "A title element is the primary text search engines and browsers use to identify the page."
        if not present:
            message = "The page does not contain a title element."
            detected = "No <title> element was found."
        else:
            message = "The page contains a title element, but it is empty."
            detected = "An empty <title> element was found."
        return make_check(
            check_id="SEO-TITLE-001",
            name="Page title exists",
            group="metadata",
            status="fail",
            severity="critical",
            message=message,
            recommendation="Add a unique and descriptive title element.",
            why=why,
            detected=detected,
            page_url=page,
        )
    return make_check(
        check_id="SEO-TITLE-001",
        name="Page title exists",
        group="metadata",
        status="pass",
        severity="critical",
        message="The page contains a title element.",
        why="A title element is the primary text search engines and browsers use to identify the page.",
        detected=title,
        page_url=page,
    )


def _title_length(title: str, page: str) -> CheckResult:
    if not title:
        return make_check(
            check_id="SEO-TITLE-002",
            name="Title length",
            group="metadata",
            status="not_applicable",
            severity="medium",
            message="Title length was not evaluated because no usable title was found.",
            page_url=page,
        )
    length = len(title)
    detected = f"{length} characters."
    why = "Search results often display roughly 50–60 characters of a title. That is a display guideline, not a ranking rule."
    if length < TITLE_SHORT:
        return make_check(
            check_id="SEO-TITLE-002",
            name="Title length",
            group="metadata",
            status="warning",
            severity="medium",
            message="The title is very short compared with common display guidelines.",
            recommendation="Consider a more descriptive title so the page is easier to identify in search results.",
            why=why,
            detected=detected,
            page_url=page,
        )
    if length > TITLE_LONG:
        return make_check(
            check_id="SEO-TITLE-002",
            name="Title length",
            group="metadata",
            status="warning",
            severity="medium",
            message="The title is very long and may be truncated in search results.",
            recommendation="Consider shortening the title. Display length is a guideline, not a ranking requirement.",
            why=why,
            detected=detected,
            page_url=page,
        )
    return make_check(
        check_id="SEO-TITLE-002",
        name="Title length",
        group="metadata",
        status="pass",
        severity="medium",
        message="The title length is within a commonly used display range.",
        why=why,
        detected=detected,
        page_url=page,
    )


def _duplicate_title(page: str) -> CheckResult:
    return make_check(
        check_id="SEO-TITLE-003",
        name="Duplicate title",
        group="metadata",
        status="not_applicable",
        severity="high",
        message="Duplicate title detection requires comparing multiple crawled pages. This scan analyzed the homepage only.",
        why="Repeated titles across a site can make pages harder to distinguish in search results.",
        page_url=page,
    )


def _title_quality(title: str, page: str) -> CheckResult:
    if not title:
        return make_check(
            check_id="SEO-TITLE-004",
            name="Title quality",
            group="metadata",
            status="not_applicable",
            severity="medium",
            message="Title quality was not evaluated because no usable title was found.",
            page_url=page,
        )
    normalized = " ".join(title.lower().split())
    if normalized in WEAK_TITLES:
        return make_check(
            check_id="SEO-TITLE-004",
            name="Title quality",
            group="metadata",
            status="warning",
            severity="medium",
            message="The title looks generic and may not describe the page well.",
            recommendation="Consider improving the title so it uniquely describes this page. This is a heuristic, not a ranking penalty.",
            why="Very generic titles such as Home or Untitled rarely communicate what the page is about.",
            detected=title,
            page_url=page,
        )
    return make_check(
        check_id="SEO-TITLE-004",
        name="Title quality",
        group="metadata",
        status="pass",
        severity="medium",
        message="The title does not match common generic placeholders.",
        why="Very generic titles such as Home or Untitled rarely communicate what the page is about.",
        detected=title,
        page_url=page,
    )


def _meta_checks(html: dict, page: str) -> list[CheckResult]:
    present = bool(html.get("meta_description_present"))
    description = html.get("meta_description")
    text = (description or "").strip() if isinstance(description, str) else ""
    why = "A meta description can help communicate the page's content in search results. It is not a confirmed ranking factor."
    checks: list[CheckResult] = []

    if not present:
        checks.append(
            make_check(
                check_id="SEO-META-001",
                name="Meta description exists",
                group="metadata",
                status="fail",
                severity="high",
                message="No meta description element was found.",
                recommendation="Add a concise, unique description that accurately summarizes the page.",
                why=why,
                detected="No <meta name=\"description\"> element was found.",
                page_url=page,
            )
        )
    else:
        checks.append(
            make_check(
                check_id="SEO-META-001",
                name="Meta description exists",
                group="metadata",
                status="pass",
                severity="high",
                message="The page contains a meta description element.",
                why=why,
                detected=text or "(empty)",
                page_url=page,
            )
        )

    if not present:
        checks.append(
            make_check(
                check_id="SEO-META-002",
                name="Meta description not empty",
                group="metadata",
                status="not_applicable",
                severity="high",
                message="Emptiness was not evaluated because no meta description element was found.",
                page_url=page,
            )
        )
    elif not text:
        checks.append(
            make_check(
                check_id="SEO-META-002",
                name="Meta description not empty",
                group="metadata",
                status="fail",
                severity="high",
                message="The meta description element is empty or whitespace-only.",
                recommendation="Add a concise, unique description that accurately summarizes the page.",
                why=why,
                detected="The description content was empty.",
                page_url=page,
            )
        )
    else:
        checks.append(
            make_check(
                check_id="SEO-META-002",
                name="Meta description not empty",
                group="metadata",
                status="pass",
                severity="high",
                message="The meta description contains text.",
                why=why,
                detected=text,
                page_url=page,
            )
        )

    if not text:
        checks.append(
            make_check(
                check_id="SEO-META-003",
                name="Meta description length",
                group="metadata",
                status="not_applicable",
                severity="medium",
                message="Description length was not evaluated because no usable description was found.",
                page_url=page,
            )
        )
    else:
        length = len(text)
        detected = f"{length} characters."
        length_why = "Search result snippets are often around 70–160 characters. That range is a display guideline, not a ranking rule."
        if length < META_SHORT or length > META_LONG:
            checks.append(
                make_check(
                    check_id="SEO-META-003",
                    name="Meta description length",
                    group="metadata",
                    status="warning",
                    severity="medium",
                    message="This description is outside the commonly recommended range.",
                    recommendation="Consider revising the description so it summarizes the page clearly. Length is a guideline, not a requirement.",
                    why=length_why,
                    detected=detected,
                    page_url=page,
                )
            )
        else:
            checks.append(
                make_check(
                    check_id="SEO-META-003",
                    name="Meta description length",
                    group="metadata",
                    status="pass",
                    severity="medium",
                    message="The meta description length is within a commonly used display range.",
                    why=length_why,
                    detected=detected,
                    page_url=page,
                )
            )

    checks.append(
        make_check(
            check_id="SEO-META-004",
            name="Duplicate meta description",
            group="metadata",
            status="not_applicable",
            severity="medium",
            message="Duplicate meta description detection requires comparing multiple crawled pages. This scan analyzed the homepage only.",
            why="Repeated descriptions can make snippets less distinctive across a site.",
            page_url=page,
        )
    )
    return checks
