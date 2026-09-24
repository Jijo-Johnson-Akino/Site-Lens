from __future__ import annotations

from backend.analyzers.mobile.checks._util import as_int, finding
from backend.analyzers.mobile.config import DEFAULT_SCORING
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    overflowing = snapshot.overflowing_elements or []
    min_width_els = snapshot.min_width_elements or []
    clipped = snapshot.clipped_containers or []
    offscreen = snapshot.offscreen_critical or []
    tolerance = DEFAULT_SCORING.overflow_tolerance_px
    checks: list[CheckResult] = []

    page_wide = [item for item in overflowing if not item.get("isolated_scroll")]
    if page_wide:
        first = page_wide[0]
        extra_px = as_int(first.get("overflow_px"))
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-LAYOUT-001",
                name="Elements stay inside the viewport",
                group="layout",
                status="fail" if extra_px >= 24 else "warning",
                severity="high" if extra_px >= 24 else "medium",
                message=f"Element {first.get('selector')} extends {extra_px}px beyond the viewport.",
                recommendation="Allow the container to shrink, wrap, or scroll locally instead of expanding the page width.",
                selector=first.get("selector"),
                affected_element_count=len(page_wide),
                measured_value=extra_px,
                expected_value=tolerance,
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-LAYOUT-001",
                name="Elements stay inside the viewport",
                group="layout",
                status="pass",
                severity="high",
                message="No measured elements extended significantly beyond the mobile viewport.",
            )
        )

    if clipped:
        first = clipped[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-LAYOUT-002",
                name="Clipped containers",
                group="layout",
                status="warning",
                severity="medium",
                message=f"A container clips overflowing content ({first.get('selector')}).",
                recommendation="Check whether important content is hidden by overflow:hidden on small screens.",
                selector=first.get("selector"),
                affected_element_count=len(clipped),
                measured_value=first.get("scroll_width"),
                expected_value=first.get("client_width"),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-LAYOUT-002",
                name="Clipped containers",
                group="layout",
                status="pass",
                severity="medium",
                message="No clipped overflowing containers were measured.",
            )
        )

    if min_width_els:
        first = min_width_els[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-LAYOUT-003",
                name="Large minimum widths",
                group="layout",
                status="warning",
                severity="medium",
                message=f"An element declares a minimum width larger than the viewport ({first.get('selector')}).",
                recommendation="Replace large min-width values with fluid constraints on small screens.",
                selector=first.get("selector"),
                affected_element_count=len(min_width_els),
                measured_value=first.get("min_width"),
                expected_value=snapshot.viewport.get("width"),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-LAYOUT-003",
                name="Large minimum widths",
                group="layout",
                status="pass",
                severity="medium",
                message="No unusually large min-width values were measured.",
            )
        )

    if offscreen:
        first = offscreen[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-LAYOUT-004",
                name="Off-screen critical content",
                group="layout",
                status="warning",
                severity="medium",
                message=f"A critical element sits outside the mobile viewport ({first.get('selector')}).",
                recommendation="Keep primary headings, navigation, and actions reachable without horizontal panning.",
                selector=first.get("selector"),
                affected_element_count=len(offscreen),
                measured_value=first.get("left"),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-LAYOUT-004",
                name="Off-screen critical content",
                group="layout",
                status="pass",
                severity="medium",
                message="No critical elements were measured fully outside the viewport.",
            )
        )
    return checks
