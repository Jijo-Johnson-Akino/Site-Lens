from __future__ import annotations

from backend.analyzers.mobile.checks._util import as_int, finding
from backend.analyzers.mobile.config import DEFAULT_SCORING
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    cta = snapshot.cta or {}
    exists = bool(cta.get("exists"))
    checks: list[CheckResult] = []
    if not exists:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-CTA-001",
                name="Primary CTA visibility",
                group="cta",
                status="not_applicable",
                severity="medium",
                message="No primary CTA candidate was detected, so mobile CTA visibility was not scored.",
            )
        )
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-CTA-002",
                name="CTA touch target",
                group="cta",
                status="not_applicable",
                severity="low",
                message="No primary CTA candidate was detected.",
            )
        )
        return checks

    clipped = bool(cta.get("clipped")) or not bool(cta.get("in_viewport"))
    if clipped:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-CTA-001",
                name="Primary CTA visibility",
                group="cta",
                status="warning",
                severity="medium",
                message="Primary CTA candidate is partially outside the mobile viewport.",
                recommendation="Keep the primary action fully visible without horizontal panning.",
                selector=cta.get("selector"),
                measured_value=cta.get("overflow_px"),
                expected_value=0,
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-CTA-001",
                name="Primary CTA visibility",
                group="cta",
                status="pass",
                severity="medium",
                message="The primary CTA candidate is visible within the mobile viewport.",
                selector=cta.get("selector"),
            )
        )

    min_dim = as_int(cta.get("min_dim") or min(as_int(cta.get("width"), 99), as_int(cta.get("height"), 99)))
    baseline = DEFAULT_SCORING.touch_baseline_px
    if min_dim and min_dim < baseline:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-CTA-002",
                name="CTA touch target",
                group="cta",
                status="warning",
                severity="medium",
                message="The primary CTA candidate is below the configured touch-target baseline.",
                recommendation="Increase the tap area of the primary action on mobile.",
                selector=cta.get("selector"),
                measured_value=min_dim,
                expected_value=baseline,
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-CTA-002",
                name="CTA touch target",
                group="cta",
                status="pass",
                severity="low",
                message="The primary CTA candidate meets the configured touch-target baseline.",
                selector=cta.get("selector"),
                measured_value=min_dim,
                expected_value=baseline,
            )
        )
    return checks
