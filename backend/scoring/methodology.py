"""Public Health Score methodology copy. Aggregation only — no ranking or business predictions."""

from __future__ import annotations

from backend.scoring.models import ScoreMethodology
from backend.scoring.weights import CALCULATION_VERSION, CATEGORY_WEIGHTS, SCORE_BANDS

FORMULA = "Weighted average of available category scores with available-weight normalization"

UNAVAILABLE_BEHAVIOR = (
    "Unavailable or failed categories are excluded from the overall score. "
    "Their configured weights are omitted and the remaining weights are renormalized. "
    "Missing analysis is not treated as a score of zero."
)

ROUNDING = (
    "Internal calculations keep full floating-point precision. "
    "The overall score is rounded to an integer only for presentation. "
    "Weighted contributions are rounded to two decimal places for display."
)

SCORE_NOTE = (
    "The SiteLens Health Score is a composite website analysis metric based on the categories included in the scan. "
    "It is not a prediction of search rankings, traffic, revenue, conversions, business success, or user trust."
)

COVERAGE_NOTE = (
    "Score coverage reflects how much of the configured scoring model was supported by completed analysis. "
    "It is not a statistical confidence interval."
)

LIMITATIONS = [
    "Each category score is calculated by its analyzer. The Health Score does not recalculate those checks or subtract issue counts again.",
    "Unavailable analyzers are excluded rather than scored as zero.",
    "The score does not predict search rankings, traffic, revenue, conversions, or business outcomes.",
    "The score is not a legal, accessibility-compliance, security-certification, or trustworthiness determination.",
    "Website Architecture is informational and is not included in the weighted overall score.",
]

PARTIAL_NOTICE = (
    "Some analysis categories were unavailable. The overall score uses the available categories and renormalizes their configured weights."
)

LIMITED_NOTICE = "Limited analysis data is available. Treat the overall score as provisional."

UNAVAILABLE_NOTICE = "Health score unavailable"


def methodology_payload(weights: dict[str, float] | None = None) -> ScoreMethodology:
    bands = {label: f"{low}–{high}" for low, high, label in SCORE_BANDS}
    return ScoreMethodology(
        calculation_version=CALCULATION_VERSION,
        weights=dict(weights or CATEGORY_WEIGHTS),
        formula=FORMULA,
        score_range=[0, 100],
        unavailable_behavior=UNAVAILABLE_BEHAVIOR,
        rounding=ROUNDING,
        bands=bands,
        coverage_rules={
            "complete": "100% of configured category weight is available",
            "partial": "80% to 99.99% of configured category weight is available",
            "limited": "50% to 79.99% of configured category weight is available",
            "unavailable": "Less than 50% of configured category weight is available, or no usable category scores exist",
        },
    )


def band_for(score: int | None) -> str | None:
    if score is None:
        return None
    for low, high, label in SCORE_BANDS:
        if low <= score <= high:
            return label
    return None
