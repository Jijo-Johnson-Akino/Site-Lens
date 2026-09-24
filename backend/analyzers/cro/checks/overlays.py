from backend.analyzers.cro.checks._util import cro_check, primary_ctas
from backend.analyzers.cro.config import OVERLAY_COVER_THRESHOLD
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult


def run(ctx: PageCroContext) -> list[CheckResult]:
    if not ctx.rendered:
        return [
            cro_check(
                ctx,
                check_id="cro.overlay.cta.covered",
                name="Overlay coverage",
                group="interaction",
                status="not_applicable",
                severity="medium",
                message="Overlays were not measured because this page was not rendered.",
            )
        ]
    overlays = ctx.overlays or []
    coverage = 0.0
    for item in overlays:
        try:
            coverage = max(coverage, float(item.get("coverage") or 0))
        except (TypeError, ValueError):
            continue
    primaries = primary_ctas(ctx)
    in_view = bool(primaries and (primaries[0].get("in_viewport") or ctx.desktop and (ctx.desktop.get("cta") or {}).get("in_viewport")))
    covered = coverage >= OVERLAY_COVER_THRESHOLD and (in_view or bool(primaries))
    if not overlays:
        return [
            cro_check(
                ctx,
                check_id="cro.overlay.cta.covered",
                name="Overlay coverage",
                group="interaction",
                status="pass",
                severity="low",
                message="No overlay covering a conversion action was detected.",
            )
        ]
    return [
        cro_check(
            ctx,
            check_id="cro.overlay.cta.covered",
            name="Overlay coverage",
            group="interaction",
            status="warning" if covered else "pass",
            severity="medium" if covered else "low",
            message=(
                "Overlay detected covering the primary CTA."
                if covered
                else "An overlay was detected on the initial viewport."
            ),
            detected=f"coverage={coverage:.2f}",
            selector=(overlays[0] or {}).get("selector") if overlays else None,
            evidence={"coverage": coverage},
        )
    ]
