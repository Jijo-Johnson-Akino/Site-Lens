from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    headings = snapshot.headings or []
    checks: list[CheckResult] = []
    if not headings:
        checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-001", name="Heading structure exists", group="headings", status="warning", severity="medium", message="No heading elements were detected.", recommendation="Use headings to outline the page structure.", wcag_reference="WCAG 1.3.1"))
        checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-002", name="Headings have accessible text", group="headings", status="not_applicable", severity="medium", message="Empty headings were not evaluated because no headings were present."))
        checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-003", name="Heading hierarchy", group="headings", status="not_applicable", severity="low", message="Heading order was not evaluated because no headings were present."))
        checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-004", name="Multiple H1 headings", group="headings", status="not_applicable", severity="low", message="H1 count was not evaluated because no headings were present."))
        return checks

    checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-001", name="Heading structure exists", group="headings", status="pass", severity="medium", message=f"{len(headings)} heading elements were detected.", wcag_reference="WCAG 1.3.1"))
    empty = [item for item in headings if item.get("empty")]
    hidden = [item for item in headings if item.get("hidden")]
    if empty:
        checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-002", name="Headings have accessible text", group="headings", status="fail", severity="medium", message=f"{len(empty)} empty heading(s) were detected.", recommendation="Give headings accessible text or remove unused heading tags.", selector=empty[0].get("selector"), affected_element_count=len(empty), wcag_reference="WCAG 1.3.1"))
    elif hidden:
        checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-002", name="Headings have accessible text", group="headings", status="warning", severity="medium", message="A heading is hidden from assistive technology with aria-hidden.", recommendation="Do not hide visually important headings from the accessibility tree.", selector=hidden[0].get("selector"), affected_element_count=len(hidden), wcag_reference="WCAG 1.3.1"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-002", name="Headings have accessible text", group="headings", status="pass", severity="medium", message="Headings expose accessible text."))

    jump = False
    jump_selector = None
    previous = headings[0].get("level") or 1
    for item in headings[1:]:
        level = int(item.get("level") or previous)
        if level > previous + 1:
            jump = True
            jump_selector = item.get("selector")
            break
        previous = level
    checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-003", name="Heading hierarchy", group="headings", status="warning" if jump else "pass", severity="low", message="A heading level was skipped." if jump else "No skipped heading levels were detected.", recommendation="Avoid skipping heading levels when outlining content." if jump else None, selector=jump_selector if jump else None, wcag_reference="WCAG 1.3.1"))

    h1s = [item for item in headings if int(item.get("level") or 0) == 1]
    if len(h1s) > 1:
        checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-004", name="Multiple H1 headings", group="headings", status="warning", severity="low", message=f"{len(h1s)} H1 headings were detected. This is a structural note, not automatically an accessibility failure.", selector=h1s[0].get("selector"), affected_element_count=len(h1s)))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-HEAD-004", name="Multiple H1 headings", group="headings", status="pass", severity="low", message="Heading outline does not use multiple H1 elements."))
    return checks
