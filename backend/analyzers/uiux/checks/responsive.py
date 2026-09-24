from __future__ import annotations

from backend.analyzers.uiux.config import DEFAULT_SCORING
from backend.analyzers.uiux.checks._util import ux_check, viewport_name, viewport_width
from backend.analyzers.uiux.models import CheckResult, ViewportSnapshot


def run(snapshot: ViewportSnapshot) -> list[CheckResult]:
    layout = snapshot.layout or {}
    overflow = bool(layout.get("horizontal_overflow"))
    overflow_px = int(layout.get("overflow_px") or 0)
    width = viewport_width(snapshot)
    name = viewport_name(snapshot)
    checks: list[CheckResult] = []

    if overflow and overflow_px > DEFAULT_SCORING.overflow_tolerance_px:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-001",
                name="No horizontal overflow",
                group="responsive",
                status="fail",
                severity="high",
                message=f"The page content extends beyond the {name} viewport.",
                recommendation="Inspect elements wider than the viewport and correct their responsive layout.",
                detected=f"The document width exceeds the viewport by {overflow_px}px.",
                why="Horizontal overflow forces sideways scrolling and hides content on smaller screens.",
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-001",
                name="No horizontal overflow",
                group="responsive",
                status="pass",
                severity="high",
                message=f"No horizontal overflow was detected at the {name} viewport.",
                detected=f"scrollWidth={layout.get('scroll_width')} innerWidth={layout.get('viewport_width')}",
            )
        )

    overflowing = snapshot.overflowing_elements or []
    if overflowing:
        first = overflowing[0]
        extra = int(first.get("overflow_px") or 0)
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-002",
                name="Elements stay inside the viewport",
                group="responsive",
                status="fail" if extra >= 20 else "warning",
                severity="high",
                message=f"At least one element extends outside the {name} viewport.",
                recommendation="Inspect the affected container and child elements for fixed widths or overflow that exceed the viewport.",
                detected=f"Element: {first.get('selector')}\nOverflow: {extra}px",
                affected_element=first.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-002",
                name="Elements stay inside the viewport",
                group="responsive",
                status="pass",
                severity="high",
                message=f"No measured elements extended significantly beyond the {name} viewport.",
            )
        )

    fixed = snapshot.fixed_width_elements or []
    if name == "desktop":
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-003",
                name="No oversized fixed-width elements",
                group="responsive",
                status="not_applicable",
                severity="medium",
                message="Fixed-width checks are applied on tablet and mobile viewports.",
            )
        )
    elif fixed:
        first = fixed[0]
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-003",
                name="No oversized fixed-width elements",
                group="responsive",
                status="warning",
                severity="medium",
                message=f"A large fixed-width element was detected at the {name} viewport ({width}px).",
                recommendation="Replace large pixel widths with fluid or max-width constraints on smaller viewports.",
                detected=f"Element: {first.get('selector')}\nDeclared width: {first.get('width')}px",
                affected_element=first.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-003",
                name="No oversized fixed-width elements",
                group="responsive",
                status="pass",
                severity="medium",
                message=f"No unusually large fixed-width elements were detected at the {name} viewport.",
            )
        )

    nav = snapshot.navigation or {}
    nav_exists = bool(nav.get("exists"))
    nav_visible = bool(nav.get("visible"))
    menu = nav.get("menu_button")
    nav_overflow = bool(nav.get("overflow"))
    if name == "desktop":
        status = "pass" if (nav_exists and nav_visible) or not nav_exists else "warning"
        if not nav_exists:
            status = "not_applicable"
            message = "No primary navigation was detected, so mobile adaptation was not evaluated."
        else:
            message = "Desktop navigation is present and was used as the baseline for smaller viewports."
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-004",
                name="Responsive navigation",
                group="responsive",
                status=status,
                severity="medium",
                message=message,
            )
        )
    elif not nav_exists:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-004",
                name="Responsive navigation",
                group="responsive",
                status="not_applicable",
                severity="medium",
                message="No primary navigation was detected, so mobile adaptation was not evaluated.",
            )
        )
    elif nav_visible or menu:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-004",
                name="Responsive navigation",
                group="responsive",
                status="pass" if not nav_overflow or menu else "warning",
                severity="medium",
                message=(
                    "Navigation remains accessible at this viewport."
                    if nav_visible or menu
                    else "A menu control was detected for smaller viewports."
                ),
                detected=f"visible={nav_visible} menu_button={menu or 'none'} overflow={nav_overflow}",
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-RESP-004",
                name="Responsive navigation",
                group="responsive",
                status="fail",
                severity="high",
                message="Navigation was not accessible at this viewport.",
                recommendation="Keep navigation visible or provide an accessible menu control on smaller screens.",
                detected=f"visible={nav_visible} menu_button={menu or 'none'}",
            )
        )
    return checks
