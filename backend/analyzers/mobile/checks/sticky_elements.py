from __future__ import annotations

from backend.analyzers.mobile.checks._util import as_float, finding
from backend.analyzers.mobile.config import DEFAULT_SCORING
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    sticky = snapshot.sticky_elements or []
    if not sticky:
        return [
            finding(
                snapshot,
                check_id="MOBILE-FIXED-001",
                name="Fixed element coverage",
                group="sticky",
                status="not_applicable",
                severity="medium",
                message="No fixed or sticky elements were measured.",
            )
        ]
    threshold = DEFAULT_SCORING.fixed_coverage
    large = [item for item in sticky if as_float(item.get("coverage")) >= threshold]
    if large:
        first = max(large, key=lambda item: as_float(item.get("coverage")))
        coverage = as_float(first.get("coverage"))
        return [
            finding(
                snapshot,
                check_id="MOBILE-FIXED-001",
                name="Fixed element coverage",
                group="sticky",
                status="warning",
                severity="medium",
                message=f"A fixed element covers a large portion of the initial mobile viewport ({int(coverage * 100)}%).",
                recommendation="Reduce the height of sticky chrome, or allow it to dismiss, so primary content remains visible.",
                selector=first.get("selector"),
                affected_element_count=len(large),
                measured_value=round(coverage, 3),
                expected_value=threshold,
            )
        ]
    return [
        finding(
            snapshot,
            check_id="MOBILE-FIXED-001",
            name="Fixed element coverage",
            group="sticky",
            status="pass",
            severity="medium",
            message="Fixed and sticky elements do not occupy a large share of the mobile viewport.",
            affected_element_count=len(sticky),
        )
    ]
