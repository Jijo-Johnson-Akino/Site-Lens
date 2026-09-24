from __future__ import annotations

from backend.analyzers.mobile.checks._util import as_int, finding
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    forms = snapshot.forms or []
    checks: list[CheckResult] = []
    if not forms:
        for check_id, name in (
            ("MOBILE-FORM-001", "Form overflow"),
            ("MOBILE-FORM-002", "Controls inside the viewport"),
            ("MOBILE-FORM-003", "Mobile input hints"),
        ):
            checks.append(
                finding(
                    snapshot,
                    check_id=check_id,
                    name=name,
                    group="forms",
                    status="not_applicable",
                    severity="medium",
                    message="No forms were measured on this page.",
                )
            )
        return checks

    overflowing = [item for item in forms if item.get("overflowing") and not item.get("isolated_scroll")]
    outside = sum(as_int(item.get("controls_outside")) for item in forms)
    if overflowing:
        first = overflowing[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-FORM-001",
                name="Form overflow",
                group="forms",
                status="warning",
                severity="medium",
                message=f"A form extends beyond the mobile viewport ({first.get('selector')}).",
                recommendation="Use fluid form widths and avoid fixed layouts that require horizontal scrolling of the page.",
                selector=first.get("selector"),
                affected_element_count=len(overflowing),
                measured_value=first.get("width"),
                expected_value=snapshot.viewport.get("width"),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-FORM-001",
                name="Form overflow",
                group="forms",
                status="pass",
                severity="medium",
                message="Measured forms stay within the mobile viewport or a local scroll region.",
            )
        )

    if outside:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-FORM-002",
                name="Controls inside the viewport",
                group="forms",
                status="warning",
                severity="medium",
                message=f"{outside} form control{'s' if outside != 1 else ''} extend outside the mobile viewport.",
                recommendation="Keep inputs, labels, and submit controls fully visible without horizontal panning.",
                affected_element_count=outside,
                measured_value=outside,
                expected_value=0,
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-FORM-002",
                name="Controls inside the viewport",
                group="forms",
                status="pass",
                severity="medium",
                message="Form controls stay inside the mobile viewport.",
            )
        )

    email_like = []
    for form in forms:
        for control in form.get("controls") or []:
            ctype = str(control.get("type") or "")
            name = str(control.get("selector") or "")
            if "email" in name and ctype == "text" and not control.get("inputmode"):
                email_like.append(control)
            if ctype in {"tel", "email", "number", "search"}:
                continue
    if email_like:
        first = email_like[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-FORM-003",
                name="Mobile input hints",
                group="forms",
                status="warning",
                severity="low",
                message="An email-like field uses type=text without inputmode or autocomplete hints.",
                recommendation="Where appropriate, use type=email, inputmode, or autocomplete to improve mobile keyboards. This is not required on every field.",
                selector=first.get("selector"),
                affected_element_count=len(email_like),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-FORM-003",
                name="Mobile input hints",
                group="forms",
                status="pass",
                severity="low",
                message="No measured email-like fields lacked a specific input type or inputmode.",
            )
        )
    return checks
