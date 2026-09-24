from __future__ import annotations

from backend.analyzers.mobile.checks._util import finding
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    media = snapshot.media or []
    if not media:
        return [
            finding(
                snapshot,
                check_id="MOBILE-MEDIA-001",
                name="Media within the viewport",
                group="media",
                status="not_applicable",
                severity="medium",
                message="No video, audio, or embedded media was measured.",
            )
        ]
    overflowing = [item for item in media if item.get("overflowing") or item.get("fixed_width")]
    if overflowing:
        first = overflowing[0]
        return [
            finding(
                snapshot,
                check_id="MOBILE-MEDIA-001",
                name="Media within the viewport",
                group="media",
                status="warning",
                severity="medium",
                message=f"Embedded media extends beyond the mobile viewport ({first.get('selector')}).",
                recommendation="Use fluid widths for video and iframes (for example max-width: 100%).",
                selector=first.get("selector"),
                affected_element_count=len(overflowing),
                measured_value=first.get("width"),
                expected_value=snapshot.viewport.get("width"),
            )
        ]
    return [
        finding(
            snapshot,
            check_id="MOBILE-MEDIA-001",
            name="Media within the viewport",
            group="media",
            status="pass",
            severity="medium",
            message="Measured media elements fit within the mobile viewport.",
        )
    ]
