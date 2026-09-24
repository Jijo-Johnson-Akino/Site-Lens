from __future__ import annotations

from backend.analyzers.uiux.config import DEFAULT_SCORING
from backend.analyzers.uiux.checks._util import ux_check, viewport_name
from backend.analyzers.uiux.models import CheckResult, ViewportSnapshot


def run(snapshot: ViewportSnapshot) -> list[CheckResult]:
    name = viewport_name(snapshot)
    small = snapshot.small_text or []
    clipped = snapshot.clipped_text or []
    headings = snapshot.headings or []
    checks: list[CheckResult] = []

    if small:
        first = small[0]
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-TYPE-001",
                name="Text is not extremely small",
                group="typography",
                status="warning",
                severity="medium",
                message=f"Visible text smaller than {DEFAULT_SCORING.min_font_px:g}px was detected at the {name} viewport.",
                recommendation="Increase the font size of body copy that falls below the configured minimum.",
                detected=f"Element: {first.get('selector')} font-size={first.get('font_size')}px",
                affected_element=first.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-TYPE-001",
                name="Text is not extremely small",
                group="typography",
                status="pass",
                severity="low",
                message=f"No visible text below {DEFAULT_SCORING.min_font_px:g}px was detected.",
            )
        )

    if clipped:
        first = clipped[0]
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-TYPE-002",
                name="Text is not clipped",
                group="typography",
                status="warning",
                severity="medium",
                message="Visible text appears clipped by overflow or a fixed height.",
                recommendation="Allow the container to grow or wrap so the text remains readable.",
                detected=f"Element: {first.get('selector')}",
                affected_element=first.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-TYPE-002",
                name="Text is not clipped",
                group="typography",
                status="pass",
                severity="medium",
                message="No clipped paragraph or heading text was detected.",
            )
        )

    if not headings:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-TYPE-003",
                name="Primary heading visibility",
                group="typography",
                status="not_applicable",
                severity="medium",
                message="No H1 heading was present to evaluate visibility.",
            )
        )
    elif any(item.get("visible") for item in headings):
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-TYPE-003",
                name="Primary heading visibility",
                group="typography",
                status="pass",
                severity="medium",
                message="The primary heading is visible.",
                detected=headings[0].get("text"),
                affected_element=headings[0].get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-TYPE-003",
                name="Primary heading visibility",
                group="typography",
                status="fail",
                severity="medium",
                message="An H1 is present but is not visible in the rendered page.",
                recommendation="Remove CSS that hides the primary heading at this viewport.",
                affected_element=headings[0].get("selector"),
            )
        )
    return checks
