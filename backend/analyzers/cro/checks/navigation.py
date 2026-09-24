from backend.analyzers.cro.checks._util import cro_check, primary_ctas
from backend.analyzers.cro.config import NAV_ITEM_WARNING
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult


def run(ctx: PageCroContext) -> list[CheckResult]:
    if ctx.nav_links is None:
        return [
            cro_check(
                ctx,
                check_id="cro.navigation.conversion_action_hidden",
                name="Navigation conversion action",
                group="navigation",
                status="not_applicable",
                severity="low",
                message="Navigation measurements were not available for this page.",
            )
        ]
    primaries = primary_ctas(ctx)
    in_nav = False
    for item in ctx.ctas:
        if item.get("strong") or item.get("primary_candidate"):
            if item.get("kind") == "link" and item.get("in_viewport"):
                in_nav = True
    hidden = bool(primaries) and ctx.nav_links >= NAV_ITEM_WARNING and not in_nav
    checks = [
        cro_check(
            ctx,
            check_id="cro.navigation.conversion_action_hidden",
            name="Navigation conversion action",
            group="navigation",
            status="warning" if hidden else "pass",
            severity="low",
            message=(
                "A conversion action may be difficult to reach among a large number of navigation items."
                if hidden
                else "Navigation conversion-action placement did not exceed the configured item threshold."
            ),
            detected=f"{ctx.nav_links} navigation links",
        )
    ]
    return checks
