from __future__ import annotations

from backend.analyzers.mobile.checks._util import finding
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    nav = snapshot.navigation or {}
    exists = bool(nav.get("exists"))
    visible = bool(nav.get("visible"))
    menu = nav.get("menu_button")
    overflow = bool(nav.get("overflow"))
    tested = bool(nav.get("menu_tested"))
    opened = bool(nav.get("menu_opened"))
    named = bool(nav.get("menu_named"))
    checks: list[CheckResult] = []

    if not exists:
        for check_id, name, message in (
            ("MOBILE-NAV-001", "Mobile navigation visibility", "No primary navigation was detected, so mobile navigation was not evaluated."),
            ("MOBILE-NAV-002", "Mobile menu control", "No primary navigation was detected, so a menu control was not evaluated."),
            ("MOBILE-NAV-003", "Mobile menu overflow", "No primary navigation was detected, so menu overflow was not evaluated."),
            ("MOBILE-NAV-004", "Menu control name", "No primary navigation was detected, so menu naming was not evaluated."),
        ):
            checks.append(
                finding(
                    snapshot,
                    check_id=check_id,
                    name=name,
                    group="navigation",
                    status="not_applicable",
                    severity="medium",
                    message=message,
                )
            )
        return checks

    if visible or menu:
        status = "warning" if overflow and not menu else "pass"
        if not visible and menu and tested and not opened:
            status = "fail"
        message = "Mobile navigation is visible or a menu control is present."
        if status == "fail":
            message = "A menu control was found but navigation did not become visible after a safe open attempt."
        elif overflow and not menu:
            message = "Navigation items overflow the mobile viewport and no menu control was detected."
            status = "fail"
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-NAV-001",
                name="Mobile navigation visibility",
                group="navigation",
                status=status,
                severity="high",
                message=message,
                recommendation="Keep navigation reachable with a visible menu control that opens within the viewport." if status != "pass" else None,
                selector=menu,
                detected=f"visible={visible} menu={menu or 'none'} opened={opened}",
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-NAV-001",
                name="Mobile navigation visibility",
                group="navigation",
                status="fail",
                severity="high",
                message="Mobile navigation is not visible and no menu control was detected.",
                recommendation="Provide a reachable mobile menu or keep navigation usable at this viewport.",
            )
        )

    if menu:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-NAV-002",
                name="Mobile menu control",
                group="navigation",
                status="pass" if (not tested or opened or nav.get("reason") == "interaction_failed") else "warning",
                severity="medium",
                message=(
                    "A mobile menu control was detected"
                    + (" and opened during a safe interaction." if opened else (" but could not be opened." if tested else "."))
                ),
                selector=menu,
                detected=f"tested={tested} opened={opened} reason={nav.get('reason')}",
            )
        )
        if tested and opened and nav.get("menu_overflow_after_open"):
            nav_status = "warning"
            nav_message = "The opened mobile menu extends outside the viewport."
        elif overflow and not opened:
            nav_status = "warning"
            nav_message = "Navigation items overflow the viewport."
        else:
            nav_status = "pass"
            nav_message = "The mobile menu does not appear to overflow the viewport."
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-NAV-003",
                name="Mobile menu overflow",
                group="navigation",
                status=nav_status,
                severity="medium",
                message=nav_message,
                selector=menu,
            )
        )
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-NAV-004",
                name="Menu control name",
                group="navigation",
                status="pass" if named else "warning",
                severity="low",
                message="The menu control has a visible or accessible name." if named else "The menu control does not expose a measurable name.",
                recommendation=None if named else "Give the menu control a short visible or accessible name so it can be identified on a small screen.",
                selector=menu,
                detected=nav.get("menu_name"),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-NAV-002",
                name="Mobile menu control",
                group="navigation",
                status="not_applicable" if visible and not overflow else "warning",
                severity="medium",
                message="No dedicated mobile menu control was detected." if overflow or not visible else "A dedicated menu control was not required because navigation remains visible.",
            )
        )
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-NAV-003",
                name="Mobile menu overflow",
                group="navigation",
                status="warning" if overflow else "pass",
                severity="medium",
                message="Navigation items overflow the mobile viewport." if overflow else "Navigation does not overflow the mobile viewport.",
                selector=nav.get("overflow_selector"),
                measured_value=nav.get("overflow_px"),
            )
        )
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-NAV-004",
                name="Menu control name",
                group="navigation",
                status="not_applicable",
                severity="low",
                message="Menu naming was not evaluated because no menu control was detected.",
            )
        )
    return checks
