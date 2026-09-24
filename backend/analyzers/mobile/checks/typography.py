from __future__ import annotations

from backend.analyzers.mobile.checks._util import as_float, finding
from backend.analyzers.mobile.config import DEFAULT_SCORING
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    small = snapshot.small_text or []
    clipped = snapshot.clipped_text or []
    overflowing_headings = snapshot.overflowing_headings or []
    warn_px = DEFAULT_SCORING.min_font_warn_px
    high_px = DEFAULT_SCORING.min_font_high_px
    high = [item for item in small if item.get("high") or as_float(item.get("font_size"), 99) < high_px]
    checks: list[CheckResult] = []

    if high:
        first = high[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TYPE-001",
                name="Text size",
                group="typography",
                status="warning",
                severity="high",
                message=f"Text is below the configured high-warning size ({as_float(first.get('font_size')):.1f}px).",
                recommendation="Increase body and control text that is smaller than the configured minimum on mobile.",
                selector=first.get("selector"),
                affected_element_count=len(high),
                measured_value=first.get("font_size"),
                expected_value=high_px,
            )
        )
    elif small:
        first = small[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TYPE-001",
                name="Text size",
                group="typography",
                status="warning",
                severity="medium",
                message=f"Text is below the configured minimum size ({as_float(first.get('font_size')):.1f}px).",
                recommendation="Review small labels and body copy that may be hard to read on a 390px viewport.",
                selector=first.get("selector"),
                affected_element_count=len(small),
                measured_value=first.get("font_size"),
                expected_value=warn_px,
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TYPE-001",
                name="Text size",
                group="typography",
                status="pass",
                severity="medium",
                message="No substantial text was measured below the configured mobile minimum.",
                expected_value=warn_px,
            )
        )

    if clipped:
        first = clipped[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TYPE-002",
                name="Clipped text",
                group="typography",
                status="warning",
                severity="medium",
                message=f"Text appears clipped on mobile ({first.get('selector')}).",
                recommendation="Allow wrapping or increase the container size so labels and headings remain readable.",
                selector=first.get("selector"),
                affected_element_count=len(clipped),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TYPE-002",
                name="Clipped text",
                group="typography",
                status="pass",
                severity="medium",
                message="No clipped text blocks were measured.",
            )
        )

    if overflowing_headings:
        first = overflowing_headings[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TYPE-003",
                name="Overflowing headings",
                group="typography",
                status="warning",
                severity="medium",
                message=f"A heading extends beyond the mobile viewport ({first.get('selector')}).",
                recommendation="Allow headings to wrap instead of overflowing horizontally.",
                selector=first.get("selector"),
                affected_element_count=len(overflowing_headings),
                measured_value=first.get("overflow_px"),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TYPE-003",
                name="Overflowing headings",
                group="typography",
                status="pass",
                severity="medium",
                message="No headings were measured overflowing the viewport.",
            )
        )
    return checks
