from backend.analyzers.cro.checks._util import cro_check, primary_ctas
from backend.analyzers.cro.config import VP_PAGE_TYPES
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult


def run(ctx: PageCroContext) -> list[CheckResult]:
    if ctx.page_type not in VP_PAGE_TYPES:
        return [
            cro_check(
                ctx,
                check_id="cro.value_proposition.h1_missing",
                name="Value proposition heading",
                group="value_proposition",
                status="not_applicable",
                severity="medium",
                message="Value proposition checks are limited on this page type.",
            ),
            cro_check(
                ctx,
                check_id="cro.value_proposition.supporting_text_missing",
                name="Supporting description",
                group="value_proposition",
                status="not_applicable",
                severity="medium",
                message="Supporting description was not required for this page type.",
            ),
            cro_check(
                ctx,
                check_id="cro.value_proposition.cta_missing",
                name="Value proposition CTA",
                group="value_proposition",
                status="not_applicable",
                severity="medium",
                message="A value-proposition CTA was not required for this page type.",
            ),
        ]
    h1 = (ctx.signals.get("h1") or ctx.page.h1 or "").strip()
    generic = bool(ctx.signals.get("generic_h1"))
    heading_visible = True
    if ctx.desktop:
        headings = ctx.desktop.get("headings") or []
        if headings:
            heading_visible = any(item.get("visible") and item.get("in_viewport") for item in headings)
        elif ctx.desktop.get("content", {}).get("h1_visible") is False:
            heading_visible = False
    if not h1:
        h1_status, h1_msg = "fail", "Primary page heading does not clearly communicate a product/service proposition."
    elif generic:
        h1_status, h1_msg = "warning", "Primary page heading does not clearly communicate a product/service proposition."
    elif ctx.rendered and not heading_visible:
        h1_status, h1_msg = "warning", "A heading exists but is not visible in the initial viewport."
    else:
        h1_status, h1_msg = "pass", "Value proposition components detected in the primary heading."
    checks = [
        cro_check(
            ctx,
            check_id="cro.value_proposition.h1_missing",
            name="Value proposition heading",
            group="value_proposition",
            status=h1_status,
            severity="medium",
            message=h1_msg,
            detected=h1 or None,
            recommendation=None if h1_status == "pass" else "Use a heading that names the product or service and who it is for.",
        )
    ]
    supporting = (ctx.signals.get("supporting_text") or "").strip()
    if len(supporting) >= 40:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.value_proposition.supporting_text_missing",
                name="Supporting description",
                group="value_proposition",
                status="pass",
                severity="low",
                message="Supporting descriptive text was detected near the primary heading.",
                detected=supporting[:160],
            )
        )
    else:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.value_proposition.supporting_text_missing",
                name="Supporting description",
                group="value_proposition",
                status="warning",
                severity="low",
                message="Supporting descriptive text was not detected near the primary heading.",
                recommendation="Add a short description that explains the offer beneath the heading.",
            )
        )
    if primary_ctas(ctx):
        checks.append(
            cro_check(
                ctx,
                check_id="cro.value_proposition.cta_missing",
                name="Value proposition CTA",
                group="value_proposition",
                status="pass",
                severity="medium",
                message="A conversion action was detected with the value proposition.",
            )
        )
    else:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.value_proposition.cta_missing",
                name="Value proposition CTA",
                group="value_proposition",
                status="warning",
                severity="medium",
                message="No conversion action was detected with the value proposition.",
            )
        )
    return checks
