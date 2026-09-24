from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    tables = snapshot.tables or []
    if not tables:
        return [
            a11y_check(snapshot, check_id="A11Y-TABLE-001", name="Data tables expose headers", group="tables", status="not_applicable", severity="medium", message="No tables were present."),
            a11y_check(snapshot, check_id="A11Y-TABLE-002", name="Table caption", group="tables", status="not_applicable", severity="info", message="Table captions were not evaluated because no tables were present."),
        ]
    data_tables = [item for item in tables if item.get("role") != "presentation" and item.get("role") != "none"]
    missing = [item for item in data_tables if int(item.get("headers") or 0) == 0]
    if missing:
        header_check = a11y_check(snapshot, check_id="A11Y-TABLE-001", name="Data tables expose headers", group="tables", status="warning", severity="medium", message="A table does not expose header cells.", recommendation="Use th elements (and scope where helpful) for data tables. Layout tables should use role=\"presentation\" if they are not data tables.", selector=missing[0].get("selector"), affected_element_count=len(missing), wcag_reference="WCAG 1.3.1")
    else:
        header_check = a11y_check(snapshot, check_id="A11Y-TABLE-001", name="Data tables expose headers", group="tables", status="pass", severity="medium", message="Tables expose header cells or are marked as presentational.")
    untitled = [item for item in data_tables if not item.get("caption")]
    caption_check = a11y_check(
        snapshot,
        check_id="A11Y-TABLE-002",
        name="Table caption",
        group="tables",
        status="pass",
        severity="info",
        message="Captions are optional. Missing captions were not treated as failures.",
        affected_element_count=len(untitled),
    )
    return [header_check, caption_check]
