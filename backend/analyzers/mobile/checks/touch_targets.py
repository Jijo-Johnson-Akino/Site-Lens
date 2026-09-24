from __future__ import annotations

from backend.analyzers.mobile.checks._util import as_int, finding
from backend.analyzers.mobile.config import DEFAULT_SCORING
from backend.analyzers.mobile.models import CheckResult, MobileSnapshot


def run(snapshot: MobileSnapshot) -> list[CheckResult]:
    touch = snapshot.touch_targets or {}
    items = touch.get("items") or []
    below = as_int(touch.get("below_baseline"), len(items))
    very_small = [item for item in items if item.get("very_small")]
    close_pairs = touch.get("close_pairs") or []
    baseline = DEFAULT_SCORING.touch_baseline_px
    small = DEFAULT_SCORING.touch_small_px
    total = as_int(touch.get("interactive_elements"))
    checks: list[CheckResult] = []

    if total <= 0 and not items:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TOUCH-001",
                name="Touch-target baseline",
                group="touch",
                status="not_applicable",
                severity="medium",
                message="No interactive elements were measured.",
            )
        )
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TOUCH-002",
                name="Very small touch targets",
                group="touch",
                status="not_applicable",
                severity="high",
                message="No interactive elements were measured.",
            )
        )
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TOUCH-003",
                name="Touch-target spacing",
                group="touch",
                status="not_applicable",
                severity="medium",
                message="No interactive elements were measured.",
            )
        )
        return checks

    if below:
        first = items[0] if items else {}
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TOUCH-001",
                name="Touch-target baseline",
                group="touch",
                status="warning",
                severity="medium",
                message=f"{below} interactive target{'s' if below != 1 else ''} measured below the configured touch-target baseline ({baseline}×{baseline} CSS pixels).",
                recommendation="Increase padding or hit area so controls are easier to tap on a phone.",
                selector=first.get("selector"),
                affected_element_count=below,
                measured_value=first.get("min_dim"),
                expected_value=baseline,
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TOUCH-001",
                name="Touch-target baseline",
                group="touch",
                status="pass",
                severity="medium",
                message="Measured interactive targets meet the configured touch-target baseline.",
                expected_value=baseline,
            )
        )

    if very_small:
        first = very_small[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TOUCH-002",
                name="Very small touch targets",
                group="touch",
                status="warning",
                severity="high",
                message=f"{len(very_small)} interactive target{'s' if len(very_small) != 1 else ''} measured under {small} CSS pixels.",
                recommendation="Avoid controls smaller than the configured high-warning size on mobile.",
                selector=first.get("selector"),
                affected_element_count=len(very_small),
                measured_value=first.get("min_dim"),
                expected_value=small,
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TOUCH-002",
                name="Very small touch targets",
                group="touch",
                status="pass",
                severity="high",
                message="No extremely small interactive targets were measured.",
                expected_value=small,
            )
        )

    if close_pairs:
        first = close_pairs[0]
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TOUCH-003",
                name="Touch-target spacing",
                group="touch",
                status="warning",
                severity="medium",
                message="Interactive controls overlap or sit closer than the configured spacing baseline.",
                recommendation="Increase spacing between adjacent tap targets so they are easier to activate independently.",
                selector=first.get("a"),
                affected_element_count=len(close_pairs),
                measured_value=first.get("gap"),
                expected_value=DEFAULT_SCORING.touch_gap_px,
                details={"pairs": close_pairs[:6]},
            )
        )
    else:
        checks.append(
            finding(
                snapshot,
                check_id="MOBILE-TOUCH-003",
                name="Touch-target spacing",
                group="touch",
                status="pass",
                severity="medium",
                message="No closely packed icon-like controls were measured.",
            )
        )
    return checks
