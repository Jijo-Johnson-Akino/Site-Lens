from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    controls = [item for item in (snapshot.controls or []) if item.get("visible") is not False]
    if not controls:
        return [
            a11y_check(snapshot, check_id="A11Y-CTRL-001", name="Buttons have accessible names", group="controls", status="not_applicable", severity="high", message="No buttons were present to evaluate.")
        ]
    unnamed = [item for item in controls if not item.get("named")]
    if unnamed:
        return [
            a11y_check(
                snapshot,
                check_id="A11Y-CTRL-001",
                name="Buttons have accessible names",
                group="controls",
                status="fail",
                severity="high",
                message=f"{len(unnamed)} button(s) have no accessible name.",
                recommendation="Provide visible text or an aria-label / aria-labelledby name. Icon-only buttons need an accessible name.",
                selector=unnamed[0].get("selector"),
                affected_element_count=len(unnamed),
                wcag_reference="WCAG 4.1.2",
            )
        ]
    return [
        a11y_check(
            snapshot,
            check_id="A11Y-CTRL-001",
            name="Buttons have accessible names",
            group="controls",
            status="pass",
            severity="high",
            message="Visible buttons expose accessible names, including aria-label where used.",
            wcag_reference="WCAG 4.1.2",
        )
    ]
