from __future__ import annotations

from backend.analyzers.mobile.checks._util import finding
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    content = snapshot.content or {}
    headings = snapshot.headings or []
    h1_clipped = bool(content.get("h1_clipped") or any(item.get("clipped") for item in headings))
    h1_visible = bool(content.get("h1_visible") or any(item.get("visible") for item in headings))
    h1_in = bool(content.get("h1_in_viewport") or any(item.get("in_viewport") for item in headings))
    main_visible = bool(content.get("main_visible"))
    checks: list[CheckResult] = []

    if not headings:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-CONTENT-001",
                name="Primary heading visibility",
                group="visibility",
                status="not_applicable",
                severity="medium",
                message="No H1 was measured.",
            )
        )
    elif h1_clipped or (h1_visible and not h1_in):
        first = headings[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-CONTENT-001",
                name="Primary heading visibility",
                group="visibility",
                status="warning",
                severity="medium",
                message="The primary heading is clipped or outside the mobile viewport.",
                recommendation="Keep the H1 readable without horizontal scrolling or overlay clipping.",
                selector=first.get("selector"),
                measured_value=first.get("overflow_px"),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-CONTENT-001",
                name="Primary heading visibility",
                group="visibility",
                status="pass",
                severity="medium",
                message="The primary heading remains visible on the mobile viewport.",
            )
        )

    checks.append(
        finding(
            snapshot,
            check_id="MOBILE-CONTENT-002",
            name="Main content visibility",
            group="visibility",
            status="pass" if main_visible else "warning",
            severity="medium",
            message="Main content is visible on mobile." if main_visible else "Main content was not clearly visible in the mobile viewport.",
            recommendation=None if main_visible else "Check overlays, off-screen positioning, or collapsed containers hiding the main region.",
            selector=content.get("main_selector"),
        )
    )
    return checks
