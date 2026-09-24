from __future__ import annotations

from backend.analyzers.uiux.checks._util import ux_check, viewport_name
from backend.analyzers.uiux.models import CheckResult, ViewportSnapshot


def run(snapshot: ViewportSnapshot) -> list[CheckResult]:
    cta = snapshot.cta or {}
    name = viewport_name(snapshot)
    exists = bool(cta.get("exists"))
    visible = bool(cta.get("visible"))
    clipped = bool(cta.get("clipped"))
    empty_buttons = [item for item in (snapshot.buttons or []) if item.get("empty") and item.get("visible")]
    checks: list[CheckResult] = []

    if exists:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CTA-001",
                name="Primary action exists",
                group="interactive",
                status="pass",
                severity="medium",
                message="A prominent action control was detected.",
                detected=f"text={cta.get('text') or 'unlabeled'} selector={cta.get('selector')}",
                affected_element=cta.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CTA-001",
                name="Primary action exists",
                group="interactive",
                status="warning",
                severity="low",
                message="No prominent action control was detected.",
                recommendation="If the page has a primary next step, make that control visible as a button or link.",
            )
        )

    if not exists:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CTA-002",
                name="Primary action visibility",
                group="interactive",
                status="not_applicable",
                severity="medium",
                message="CTA visibility was not evaluated because no primary action was detected.",
            )
        )
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CTA-003",
                name="Primary action not clipped",
                group="interactive",
                status="not_applicable",
                severity="medium",
                message="CTA clipping was not evaluated because no primary action was detected.",
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CTA-002",
                name="Primary action visibility",
                group="interactive",
                status="pass" if visible else "fail",
                severity="medium",
                message=(
                    "The detected primary action is visible on the rendered page."
                    if visible
                    else "The detected primary action is not visible in the rendered page."
                ),
                recommendation=None if visible else "Ensure the primary action is not hidden with CSS at this viewport.",
                affected_element=cta.get("selector"),
            )
        )
        if clipped:
            overflow_px = int(cta.get("overflow_px") or 0)
            checks.append(
                ux_check(
                    snapshot,
                    check_id="UX-CTA-003",
                    name="Primary action not clipped",
                    group="interactive",
                    status="fail",
                    severity="high",
                    message=f"A primary action is clipped or extends beyond the {name} viewport.",
                    recommendation="Keep the action control fully inside the viewport at this width.",
                    detected=f"The control extends beyond the viewport by {overflow_px}px.",
                    affected_element=cta.get("selector"),
                )
            )
        else:
            checks.append(
                ux_check(
                    snapshot,
                    check_id="UX-CTA-003",
                    name="Primary action not clipped",
                    group="interactive",
                    status="pass",
                    severity="medium",
                    message="The detected primary action is fully inside the viewport.",
                    affected_element=cta.get("selector"),
                )
            )

    if empty_buttons:
        first = empty_buttons[0]
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CTA-004",
                name="Button text present",
                group="interactive",
                status="fail",
                severity="medium",
                message="An empty button was detected.",
                recommendation="Give every button visible text or an accessible name.",
                detected=f"Empty controls: {len(empty_buttons)}",
                affected_element=first.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-CTA-004",
                name="Button text present",
                group="interactive",
                status="pass" if snapshot.buttons else "not_applicable",
                severity="medium",
                message=(
                    "Visible buttons include text or an accessible name."
                    if snapshot.buttons
                    else "No buttons were present to evaluate."
                ),
            )
        )
    return checks
