from __future__ import annotations

import re

from backend.analyzers.uiux.checks._util import ux_check
from backend.analyzers.uiux.models import CheckResult, ViewportSnapshot

UNSAFE_LABEL = re.compile(
    r"\b(delete|remove account|purchase|buy now|pay now|checkout|logout|log out|sign out|unsubscribe)\b",
    re.I,
)


def run(snapshot: ViewportSnapshot) -> list[CheckResult]:
    buttons = snapshot.buttons or []
    links = snapshot.links or []
    disabled = snapshot.disabled_primary or [item for item in buttons if item.get("disabled") and item.get("in_viewport")]
    checks: list[CheckResult] = []

    if buttons:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-INTERACT-001",
                name="Visible buttons",
                group="interactive",
                status="pass",
                severity="low",
                message=f"{len(buttons)} visible button{'' if len(buttons) == 1 else 's'} detected.",
                detected=str(len(buttons)),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-INTERACT-001",
                name="Visible buttons",
                group="interactive",
                status="warning",
                severity="low",
                message="No visible buttons were detected.",
            )
        )

    if links:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-INTERACT-002",
                name="Visible links",
                group="interactive",
                status="pass",
                severity="low",
                message=f"{len(links)} visible link{'' if len(links) == 1 else 's'} detected.",
                detected=str(len(links)),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-INTERACT-002",
                name="Visible links",
                group="interactive",
                status="warning",
                severity="low",
                message="No visible links were detected.",
                recommendation="Provide visible links so visitors can reach other pages or actions.",
            )
        )

    if disabled:
        first = disabled[0]
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-INTERACT-003",
                name="Primary controls are enabled",
                group="interactive",
                status="warning",
                severity="medium",
                message="A prominently visible disabled button was detected.",
                recommendation="If the control is the primary action, enable it or explain why it is unavailable.",
                detected=f"text={first.get('text') or 'unlabeled'}",
                affected_element=first.get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-INTERACT-003",
                name="Primary controls are enabled",
                group="interactive",
                status="pass" if buttons else "not_applicable",
                severity="low",
                message=(
                    "No prominently disabled primary buttons were detected."
                    if buttons
                    else "No buttons were present to evaluate disabled state."
                ),
            )
        )

    testable = [
        item
        for item in buttons
        if not UNSAFE_LABEL.search(str(item.get("text") or ""))
        and item.get("pointer_events") != "none"
        and not item.get("disabled")
    ]
    blocked = [item for item in buttons if item.get("pointer_events") == "none"]
    if not buttons and not links:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-INTERACT-004",
                name="Interactive controls appear usable",
                group="interactive",
                status="not_applicable",
                severity="low",
                message="No interactive controls were present to inspect.",
            )
        )
    elif blocked and not testable and not links:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-INTERACT-004",
                name="Interactive controls appear usable",
                group="interactive",
                status="warning",
                severity="low",
                message="Visible buttons have pointer events disabled.",
                detected=f"pointer-events:none count={len(blocked)}",
                affected_element=blocked[0].get("selector"),
            )
        )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-INTERACT-004",
                name="Interactive controls appear usable",
                group="interactive",
                status="pass",
                severity="low",
                message="Visible interactive controls appear enabled. Destructive actions were not activated.",
                detected=f"inspected_buttons={len(testable)} visible_links={len(links)}",
            )
        )
    return checks
