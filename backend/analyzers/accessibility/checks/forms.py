from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    fields = snapshot.fields or []
    forms = snapshot.forms or []
    checks: list[CheckResult] = []
    if not fields and not forms:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-001", name="Form controls have accessible names", group="forms", status="not_applicable", severity="high", message="No form fields were present."))
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-002", name="Related controls are grouped", group="forms", status="not_applicable", severity="low", message="Fieldsets were not evaluated because no form fields were present."))
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-003", name="Submit controls have accessible names", group="forms", status="not_applicable", severity="medium", message="Submit controls were not evaluated because no form was present."))
        return checks

    unnamed = [item for item in fields if not item.get("named")]
    if unnamed:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-001", name="Form controls have accessible names", group="forms", status="fail", severity="high", message=f"{len(unnamed)} form field(s) have no associated label or accessible name.", recommendation="Associate a label, or provide aria-label / aria-labelledby. A visible label is preferred but an accessible name is sufficient.", selector=unnamed[0].get("selector"), affected_element_count=len(unnamed), wcag_reference="WCAG 1.3.1"))
    elif fields:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-001", name="Form controls have accessible names", group="forms", status="pass", severity="high", message="Form fields expose an accessible name.", wcag_reference="WCAG 1.3.1"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-001", name="Form controls have accessible names", group="forms", status="not_applicable", severity="high", message="No form fields were present."))

    missing_groups = int(snapshot.radio_groups_without_fieldset or 0)
    if snapshot.radio_groups and missing_groups:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-002", name="Related controls are grouped", group="forms", status="warning", severity="low", message="Radio controls are not grouped in a fieldset with a legend.", recommendation="Group related radio or checkbox controls with fieldset and legend where it helps.", wcag_reference="WCAG 1.3.1"))
    elif snapshot.radio_groups:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-002", name="Related controls are grouped", group="forms", status="pass", severity="low", message="Related radio controls appear grouped."))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-002", name="Related controls are grouped", group="forms", status="not_applicable", severity="low", message="No radio groups were present."))

    unnamed_submit = [item for item in forms if item.get("has_submit") and not item.get("submit_named")]
    no_submit = [item for item in forms if not item.get("has_submit")]
    if unnamed_submit:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-003", name="Submit controls have accessible names", group="forms", status="fail", severity="medium", message="A form submit control has no accessible name.", selector=unnamed_submit[0].get("selector"), affected_element_count=len(unnamed_submit), wcag_reference="WCAG 4.1.2"))
    elif forms and not no_submit:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-003", name="Submit controls have accessible names", group="forms", status="pass", severity="medium", message="Form submit controls expose accessible names."))
    elif not forms:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-003", name="Submit controls have accessible names", group="forms", status="not_applicable", severity="medium", message="No forms were present."))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-FORM-003", name="Submit controls have accessible names", group="forms", status="warning", severity="low", message="A form does not expose a submit control with an accessible name."))
    return checks
