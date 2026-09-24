from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    land = snapshot.landmarks or {}
    mains = int(land.get("main") or 0)
    navs = int(land.get("nav") or 0)
    unnamed = int(land.get("unnamed_navs") or 0)
    skip = snapshot.skip or {}
    checks: list[CheckResult] = []

    if mains == 1:
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-001", name="Main landmark exists", group="landmarks", status="pass", severity="high", message="A main landmark is present.", wcag_reference="WCAG 1.3.1", selector="main"))
    elif mains == 0:
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-001", name="Main landmark exists", group="landmarks", status="warning", severity="medium", message="No main landmark was detected.", recommendation="Wrap primary content in a main element or role=\"main\".", wcag_reference="WCAG 1.3.1"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-001", name="Main landmark exists", group="landmarks", status="pass", severity="high", message="A main landmark is present.", selector="main"))

    if mains > 1:
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-002", name="A single main landmark", group="landmarks", status="fail", severity="medium", message=f"{mains} main landmarks were detected.", recommendation="Keep a single main landmark so assistive technology can skip to the primary content.", affected_element_count=mains, wcag_reference="WCAG 1.3.1", selector="main"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-002", name="A single main landmark", group="landmarks", status="pass" if mains else "not_applicable", severity="medium", message="No duplicate main landmarks were detected."))

    if navs >= 2 and unnamed >= 2:
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-003", name="Landmarks have distinguishable names", group="landmarks", status="warning", severity="medium", message="Multiple navigation landmarks were found without distinguishing accessible names.", recommendation="Give each nav a unique aria-label when more than one is present.", affected_element_count=navs, wcag_reference="WCAG 1.3.1", selector="nav"))
    elif navs:
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-003", name="Landmarks have distinguishable names", group="landmarks", status="pass", severity="low", message="Navigation landmarks are distinguishable or only one nav is present."))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-003", name="Landmarks have distinguishable names", group="landmarks", status="not_applicable", severity="low", message="No navigation landmarks were present."))

    if skip.get("exists"):
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-004", name="Skip navigation mechanism", group="landmarks", status="pass", severity="low", message="A skip link was detected.", selector=skip.get("selector"), wcag_reference="WCAG 2.4.1"))
    elif navs:
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-004", name="Skip navigation mechanism", group="landmarks", status="warning", severity="low", message="Repeated navigation was detected without a skip link.", recommendation="Consider providing a skip link to help keyboard users bypass repeated navigation.", wcag_reference="WCAG 2.4.1"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-LAND-004", name="Skip navigation mechanism", group="landmarks", status="not_applicable", severity="low", message="A skip link was not required because no primary navigation landmark was detected."))
    return checks
