from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.config import KEYBOARD_TAB_LIMIT
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    focus = snapshot.focus or {}
    positive = focus.get("tabindex_positive") or []
    hidden = focus.get("hidden_focusable") or (snapshot.aria or {}).get("hidden_focusable") or []
    tab_path = focus.get("tab_path") or []
    focusable = int(focus.get("focusable_count") or 0)
    controls = snapshot.controls or []
    links = snapshot.links or []
    checks: list[CheckResult] = []

    if positive:
        selector = positive[0] if isinstance(positive[0], str) else None
        checks.append(a11y_check(snapshot, check_id="A11Y-FOCUS-001", name="tabindex values are not positive", group="keyboard", status="warning", severity="medium", message="Positive tabindex values change the natural focus order.", recommendation="Prefer tabindex=\"0\" or native interactive elements instead of tabindex greater than 0.", selector=selector, affected_element_count=len(positive), wcag_reference="WCAG 2.4.3"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-FOCUS-001", name="tabindex values are not positive", group="keyboard", status="pass", severity="medium", message="No positive tabindex values were detected."))

    if hidden:
        selector = hidden[0] if isinstance(hidden[0], str) else (hidden[0] or {}).get("selector")
        checks.append(a11y_check(snapshot, check_id="A11Y-FOCUS-002", name="Focusable content is not aria-hidden", group="keyboard", status="fail", severity="high", message="Focusable content is inside an aria-hidden ancestor.", selector=selector, affected_element_count=len(hidden), wcag_reference="WCAG 4.1.2"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-FOCUS-002", name="Focusable content is not aria-hidden", group="keyboard", status="pass", severity="high", message="No hidden-and-focusable pattern was detected in the DOM snapshot."))

    interactive = len(controls) + len(links)
    if interactive == 0:
        checks.append(a11y_check(snapshot, check_id="A11Y-KEY-001", name="Keyboard can reach interactive controls", group="keyboard", status="not_applicable", severity="medium", message="No interactive controls were present for a Tab probe."))
    elif tab_path:
        unique = {item for item in tab_path if item}
        trapped = len(tab_path) >= max(4, min(KEYBOARD_TAB_LIMIT, 8)) and len(unique) <= 1 and (focusable > 1 or interactive > 1)
        if trapped:
            checks.append(a11y_check(snapshot, check_id="A11Y-KEY-001", name="Keyboard can reach interactive controls", group="keyboard", status="fail", severity="high", message="Keyboard focus appears trapped on a single control during a limited Tab probe.", recommendation="Ensure Tab can move between interactive elements. Do not intercept Tab unless a dialog is intentionally trapping focus.", selector=next(iter(unique), None), detected=f"tabs={len(tab_path)} unique={len(unique)}", wcag_reference="WCAG 2.1.1"))
        else:
            checks.append(a11y_check(snapshot, check_id="A11Y-KEY-001", name="Keyboard can reach interactive controls", group="keyboard", status="pass", severity="medium", message=f"A limited Tab probe reached {len(unique)} control(s). This does not prove complete keyboard accessibility.", detected=f"tabs={len(tab_path)} focusable={focusable}", wcag_reference="WCAG 2.1.1"))
    elif focusable == 0 and interactive:
        checks.append(a11y_check(snapshot, check_id="A11Y-KEY-001", name="Keyboard can reach interactive controls", group="keyboard", status="warning", severity="medium", message="Interactive elements were detected but none appear keyboard-focusable.", recommendation="Ensure buttons and links are reachable with the Tab key.", wcag_reference="WCAG 2.1.1", source="manual-review", manual_review=True))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-KEY-001", name="Keyboard can reach interactive controls", group="keyboard", status="warning", severity="low", message="Keyboard access was only partially probed. Manual keyboard testing is recommended.", source="manual-review", manual_review=True, wcag_reference="WCAG 2.1.1"))
    return checks
