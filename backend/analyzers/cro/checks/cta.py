from backend.analyzers.cro.checks._util import cro_check, primary_ctas
from backend.analyzers.cro.config import COMPETING_CTA_THRESHOLD, OPTIONAL_CTA_TYPES
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult


def run(ctx: PageCroContext) -> list[CheckResult]:
    checks: list[CheckResult] = []
    primaries = primary_ctas(ctx)
    potentials = [item for item in ctx.ctas if item.get("potential") or (not item.get("primary_candidate") and item.get("text"))]
    prominent = [item for item in ctx.ctas if item.get("in_viewport") or item.get("primary_candidate") or item.get("strong")]
    if ctx.page_type in OPTIONAL_CTA_TYPES and not primaries:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.primary.missing",
                name="Primary CTA",
                group="primary_cta",
                status="not_applicable",
                severity="medium",
                message="This page type is not expected to include a primary conversion action.",
            )
        )
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.primary.not_visible",
                name="Primary CTA visibility",
                group="primary_cta",
                status="not_applicable",
                severity="high",
                message="Primary CTA visibility was not evaluated for this page type.",
            )
        )
    elif not primaries:
        if potentials or ctx.ctas:
            checks.append(
                cro_check(
                    ctx,
                    check_id="cro.cta.primary.missing",
                    name="Primary CTA",
                    group="primary_cta",
                    status="warning",
                    severity="medium",
                    message="Potential CTA elements were detected, but none met the confidence threshold to be labeled a primary CTA.",
                    detected=f"Potential CTA count: {len(ctx.ctas)}",
                    recommendation="If the page has a primary next step, present it with clear action wording.",
                )
            )
        else:
            checks.append(
                cro_check(
                    ctx,
                    check_id="cro.cta.primary.missing",
                    name="Primary CTA",
                    group="primary_cta",
                    status="fail" if ctx.page_type in {"homepage", "product", "service", "pricing"} else "warning",
                    severity="high" if ctx.page_type == "homepage" else "medium",
                    message="No primary CTA was detected on this page.",
                    recommendation="If the page has an intended conversion action, make that control visible as a button or link.",
                )
            )
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.primary.not_visible",
                name="Primary CTA visibility",
                group="primary_cta",
                status="not_applicable",
                severity="high",
                message="CTA visibility was not evaluated because no primary CTA was identified.",
            )
        )
    else:
        primary = primaries[0]
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.primary.missing",
                name="Primary CTA",
                group="primary_cta",
                status="pass",
                severity="medium",
                message="A primary CTA was identified from observable action wording, placement, and control type.",
                detected=str(primary.get("text") or ""),
                selector=primary.get("selector"),
                evidence={"confidence": primary.get("confidence"), "text": primary.get("text")},
            )
        )
        if not ctx.rendered:
            checks.append(
                cro_check(
                    ctx,
                    check_id="cro.cta.primary.not_visible",
                    name="Primary CTA visibility",
                    group="primary_cta",
                    status="not_applicable",
                    severity="high",
                    message="Viewport visibility was not measured because this page was not rendered in the SiteLens browser session.",
                    selector=primary.get("selector"),
                )
            )
        else:
            visible = primary.get("visible", True) and primary.get("in_viewport") and not primary.get("clipped")
            viewport = "desktop"
            checks.append(
                cro_check(
                    ctx,
                    check_id="cro.cta.primary.not_visible",
                    name="Primary CTA visibility",
                    group="primary_cta",
                    status="pass" if visible else "fail",
                    severity="high",
                    message=(
                        "Primary conversion action is visible within the initial desktop viewport."
                        if visible
                        else "Primary conversion action is not visible within the initial viewport."
                    ),
                    recommendation=None if visible else "Keep the primary conversion action visible in the initial viewport.",
                    selector=primary.get("selector"),
                    viewport=viewport,
                    detected=str(primary.get("text") or ""),
                )
            )

    broken = [item for item in ctx.ctas if item.get("broken") or item.get("disabled")]
    if broken:
        first = broken[0]
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.destination.unresolved",
                name="CTA destination",
                group="conversion_path",
                status="warning",
                severity="medium",
                message="A CTA destination could not be resolved or the control is disabled.",
                detected=str(first.get("text") or first.get("href") or ""),
                selector=first.get("selector"),
                affected_element_count=len(broken),
            )
        )
    elif primaries and primaries[0].get("destination") in {None, "unknown"}:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.destination.unresolved",
                name="CTA destination",
                group="conversion_path",
                status="warning",
                severity="low",
                message="Primary CTA destination could not be resolved.",
                detected=str(primaries[0].get("text") or ""),
                selector=primaries[0].get("selector"),
            )
        )
    elif primaries:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.destination.unresolved",
                name="CTA destination",
                group="conversion_path",
                status="pass",
                severity="low",
                message=f"Primary CTA destination classified as {primaries[0].get('destination')}.",
                detected=str(primaries[0].get("href") or primaries[0].get("destination")),
                selector=primaries[0].get("selector"),
            )
        )
    else:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.destination.unresolved",
                name="CTA destination",
                group="conversion_path",
                status="not_applicable",
                severity="low",
                message="CTA destination was not evaluated because no primary CTA was identified.",
            )
        )

    competing = [item for item in prominent if item.get("in_viewport") or item.get("strong")]
    if len(competing) >= COMPETING_CTA_THRESHOLD:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.multiple_competing",
                name="Competing CTAs",
                group="interaction",
                status="warning",
                severity="low",
                message="Multiple prominent actions detected in the primary conversion area.",
                detected=f"{len(competing)} prominent actions",
                affected_element_count=len(competing),
            )
        )
    else:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.multiple_competing",
                name="Competing CTAs",
                group="interaction",
                status="pass" if ctx.ctas else "not_applicable",
                severity="low",
                message=(
                    "Prominent action count is within the configured threshold."
                    if ctx.ctas
                    else "No prominent actions were present to compare."
                ),
            )
        )
    return checks
