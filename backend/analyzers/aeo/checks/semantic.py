from __future__ import annotations

from backend.analyzers.aeo.checks._util import looks_like_article, page_url, types_present
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, make_check
from backend.parser.structured_data import ARTICLE_TYPES

SEMANTIC_NAMES = ("header", "nav", "main", "article", "section", "aside", "footer")


def run(ctx: AeoContext) -> list[CheckResult]:
    page = page_url(ctx)
    semantic = ctx.html.get("semantic") or {}
    return [_semantic_use(semantic, page), _main(ctx, page), _article(ctx, page)]


def _semantic_use(semantic: dict, page: str) -> CheckResult:
    why = "Landmark elements (header, nav, main, article, section, aside, footer) can improve machine interpretability. This check is weighted lightly."
    present = [name for name in SEMANTIC_NAMES if int(semantic.get(name) or 0) > 0]
    detected = ", ".join(f"{name}={semantic.get(name, 0)}" for name in SEMANTIC_NAMES)
    if len(present) >= 3:
        return make_check(
            check_id="AEO-SEM-001",
            name="Semantic HTML landmarks",
            group="semantic_structure",
            status="pass",
            severity="low",
            message="The page uses several semantic landmark elements.",
            why=why,
            detected=detected,
            page_url=page,
        )
    if present:
        return make_check(
            check_id="AEO-SEM-001",
            name="Semantic HTML landmarks",
            group="semantic_structure",
            status="warning",
            severity="low",
            message="Only a few semantic landmark elements were found.",
            recommendation="Use header, nav, main, and footer when they match the visible layout.",
            why=why,
            detected=detected,
            page_url=page,
        )
    return make_check(
        check_id="AEO-SEM-001",
        name="Semantic HTML landmarks",
        group="semantic_structure",
        status="warning",
        severity="low",
        message="No header, nav, main, article, section, aside, or footer elements were found.",
        recommendation="Add landmark elements that match the page layout. This is a structure signal, not a ranking claim.",
        why=why,
        detected=detected,
        page_url=page,
    )


def _main(ctx: AeoContext, page: str) -> CheckResult:
    why = "A main landmark (or an equivalent role/id) identifies the primary content region."
    if ctx.html.get("has_main_landmark"):
        return make_check(
            check_id="AEO-SEM-002",
            name="Main content landmark",
            group="semantic_structure",
            status="pass",
            severity="medium",
            message="A main content landmark was detected.",
            why=why,
            detected="<main>, role=main, or a common main/content id.",
            page_url=page,
        )
    return make_check(
        check_id="AEO-SEM-002",
        name="Main content landmark",
        group="semantic_structure",
        status="warning",
        severity="medium",
        message="No <main> element or equivalent main-content landmark was found.",
        recommendation="Wrap primary copy in a <main> element.",
        why=why,
        page_url=page,
    )


def _article(ctx: AeoContext, page: str) -> CheckResult:
    why = "Article markup or Article/BlogPosting schema is useful for pages that actually present an article. Homepages are not failed for omitting it."
    semantic = ctx.html.get("semantic") or {}
    has_article = int(semantic.get("article") or 0) > 0 or bool(ARTICLE_TYPES.intersection(types_present(ctx)))
    if not looks_like_article(ctx):
        return make_check(
            check_id="AEO-SEM-003",
            name="Article content",
            group="semantic_structure",
            status="not_applicable",
            severity="low",
            message="Article markup was not required because this page does not look like an article or post.",
            why=why,
            page_url=page,
        )
    if has_article:
        return make_check(
            check_id="AEO-SEM-003",
            name="Article content",
            group="semantic_structure",
            status="pass",
            severity="low",
            message="Article markup or article structured data is present.",
            why=why,
            page_url=page,
        )
    return make_check(
        check_id="AEO-SEM-003",
        name="Article content",
        group="semantic_structure",
        status="warning",
        severity="low",
        message="The page looks like an article, but no <article> element or Article schema was found.",
        recommendation="Wrap the post in <article> and/or add Article JSON-LD.",
        why=why,
        page_url=page,
    )
