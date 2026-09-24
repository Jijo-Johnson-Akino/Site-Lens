from __future__ import annotations

from backend.analyzers.mobile.checks._util import finding
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    tables = snapshot.tables or []
    checks: list[CheckResult] = []
    if not tables:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TABLE-001",
                name="Table page overflow",
                group="tables",
                status="not_applicable",
                severity="medium",
                message="No tables were measured.",
            )
        )
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TABLE-002",
                name="Isolated table scrolling",
                group="tables",
                status="not_applicable",
                severity="low",
                message="No tables were measured.",
            )
        )
        return checks

    page_wide = [item for item in tables if item.get("page_wide")]
    isolated = [item for item in tables if item.get("overflowing") and item.get("isolated_scroll")]
    if page_wide:
        first = page_wide[0]
        extra = int(first.get("overflow_px") or 0)
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TABLE-001",
                name="Table page overflow",
                group="tables",
                status="warning" if extra < 80 else "fail",
                severity="high" if extra >= 80 else "medium",
                message=f"A table causes page-wide horizontal overflow ({first.get('selector')}).",
                recommendation="Wrap wide tables in a locally scrollable container or stack the rows on small screens.",
                selector=first.get("selector"),
                affected_element_count=len(page_wide),
                measured_value=first.get("width"),
                expected_value=snapshot.viewport.get("width"),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TABLE-001",
                name="Table page overflow",
                group="tables",
                status="pass",
                severity="high",
                message="No table causes page-wide horizontal overflow.",
            )
        )

    if isolated and not page_wide:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TABLE-002",
                name="Isolated table scrolling",
                group="tables",
                status="pass",
                severity="low",
                message="Wide tables are contained in a local scroll region rather than expanding the page.",
                affected_element_count=len(isolated),
            )
        )
    elif isolated:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TABLE-002",
                name="Isolated table scrolling",
                group="tables",
                status="warning",
                severity="low",
                message="Some tables scroll locally, but at least one still expands the page.",
                affected_element_count=len(isolated),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TABLE-002",
                name="Isolated table scrolling",
                group="tables",
                status="pass" if not page_wide else "warning",
                severity="low",
                message="No locally scrollable table containers were required." if not page_wide else "Wide tables are not isolated in a scroll container.",
            )
        )
    return checks
