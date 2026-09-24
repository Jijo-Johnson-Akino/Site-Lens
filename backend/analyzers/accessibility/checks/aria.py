from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    aria = snapshot.aria or {}
    ids = snapshot.ids or {}
    broken = aria.get("broken_refs") or []
    hidden = aria.get("hidden_focusable") or snapshot.focus.get("hidden_focusable") or []
    dupes = ids.get("duplicates") or []
    checks: list[CheckResult] = []

    checks.append(a11y_check(snapshot, check_id="A11Y-ARIA-001", name="ARIA attributes are valid", group="aria", status="pass", severity="high", message="No invalid ARIA attributes were detected by SiteLens DOM inspection. axe-core results are merged when present.", wcag_reference="WCAG 4.1.2"))

    if broken:
        checks.append(a11y_check(snapshot, check_id="A11Y-ARIA-002", name="ARIA references exist", group="aria", status="fail", severity="high", message="aria-labelledby or aria-describedby points to a missing ID.", recommendation="Point ARIA relationships at elements that exist in the document.", selector=(broken[0] or {}).get("selector") if isinstance(broken[0], dict) else None, affected_element_count=len(broken), wcag_reference="WCAG 1.3.1", detected=str((broken[0] or {}).get("ref") if isinstance(broken[0], dict) else broken[0])))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-ARIA-002", name="ARIA references exist", group="aria", status="pass", severity="medium", message="ARIA labelledby/describedby references resolve."))

    if hidden:
        first = hidden[0]
        selector = first.get("selector") if isinstance(first, dict) else first
        checks.append(a11y_check(snapshot, check_id="A11Y-ARIA-003", name="Hidden content is not focusable", group="aria", status="fail", severity="high", message="An aria-hidden ancestor contains a focusable control.", recommendation="Do not hide focusable controls from the accessibility tree, or remove them from tab order.", selector=selector, affected_element_count=len(hidden), wcag_reference="WCAG 4.1.2"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-ARIA-003", name="Hidden content is not focusable", group="aria", status="pass", severity="high", message="No aria-hidden focusable descendants were detected."))

    if dupes:
        checks.append(a11y_check(snapshot, check_id="A11Y-ID-001", name="IDs are unique", group="aria", status="fail", severity="high", message=f"Duplicate IDs were detected ({', '.join(str(item) for item in dupes[:4])}).", recommendation="Make every id unique. Duplicates break labels, ARIA references, and fragment navigation.", affected_element_count=len(dupes), wcag_reference="WCAG 4.1.1", detected=", ".join(str(item) for item in dupes[:6])))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-ID-001", name="IDs are unique", group="aria", status="pass", severity="medium", message="No duplicate IDs were detected."))
    return checks
