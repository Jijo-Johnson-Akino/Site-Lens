from __future__ import annotations

from backend.analyzers.mobile.checks._util import finding
from backend.analyzers.mobile.config import DEFAULT_SCORING
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    images = [item for item in snapshot.images or [] if item.get("visible")]
    checks: list[CheckResult] = []
    if not images:
        for check_id, name in (
            ("MOBILE-IMG-001", "Image width"),
            ("MOBILE-IMG-002", "Image overflow"),
            ("MOBILE-IMG-003", "Responsive image sizing"),
        ):
            checks.append(
                finding(
                    snapshot,
                    check_id=check_id,
                    name=name,
                    group="images",
                    status="not_applicable",
                    severity="medium",
                    message="No visible images were measured.",
                )
            )
        return checks

    oversized = [item for item in images if item.get("overflowing")]
    if oversized:
        first = oversized[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-IMG-001",
                name="Image width",
                group="images",
                status="warning",
                severity="medium",
                message=f"An image exceeds the mobile viewport width ({first.get('selector')}).",
                recommendation="Use max-width: 100% or responsive srcset/sizes so images fit the viewport.",
                selector=first.get("selector"),
                affected_element_count=len(oversized),
                measured_value=first.get("width"),
                expected_value=snapshot.viewport.get("width"),
            )
        )
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-IMG-002",
                name="Image overflow",
                group="images",
                status="warning",
                severity="medium",
                message=f"An image contributes to overflow on mobile ({first.get('selector')}).",
                selector=first.get("selector"),
                affected_element_count=len(oversized),
                measured_value=first.get("overflow_px"),
                expected_value=DEFAULT_SCORING.overflow_tolerance_px,
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-IMG-001",
                name="Image width",
                group="images",
                status="pass",
                severity="medium",
                message="Visible images fit within the mobile viewport width.",
            )
        )
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-IMG-002",
                name="Image overflow",
                group="images",
                status="pass",
                severity="medium",
                message="No overflowing images were measured.",
            )
        )

    responsive = [item for item in images if item.get("responsive") or item.get("srcset") or item.get("max_width") == "100%"]
    if oversized and not responsive:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-IMG-003",
                name="Responsive image sizing",
                group="images",
                status="warning",
                severity="low",
                message="Oversized images do not show responsive sizing attributes such as max-width: 100% or srcset.",
                recommendation="Add fluid sizing (max-width: 100%) and consider srcset/sizes for mobile.",
                affected_element_count=len(oversized),
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-IMG-003",
                name="Responsive image sizing",
                group="images",
                status="pass",
                severity="low",
                message="Images use responsive sizing or remain within the viewport.",
            )
        )
    return checks
