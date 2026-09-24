from __future__ import annotations

from backend.analyzers.uiux.checks._util import ux_check
from backend.analyzers.uiux.models import CheckResult, ViewportSnapshot


def run(snapshot: ViewportSnapshot) -> list[CheckResult]:
    forms = [item for item in (snapshot.forms or []) if item.get("visible") or item.get("fields")]
    checks: list[CheckResult] = []

    if forms:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-FORM-001",
                name="Visible form exists",
                group="forms",
                status="pass",
                severity="low",
                message=f"{len(forms)} visible form{'' if len(forms) == 1 else 's'} detected.",
                detected=str(len(forms)),
                affected_element=forms[0].get("selector"),
            )
        )
        unlabeled = [item for item in forms if item.get("fields") and int(item.get("labeled") or 0) < int(item.get("fields") or 0)]
        if unlabeled:
            first = unlabeled[0]
            checks.append(
                ux_check(
                    snapshot,
                    check_id="UX-FORM-002",
                    name="Form fields have labels",
                    group="forms",
                    status="warning",
                    severity="medium",
                    message="A visible form has fields without an associated label or accessible name.",
                    recommendation="Associate a visible label or accessible name with each form field.",
                    detected=f"labeled={first.get('labeled')} of {first.get('fields')}",
                    affected_element=first.get("selector"),
                    why="This is a basic UI observation, not a full accessibility audit.",
                )
            )
        else:
            checks.append(
                ux_check(
                    snapshot,
                    check_id="UX-FORM-002",
                    name="Form fields have labels",
                    group="forms",
                    status="pass",
                    severity="medium",
                    message="Visible form fields have an associated label, name, or placeholder.",
                )
            )
        missing_submit = [item for item in forms if not item.get("has_submit")]
        if missing_submit:
            checks.append(
                ux_check(
                    snapshot,
                    check_id="UX-FORM-003",
                    name="Form has a submit control",
                    group="forms",
                    status="fail",
                    severity="medium",
                    message="A visible form does not have a submit control.",
                    recommendation="Provide a visible submit button or equivalent submit control.",
                    affected_element=missing_submit[0].get("selector"),
                )
            )
        else:
            checks.append(
                ux_check(
                    snapshot,
                    check_id="UX-FORM-003",
                    name="Form has a submit control",
                    group="forms",
                    status="pass",
                    severity="medium",
                    message="Visible forms include a submit control.",
                )
            )
    else:
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-FORM-001",
                name="Visible form exists",
                group="forms",
                status="not_applicable",
                severity="low",
                message="No visible form was detected on this page.",
            )
        )
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-FORM-002",
                name="Form fields have labels",
                group="forms",
                status="not_applicable",
                severity="medium",
                message="Form labels were not evaluated because no form was detected.",
            )
        )
        checks.append(
            ux_check(
                snapshot,
                check_id="UX-FORM-003",
                name="Form has a submit control",
                group="forms",
                status="not_applicable",
                severity="medium",
                message="Submit controls were not evaluated because no form was detected.",
            )
        )
    return checks
