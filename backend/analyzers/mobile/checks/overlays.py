from __future__ import annotations

from backend.analyzers.mobile.checks._util import as_float, finding
from backend.analyzers.mobile.config import DEFAULT_SCORING
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    overlays = snapshot.overlays or []
    if not overlays:
        return [
            finding(
                snapshot,
                check_id="MOBILE-OVERLAY-001",
                name="Overlay coverage",
                group="overlays",
                status="not_applicable",
                severity="medium",
                message="No overlays were measured on the initial mobile viewport.",
            )
        ]
    threshold = DEFAULT_SCORING.overlay_coverage
    first = max(overlays, key=lambda item: as_float(item.get("coverage")))
    coverage = as_float(first.get("coverage"))
    if coverage >= threshold:
        return [
            finding(
                snapshot,
                check_id="MOBILE-OVERLAY-001",
                name="Overlay coverage",
                group="overlays",
                status="warning",
                severity="medium",
                message=f"An overlay obscures a substantial portion of the mobile viewport ({int(coverage * 100)}%).",
                recommendation="Ensure promotional or consent overlays do not hide primary content on small screens.",
                selector=first.get("selector"),
                affected_element_count=len(overlays),
                measured_value=round(coverage, 3),
                expected_value=threshold,
            )
        ]
    return [
        finding(
            snapshot,
            check_id="MOBILE-OVERLAY-001",
            name="Overlay coverage",
            group="overlays",
            status="pass",
            severity="low",
            message="An overlay was detected, but it does not cover a substantial share of the mobile viewport.",
            selector=first.get("selector"),
            affected_element_count=len(overlays),
            measured_value=round(coverage, 3),
            expected_value=threshold,
        )
    ]
