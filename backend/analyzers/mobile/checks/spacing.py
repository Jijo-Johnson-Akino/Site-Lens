from __future__ import annotations

from backend.analyzers.mobile.checks._util import finding
from backend.analyzers.mobile.config import DEFAULT_SCORING
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    spacing = snapshot.spacing or {}
    edge = spacing.get("edge_text") or []
    padded = spacing.get("excessive_padding") or []
    pad = DEFAULT_SCORING.edge_padding_px
    checks: list[CheckResult] = []

    if edge:
        first = edge[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-SPACE-001",
                name="Edge padding",
                group="spacing",
                status="warning",
                severity="low",
                message="Text sits closer to the viewport edge than the configured padding baseline.",
                recommendation="Add modest horizontal padding so body text is not flush against the screen edge.",
                selector=first.get("selector"),
                affected_element_count=len(edge),
                measured_value=first.get("padding_left"),
                expected_value=pad,
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-SPACE-001",
                name="Edge padding",
                group="spacing",
                status="pass",
                severity="low",
                message="Body text is not flush against the viewport edges.",
                expected_value=pad,
            )
        )

    if padded:
        first = padded[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-SPACE-002",
                name="Content width after padding",
                group="spacing",
                status="warning",
                severity="low",
                message="Horizontal padding substantially reduces the usable content width on mobile.",
                recommendation="Reduce large side padding on small viewports so content remains readable.",
                selector=first.get("selector"),
                measured_value=first.get("inner_width"),
                expected_value=snapshot.viewport.get("width"),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-SPACE-002",
                name="Content width after padding",
                group="spacing",
                status="pass",
                severity="low",
                message="Horizontal padding does not collapse the usable content width.",
            )
        )
    return checks
