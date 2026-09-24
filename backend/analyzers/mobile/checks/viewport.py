from __future__ import annotations

from backend.analyzers.mobile.checks._util import finding
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    meta = snapshot.viewport_meta or {}
    present = bool(meta.get("present"))
    checks: list[CheckResult] = []

    if not present:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-VIEW-001",
                name="Viewport meta tag",
                group="viewport",
                status="fail",
                severity="high",
                message="Viewport meta tag is missing.",
                recommendation="Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> so the page can size to the device width.",
                measured_value=None,
                expected_value="width=device-width",
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-VIEW-001",
                name="Viewport meta tag",
                group="viewport",
                status="pass",
                severity="high",
                message="A viewport meta tag is present.",
                detected=str(meta.get("content") or ""),
                measured_value=meta.get("content"),
                expected_value="width=device-width",
            )
        )

    if not present:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-VIEW-002",
                name="Viewport width configuration",
                group="viewport",
                status="not_applicable",
                severity="medium",
                message="Viewport width was not evaluated because no viewport meta tag was found.",
            )
        )
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-VIEW-003",
                name="Viewport zoom configuration",
                group="viewport",
                status="not_applicable",
                severity="medium",
                message="Viewport zoom was not evaluated because no viewport meta tag was found.",
            )
        )
        return checks

    if meta.get("fixed_width"):
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-VIEW-002",
                name="Viewport width configuration",
                group="viewport",
                status="warning",
                severity="medium",
                message="Viewport configuration uses a fixed width instead of device-width.",
                recommendation="Prefer width=device-width unless a measured layout requires a specific width.",
                detected=str(meta.get("content") or ""),
                measured_value=meta.get("width"),
                expected_value="device-width",
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-VIEW-002",
                name="Viewport width configuration",
                group="viewport",
                status="pass",
                severity="medium",
                message="Viewport width is not locked to a suspicious fixed pixel value.",
                detected=str(meta.get("content") or ""),
                measured_value=meta.get("width"),
                expected_value="device-width",
            )
        )

    if meta.get("zoom_restricted"):
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-VIEW-003",
                name="Viewport zoom configuration",
                group="viewport",
                status="warning",
                severity="medium",
                message="Viewport configuration may restrict zoom.",
                recommendation="Avoid user-scalable=no and maximum-scale=1 unless there is a measured reason to limit scaling.",
                detected=str(meta.get("content") or ""),
                measured_value=meta.get("user_scalable") or meta.get("maximum_scale"),
                expected_value="user-scalable allowed",
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-VIEW-003",
                name="Viewport zoom configuration",
                group="viewport",
                status="pass",
                severity="medium",
                message="Viewport configuration does not appear to disable zoom.",
                detected=str(meta.get("content") or ""),
            )
        )
    return checks
