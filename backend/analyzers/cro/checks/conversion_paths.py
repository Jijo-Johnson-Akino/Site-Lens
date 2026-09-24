from backend.analyzers.cro.checks._util import cro_check, primary_ctas
from backend.analyzers.cro.config import CONVERSION_PAGE_TYPES, OPTIONAL_CTA_TYPES
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult


def run(ctx: PageCroContext) -> list[CheckResult]:
    if ctx.page_type in OPTIONAL_CTA_TYPES and not ctx.conversion_path:
        return [
            cro_check(
                ctx,
                check_id="cro.conversion_path.unresolved",
                name="Conversion path",
                group="conversion_path",
                status="not_applicable",
                severity="medium",
                message="A conversion path is not required on this page type.",
            )
        ]
    if ctx.conversion_path:
        labels = " → ".join(item.get("page_type") or item.get("url") or "" for item in ctx.conversion_path)
        return [
            cro_check(
                ctx,
                check_id="cro.conversion_path.unresolved",
                name="Conversion path",
                group="conversion_path",
                status="pass",
                severity="medium",
                message="Internal path toward a contact/conversion page detected.",
                detected=labels[:200],
                evidence={"nodes": [item.get("url") for item in ctx.conversion_path]},
            )
        ]
    dest = None
    primaries = primary_ctas(ctx)
    if primaries:
        dest = primaries[0].get("destination")
    if dest in {"signup", "contact", "pricing", "booking", "checkout", "form"}:
        return [
            cro_check(
                ctx,
                check_id="cro.conversion_path.unresolved",
                name="Conversion path",
                group="conversion_path",
                status="pass",
                severity="medium",
                message="A plausible conversion destination was observed on the page.",
                detected=str(dest),
            )
        ]
    if ctx.site_has_conversion_page and ctx.page.is_seed:
        return [
            cro_check(
                ctx,
                check_id="cro.conversion_path.unresolved",
                name="Conversion path",
                group="conversion_path",
                status="warning",
                severity="medium",
                message="Conversion-oriented pages were crawled, but no internal path from this page was determined from the crawled links.",
            )
        ]
    if ctx.page_type in CONVERSION_PAGE_TYPES:
        return [
            cro_check(
                ctx,
                check_id="cro.conversion_path.unresolved",
                name="Conversion path",
                group="conversion_path",
                status="pass",
                severity="low",
                message="This page is itself a conversion-oriented destination.",
            )
        ]
    return [
        cro_check(
            ctx,
            check_id="cro.conversion_path.unresolved",
            name="Conversion path",
            group="conversion_path",
            status="warning",
            severity="medium",
            message="No conversion path could be determined from the crawled links.",
        )
    ]
