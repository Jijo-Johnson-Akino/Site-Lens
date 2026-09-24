from __future__ import annotations

from backend.analyzers.mobile.checks._util import as_int, finding
from backend.analyzers.mobile.config import DEFAULT_SCORING
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    layout = snapshot.layout or {}
    overflow_px = as_int(layout.get("overflow_px"))
    document_width = as_int(layout.get("document_width") or layout.get("scroll_width"))
    viewport_width = as_int(layout.get("viewport_width") or snapshot.viewport.get("width"))
    overflowing = snapshot.overflowing_elements or []
    tolerance = DEFAULT_SCORING.overflow_tolerance_px
    checks: list[CheckResult] = []

    if overflow_px > tolerance:
        first = overflowing[0] if overflowing else {}
        selector = first.get("selector")
        extra = as_int(first.get("overflow_px") or overflow_px)
        cause = first.get("cause")
        message = f"Horizontal overflow detected. Document width is {document_width}px versus a {viewport_width}px viewport ({overflow_px}px overflow)."
        if selector:
            message = f"Horizontal overflow detected. Element {selector} extends {extra}px beyond the viewport."
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-OVERFLOW-001",
                name="Horizontal overflow",
                group="overflow",
                status="fail" if overflow_px >= 24 else "warning",
                severity="high" if overflow_px >= 24 else "medium",
                message=message,
                recommendation="Make the component responsive or contain the overflow within an appropriate scrollable region.",
                selector=selector,
                affected_element_count=len(overflowing) or 1,
                measured_value=overflow_px,
                expected_value=tolerance,
                details={"document_width": document_width, "viewport_width": viewport_width, "cause": cause},
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-OVERFLOW-001",
                name="Horizontal overflow",
                group="overflow",
                status="pass",
                severity="high",
                message="No horizontal overflow was measured at this mobile viewport.",
                measured_value=overflow_px,
                expected_value=tolerance,
                details={"document_width": document_width, "viewport_width": viewport_width},
            )
        )

    identified = [item for item in overflowing if item.get("cause") and item.get("cause") != "container"]
    if overflow_px > tolerance and identified:
        first = identified[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-OVERFLOW-002",
                name="Overflow source",
                group="overflow",
                status="warning",
                severity="medium",
                message=f"Likely overflow source: {first.get('cause')} ({first.get('selector')}).",
                recommendation="Inspect the identified element and related descendants for fixed widths, wide media, or unbroken text.",
                selector=first.get("selector"),
                affected_element_count=len(identified),
                measured_value=first.get("overflow_px"),
                details={"causes": [item.get("cause") for item in identified[:6]]},
            )
        )
    elif overflow_px > tolerance:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-OVERFLOW-002",
                name="Overflow source",
                group="overflow",
                status="warning",
                severity="low",
                message="Horizontal overflow was measured, but a specific child cause was not identified.",
                measured_value=overflow_px,
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-OVERFLOW-002",
                name="Overflow source",
                group="overflow",
                status="pass",
                severity="medium",
                message="No overflowing child elements were identified.",
            )
        )
    return checks
