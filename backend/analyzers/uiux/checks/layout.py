from __future__ import annotations

from backend.analyzers.uiux.checks._util import ux_check, viewport_name
from backend.analyzers.uiux.models import CheckResult, ViewportSnapshot


def run(snapshot: ViewportSnapshot) -> list[CheckResult]:
    name = viewport_name(snapshot)
    main = snapshot.main or {}
    load = snapshot.load or {}
    overlaps = snapshot.overlapping_pairs or []
    offscreen = snapshot.offscreen_critical or []
    checks: list[CheckResult] = []

    ready = str(load.get("ready_state") or snapshot.page.get("ready_state") or "")
    visible = bool(main.get("visible") or load.get("main_visible"))
    if visible:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-LAYOUT-001",
                name="Main content visible",
                group="layout",
                status="pass",
                severity="high",
                message="Main content is visible without excessive clipping.",
                detected=f"readyState={ready or 'unknown'} selector={main.get('selector')}",
                affected_element=main.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-LAYOUT-001",
                name="Main content visible",
                group="layout",
                status="fail",
                severity="high",
                message="Main content was not visible after the page rendered.",
                recommendation="Ensure the primary content container is rendered and not hidden at this viewport.",
                detected=f"readyState={ready or 'unknown'}",
            )
        )

    if overlaps:
        first = overlaps[0]
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-LAYOUT-002",
                name="Content does not overlap unexpectedly",
                group="layout",
                status="warning",
                severity="medium",
                message="Significant overlap was detected between visible content elements.",
                recommendation="Adjust layout so unrelated text and controls do not cover each other.",
                detected=f"{first.get('a')} overlaps {first.get('b')} ({first.get('intersection_px')}px intersection)",
                affected_element=first.get("a"),
                why="Decorative layers, badges, and navigation overlays are ignored. Only conservative content overlaps are reported.",
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-LAYOUT-002",
                name="Content does not overlap unexpectedly",
                group="layout",
                status="pass",
                severity="medium",
                message="No significant unexpected content overlap was detected.",
            )
        )

    if offscreen:
        first = offscreen[0]
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-LAYOUT-003",
                name="Critical content stays on-screen",
                group="layout",
                status="fail",
                severity="high",
                message=f"Important content is positioned outside the {name} viewport.",
                recommendation="Keep headings, navigation, and primary actions inside the reachable layout.",
                detected=f"Element: {first.get('selector')} left={first.get('left')}",
                affected_element=first.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-LAYOUT-003",
                name="Critical content stays on-screen",
                group="layout",
                status="pass",
                severity="medium",
                message="No off-screen headings, navigation, or primary actions were detected.",
            )
        )
    return checks
