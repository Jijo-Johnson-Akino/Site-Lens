from __future__ import annotations

from backend.analyzers.uiux.config import DEFAULT_SCORING
from backend.analyzers.uiux.checks._util import ux_check, viewport_name
from backend.analyzers.uiux.models import CheckResult, ViewportSnapshot


def run(snapshot: ViewportSnapshot) -> list[CheckResult]:
    name = viewport_name(snapshot)
    headings = snapshot.headings or []
    empty = snapshot.empty_sections or []
    overlays = snapshot.overlays or []
    blocking = [item for item in overlays if float(item.get("coverage") or 0) >= DEFAULT_SCORING.overlay_coverage]
    checks: list[CheckResult] = []

    visible_h1 = any(item.get("visible") for item in headings)
    if not headings:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CONTENT-001",
                name="H1 visible",
                group="content",
                status="not_applicable",
                severity="medium",
                message="No H1 heading was present to verify visibility.",
            )
        )
    elif visible_h1:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CONTENT-001",
                name="H1 visible",
                group="content",
                status="pass",
                severity="medium",
                message="The H1 is visible in the rendered page.",
                detected=headings[0].get("text"),
                affected_element=headings[0].get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CONTENT-001",
                name="H1 visible",
                group="content",
                status="fail",
                severity="medium",
                message="The H1 is not visible after render.",
                recommendation="Ensure the page heading is rendered visibly at this viewport.",
                affected_element=headings[0].get("selector"),
            )
        )

    if empty:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CONTENT-002",
                name="No empty visible sections",
                group="content",
                status="warning",
                severity="low",
                message="A large visible container appears to contain no meaningful content.",
                recommendation="Remove unused empty regions or populate them with content.",
                detected=f"Element: {empty[0].get('selector')}",
                affected_element=empty[0].get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CONTENT-002",
                name="No empty visible sections",
                group="content",
                status="pass",
                severity="low",
                message="No obviously empty content sections were detected.",
            )
        )

    if blocking:
        first = blocking[0]
        coverage = float(first.get("coverage") or 0)
        keyworded = bool(first.get("keywords"))
        obscures = coverage >= 0.7
        if obscures:
            status = "warning"
            message = "A large overlay obscures the initial page content."
        else:
            status = "pass"
            message = "A full-screen overlay was detected."
        if not obscures and keyworded:
            status = "pass"
            message = "A full-screen overlay was detected."
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CONTENT-003",
                name="Overlays do not block the page",
                group="content",
                status=status,
                severity="medium" if obscures else "info",
                message=message,
                recommendation="If the overlay is unexpected, delay it or allow the underlying content to remain readable."
                if obscures
                else None,
                detected=f"coverage={coverage:.0%} keywords={keyworded} viewport={name}",
                affected_element=first.get("selector"),
                why="Overlays are reported as observations. Cookie, login, and newsletter dialogs are not automatically treated as failures.",
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CONTENT-003",
                name="Overlays do not block the page",
                group="content",
                status="pass",
                severity="info",
                message="No large overlay was covering the page.",
            )
        )
    return checks
