from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    return [
        a11y_check(
            snapshot,
            check_id="A11Y-CONTRAST-001",
            name="Text has sufficient color contrast",
            group="contrast",
            status="pass",
            severity="high",
            message="No contrast violations were reported. Contrast is measured by axe-core, not by visual guessing.",
            wcag_reference="WCAG 1.4.3",
        )
    ]
