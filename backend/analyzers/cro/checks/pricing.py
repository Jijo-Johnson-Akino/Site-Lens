from backend.analyzers.cro.checks._util import cro_check, primary_ctas
from backend.analyzers.cro.config import QUOTE_PAGE_TYPES
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult


def run(ctx: PageCroContext) -> list[CheckResult]:
    pricing = ctx.signals.get("pricing") or {}
    expects_offer = ctx.page_type in QUOTE_PAGE_TYPES or ctx.page_type == "pricing"
    if not expects_offer:
        return [
            cro_check(
                ctx,
                check_id="cro.pricing.offer.not_detected",
                name="Pricing or offer",
                group="pricing",
                status="not_applicable",
                severity="low",
                message="Visible pricing is not required on this page type.",
            )
        ]
    has_price = bool(pricing.get("price_text") or pricing.get("plan_text"))
    has_quote = bool(pricing.get("quote_cta")) or any(
        item.get("destination") in {"contact", "booking", "signup", "checkout", "pricing"}
        or "quote" in str(item.get("text") or "").lower()
        or "trial" in str(item.get("text") or "").lower()
        for item in primary_ctas(ctx) or ctx.ctas
    )
    if has_price or has_quote:
        return [
            cro_check(
                ctx,
                check_id="cro.pricing.offer.not_detected",
                name="Pricing or offer",
                group="pricing",
                status="pass",
                severity="low",
                message="Pricing or offer information was detected." if has_price else "A trial, quote, or purchase action was detected in place of public prices.",
                detected="price" if has_price else "offer CTA",
            )
        ]
    return [
        cro_check(
            ctx,
            check_id="cro.pricing.offer.not_detected",
            name="Pricing or offer",
            group="pricing",
            status="warning",
            severity="low",
            message="Pricing or offer information was not detected.",
        )
    ]
