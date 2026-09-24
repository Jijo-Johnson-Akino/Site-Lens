from __future__ import annotations

from backend.analyzers.aeo.checks._util import entities, looks_like_article, page_url, types_present
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, make_check


def run(ctx: AeoContext) -> list[CheckResult]:
    page = page_url(ctx)
    article = looks_like_article(ctx)
    return [_author_visible(ctx, page, article), _author_schema(ctx, page, article), _dates(ctx, page, article)]


def _author_names(ctx: AeoContext) -> list[str]:
    names: list[str] = []
    html = ctx.html
    for key in ("byline", "author_rel"):
        value = html.get(key)
        if value:
            names.append(value)
    for entity in entities(ctx):
        if entity.get("author"):
            names.append(entity["author"])
        if entity.get("creator"):
            names.append(entity["creator"])
        if "Person" in (entity.get("types") or []) and entity.get("name"):
            names.append(entity["name"])
    unique: list[str] = []
    seen: set[str] = set()
    for name in names:
        key = name.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(name.strip())
    return unique


def _author_visible(ctx: AeoContext, page: str, article: bool) -> CheckResult:
    why = "Author names and bylines help machines attribute informational content. Corporate homepages often have no individual author."
    names = _author_names(ctx)
    if names:
        return make_check(
            check_id="AEO-AUTHOR-001",
            name="Author information",
            group="authorship",
            status="pass",
            severity="medium",
            message="Author information is exposed on the page or in structured data.",
            why=why,
            detected=", ".join(names[:4]),
            page_url=page,
        )
    if not article:
        return make_check(
            check_id="AEO-AUTHOR-001",
            name="Author information",
            group="authorship",
            status="warning",
            severity="low",
            message="No author name, byline, or Person schema was found. That is common on corporate homepages.",
            recommendation="Add an author or organization contact if this page presents advice or original analysis.",
            why=why,
            page_url=page,
        )
    return make_check(
        check_id="AEO-AUTHOR-001",
        name="Author information",
        group="authorship",
        status="fail",
        severity="medium",
        message="This looks like an article, but no author information was found.",
        recommendation="Add a visible byline and Person/author structured data.",
        why=why,
        page_url=page,
    )


def _author_schema(ctx: AeoContext, page: str, article: bool) -> CheckResult:
    why = "Person schema or an author/creator property makes provenance machine-readable. It is scored only where it is relevant."
    has_person = "Person" in types_present(ctx)
    has_author_prop = any(entity.get("author") or entity.get("creator") for entity in entities(ctx))
    if has_person or has_author_prop:
        return make_check(
            check_id="AEO-AUTHOR-002",
            name="Author structured data",
            group="authorship",
            status="pass",
            severity="low",
            message="Author or Person structured data is present.",
            why=why,
            detected="Person schema" if has_person else "author/creator property",
            page_url=page,
        )
    if not article:
        return make_check(
            check_id="AEO-AUTHOR-002",
            name="Author structured data",
            group="authorship",
            status="not_applicable",
            severity="low",
            message="Author structured data was not required because this page does not look like an article.",
            why=why,
            page_url=page,
        )
    return make_check(
        check_id="AEO-AUTHOR-002",
        name="Author structured data",
        group="authorship",
        status="warning",
        severity="low",
        message="No Person schema or author/creator property was found on this article-like page.",
        recommendation="Add a Person entity or an author property on the Article object.",
        why=why,
        page_url=page,
    )


def _dates(ctx: AeoContext, page: str, article: bool) -> CheckResult:
    why = "Publication dates help machines understand freshness of informational content. Corporate homepages are not failed for omitting them."
    if not article:
        return make_check(
            check_id="AEO-AUTHOR-003",
            name="Publication date",
            group="authorship",
            status="not_applicable",
            severity="low",
            message="Publication dates were not required because this page does not look like an article.",
            why=why,
            page_url=page,
        )
    published = []
    modified = []
    for entity in entities(ctx):
        if entity.get("datePublished"):
            published.append(entity["datePublished"])
        if entity.get("dateModified"):
            modified.append(entity["dateModified"])
    times = ctx.html.get("time_values") or []
    if published or modified or times:
        bits = []
        if published:
            bits.append(f"datePublished={published[0]}")
        if modified:
            bits.append(f"dateModified={modified[0]}")
        if times and not bits:
            bits.append(f"time={times[0]}")
        return make_check(
            check_id="AEO-AUTHOR-003",
            name="Publication date",
            group="authorship",
            status="pass",
            severity="low",
            message="A publication or modification date was found.",
            why=why,
            detected="; ".join(bits),
            page_url=page,
        )
    return make_check(
        check_id="AEO-AUTHOR-003",
        name="Publication date",
        group="authorship",
        status="warning",
        severity="low",
        message="No datePublished, dateModified, or visible time element was found on this article-like page.",
        recommendation="Include datePublished (and dateModified when the content changes) in Article JSON-LD or a visible <time> element.",
        why=why,
        page_url=page,
    )
