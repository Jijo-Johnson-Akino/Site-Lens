from backend.analyzers.cro.checks._util import cro_check, primary_ctas
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult


def run(ctx: PageCroContext) -> list[CheckResult]:
    if not ctx.mobile_rendered:
        return [
            cro_check(
                ctx,
                check_id="cro.mobile.cta.not_visible",
                name="Mobile CTA visibility",
                group="mobile",
                status="not_applicable",
                severity="high",
                message="Mobile CTA visibility was not measured because this page was not rendered at the mobile viewport.",
                viewport="mobile",
            ),
            cro_check(
                ctx,
                check_id="cro.mobile.form.overflow",
                name="Mobile form overflow",
                group="mobile",
                status="not_applicable",
                severity="medium",
                message="Mobile form overflow was not measured for this page.",
                viewport="mobile",
            ),
        ]
    cta = ctx.mobile_cta or {}
    primaries = primary_ctas(ctx)
    if not cta.get("exists") and not primaries:
        checks = [
            cro_check(
                ctx,
                check_id="cro.mobile.cta.not_visible",
                name="Mobile CTA visibility",
                group="mobile",
                status="not_applicable",
                severity="high",
                message="No primary CTA candidate was detected, so mobile CTA visibility was not scored.",
                viewport="mobile",
            )
        ]
    else:
        clipped = bool(cta.get("clipped")) or not bool(cta.get("in_viewport"))
        checks = [
            cro_check(
                ctx,
                check_id="cro.mobile.cta.not_visible",
                name="Mobile CTA visibility",
                group="mobile",
                status="warning" if clipped else "pass",
                severity="high",
                message=(
                    "Primary CTA is not visible within the initial mobile viewport."
                    if clipped
                    else "Primary CTA candidate is visible within the initial mobile viewport."
                ),
                selector=cta.get("selector"),
                viewport="mobile",
                detected=str(cta.get("text") or ""),
            )
        ]
    if not ctx.forms:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.mobile.form.overflow",
                name="Mobile form overflow",
                group="mobile",
                status="not_applicable",
                severity="medium",
                message="No form was present to evaluate on mobile.",
                viewport="mobile",
            )
        )
    else:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.mobile.form.overflow",
                name="Mobile form overflow",
                group="mobile",
                status="warning" if ctx.mobile_forms_overflow else "pass",
                severity="medium",
                message=(
                    "A form extends beyond the mobile viewport."
                    if ctx.mobile_forms_overflow
                    else "No mobile form overflow was measured."
                ),
                viewport="mobile",
            )
        )
    return checks
