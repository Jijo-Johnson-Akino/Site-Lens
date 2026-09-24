from __future__ import annotations

from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, make_check


def run(ctx: SeoContext) -> list[CheckResult]:
    page = ctx.final_url or ctx.page_url
    images = ctx.html.get("images") or []
    return [
        _alt_attributes(images, page),
        _empty_alt(images, page),
        _title_misuse(images, page),
        _lazy(images, page),
    ]


def _alt_attributes(images: list[dict], page: str) -> CheckResult:
    why = "Alternative text describes images when they cannot be seen. Missing alt attributes leave the image undescribed."
    if not images:
        return make_check(
            check_id="SEO-IMG-001",
            name="Images with alt attributes",
            group="images",
            status="pass",
            severity="medium",
            message="No images were found on the page.",
            why=why,
            detected="0 images.",
            page_url=page,
        )
    missing = [image for image in images if not image.get("has_alt")]
    if not missing:
        return make_check(
            check_id="SEO-IMG-001",
            name="Images with alt attributes",
            group="images",
            status="pass",
            severity="medium",
            message="Every image includes an alt attribute.",
            why=why,
            detected=f"{len(images)} image(s).",
            page_url=page,
        )
    status = "fail" if len(missing) == len(images) else "warning"
    return make_check(
        check_id="SEO-IMG-001",
        name="Images with alt attributes",
        group="images",
        status=status,
        severity="medium",
        message=f"{len(missing)} image(s) are missing alt attributes.",
        recommendation="Add alt attributes to informative images. Decorative images can use an empty alt value.",
        why=why,
        detected=f"{len(missing)} of {len(images)} images have no alt attribute.",
        page_url=page,
    )


def _empty_alt(images: list[dict], page: str) -> CheckResult:
    why = "An empty alt attribute (alt=\"\") can be appropriate for decorative images. It is not automatically a failure."
    if not images:
        return make_check(
            check_id="SEO-IMG-002",
            name="Empty alt handling",
            group="images",
            status="not_applicable",
            severity="low",
            message="Empty alt values were not evaluated because no images were found.",
            page_url=page,
        )
    empty = [image for image in images if image.get("empty_alt")]
    if empty:
        return make_check(
            check_id="SEO-IMG-002",
            name="Empty alt handling",
            group="images",
            status="warning",
            severity="info",
            message=f"{len(empty)} image(s) use an empty alt attribute, which can be appropriate for decorative images.",
            recommendation="Confirm that images with empty alt are decorative. Informative images should have descriptive alt text.",
            why=why,
            detected=f"{len(empty)} empty alt attribute(s).",
            page_url=page,
        )
    return make_check(
        check_id="SEO-IMG-002",
        name="Empty alt handling",
        group="images",
        status="pass",
        severity="info",
        message="No images use an empty alt attribute.",
        why=why,
        page_url=page,
    )


def _title_misuse(images: list[dict], page: str) -> CheckResult:
    why = "The title attribute is not a replacement for alt text."
    if not images:
        return make_check(
            check_id="SEO-IMG-003",
            name="Image title misuse",
            group="images",
            status="not_applicable",
            severity="low",
            message="Image title attributes were not evaluated because no images were found.",
            page_url=page,
        )
    misused = [
        image
        for image in images
        if image.get("has_title") and (not image.get("has_alt") or image.get("empty_alt"))
    ]
    if misused:
        return make_check(
            check_id="SEO-IMG-003",
            name="Image title misuse",
            group="images",
            status="warning",
            severity="low",
            message="Some images use a title attribute without meaningful alt text. Title is not a substitute for alt.",
            recommendation="Provide alt text for informative images instead of relying on the title attribute.",
            why=why,
            detected=f"{len(misused)} image(s).",
            page_url=page,
        )
    return make_check(
        check_id="SEO-IMG-003",
        name="Image title misuse",
        group="images",
        status="pass",
        severity="low",
        message="No images were found using title as a stand-in for alt text.",
        why=why,
        page_url=page,
    )


def _lazy(images: list[dict], page: str) -> CheckResult:
    why = "loading=\"lazy\" can defer offscreen images. This is a performance-related observation, not a critical SEO failure."
    if len(images) < 3:
        return make_check(
            check_id="SEO-IMG-004",
            name="Lazy loading",
            group="images",
            status="not_applicable",
            severity="info",
            message="Lazy loading was not evaluated because the page has fewer than three images.",
            why=why,
            page_url=page,
        )
    without = [image for image in images[1:] if image.get("loading") != "lazy"]
    if without:
        return make_check(
            check_id="SEO-IMG-004",
            name="Lazy loading",
            group="images",
            status="warning",
            severity="info",
            message="Some non-leading images do not declare loading=\"lazy\".",
            recommendation="Consider lazy-loading offscreen images. The first image can stay eager.",
            why=why,
            detected=f"{len(without)} image(s) after the first have no loading=\"lazy\".",
            page_url=page,
        )
    return make_check(
        check_id="SEO-IMG-004",
        name="Lazy loading",
        group="images",
        status="pass",
        severity="info",
        message="Non-leading images declare loading=\"lazy\".",
        why=why,
        page_url=page,
    )
