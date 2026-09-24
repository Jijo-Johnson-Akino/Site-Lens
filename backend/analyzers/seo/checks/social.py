from __future__ import annotations

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, make_check


def run(ctx: SeoContext) -> list[CheckResult]:
    html = ctx.html
    page = ctx.final_url or ctx.page_url
    return [
        _tag(
            check_id="SEO-SOCIAL-001",
            name="Open Graph title",
            value=html.get("og_title"),
            why="og:title can control how the page is titled when shared on social platforms. It is SEO-adjacent, not a confirmed search ranking factor.",
            page=page,
        ),
        _tag(
            check_id="SEO-SOCIAL-002",
            name="Open Graph description",
            value=html.get("og_description"),
            why="og:description can control the snippet shown when the page is shared. It is SEO-adjacent, not a confirmed search ranking factor.",
            page=page,
        ),
        _tag(
            check_id="SEO-SOCIAL-003",
            name="Open Graph image",
            value=html.get("og_image"),
            why="og:image provides a preview image when the page is shared. It is SEO-adjacent, not a confirmed search ranking factor.",
            page=page,
        ),
        _tag(
            check_id="SEO-SOCIAL-004",
            name="Twitter/X card",
            value=html.get("twitter_card"),
            why="twitter:card hints how the page should appear on X. It is SEO-adjacent, not a confirmed search ranking factor.",
            page=page,
        ),
    ]


def _tag(*, check_id: str, name: str, value: str | None, why: str, page: str) -> CheckResult:
    text = (value or "").strip()
    if text:
        return make_check(
            check_id=check_id,
            name=name,
            group="social",
            status="pass",
            severity="low",
            message=f"{name} is present.",
            why=why,
            detected=text,
            page_url=page,
        )
    return make_check(
        check_id=check_id,
        name=name,
        group="social",
        status="warning",
        severity="low",
        message=f"{name} is missing.",
        recommendation=f"Add {name} if you want more control over how this page appears when shared.",
        why=why,
        detected="Not found.",
        page_url=page,
    )
