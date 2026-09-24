"""Score coverage from available category weights. This is not statistical confidence."""

from __future__ import annotations

from backend.scoring.models import ScoreCoverage
from backend.scoring.weights import COVERAGE_COMPLETE, COVERAGE_LIMITED, COVERAGE_PARTIAL

COVERAGE_EXPLANATION = (
    "Score coverage reflects how much of the configured scoring model was supported by completed analysis. "
    "It is not a statistical confidence interval."
)


def coverage_status(percent: float | None) -> str:
    if percent is None:
        return "unavailable"
    if percent >= COVERAGE_COMPLETE:
        return "complete"
    if percent >= COVERAGE_PARTIAL:
        return "partial"
    if percent >= COVERAGE_LIMITED:
        return "limited"
    return "unavailable"


def build_coverage(*, configured_weight: float, available_weight: float, configured_categories: int, available_categories: int) -> ScoreCoverage:
    if configured_weight <= 0:
        percent = None
        status = "unavailable"
    else:
        percent = (available_weight / configured_weight) * 100.0
        status = coverage_status(percent)
    return ScoreCoverage(
        configured_weight=configured_weight,
        available_weight=available_weight,
        coverage_percent=None if percent is None else round(percent, 2),
        status=status,  # type: ignore[arg-type]
        available_categories=available_categories,
        configured_categories=configured_categories,
        explanation=COVERAGE_EXPLANATION,
    )
