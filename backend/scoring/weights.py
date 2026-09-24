"""Centralized Health Score category weights. Change weights here, not in callers."""

from __future__ import annotations

import os


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


CALCULATION_VERSION = os.getenv("SITEBENCH_SCORE_VERSION", "1.0")

CATEGORY_WEIGHTS: dict[str, float] = {
    "seo": _float_env("SITEBENCH_SCORE_WEIGHT_SEO", 15),
    "aeo": _float_env("SITEBENCH_SCORE_WEIGHT_AEO", 10),
    "uiux": _float_env("SITEBENCH_SCORE_WEIGHT_UIUX", 10),
    "accessibility": _float_env("SITEBENCH_SCORE_WEIGHT_ACCESSIBILITY", 10),
    "performance": _float_env("SITEBENCH_SCORE_WEIGHT_PERFORMANCE", 15),
    "content": _float_env("SITEBENCH_SCORE_WEIGHT_CONTENT", 10),
    "structured_data": _float_env("SITEBENCH_SCORE_WEIGHT_STRUCTURED_DATA", 5),
    "mobile": _float_env("SITEBENCH_SCORE_WEIGHT_MOBILE", 10),
    "cro": _float_env("SITEBENCH_SCORE_WEIGHT_CRO", 7.5),
    "trust": _float_env("SITEBENCH_SCORE_WEIGHT_TRUST", 7.5),
}

CATEGORY_LABELS: dict[str, str] = {
    "seo": "SEO",
    "aeo": "AEO / AI Search Readiness",
    "uiux": "UI/UX",
    "accessibility": "Accessibility",
    "performance": "Performance",
    "content": "Content",
    "structured_data": "Structured Data",
    "mobile": "Mobile",
    "cro": "CRO",
    "trust": "Trust & Credibility",
}

CATEGORY_HREFS: dict[str, str] = {
    "seo": "seo",
    "aeo": "aeo",
    "uiux": "uiux",
    "accessibility": "accessibility",
    "performance": "performance",
    "content": "content",
    "structured_data": "structured-data",
    "mobile": "mobile",
    "cro": "cro",
    "trust": "trust",
}

PAYLOAD_KEYS: dict[str, str] = {
    "seo": "seo",
    "aeo": "aeo",
    "uiux": "uiux",
    "accessibility": "accessibility",
    "performance": "performance",
    "content": "content",
    "structured_data": "structured_data",
    "mobile": "mobile",
    "cro": "cro",
    "trust": "trust",
}

ERROR_KEYS: dict[str, str] = {
    "seo": "seo_error",
    "aeo": "aeo_error",
    "uiux": "uiux_error",
    "accessibility": "accessibility_error",
    "performance": "performance_error",
    "content": "content_error",
    "structured_data": "structured_data_error",
    "mobile": "mobile_error",
    "cro": "cro_error",
    "trust": "trust_error",
}

SCORE_BANDS: tuple[tuple[int, int, str], ...] = (
    (90, 100, "Excellent"),
    (75, 89, "Good"),
    (60, 74, "Needs Improvement"),
    (40, 59, "Poor"),
    (0, 39, "Critical"),
)

COVERAGE_COMPLETE = _float_env("SITEBENCH_SCORE_COVERAGE_COMPLETE", 100)
COVERAGE_PARTIAL = _float_env("SITEBENCH_SCORE_COVERAGE_PARTIAL", 80)
COVERAGE_LIMITED = _float_env("SITEBENCH_SCORE_COVERAGE_LIMITED", 50)

WEIGHT_TOTAL_TOLERANCE = 1e-6


class WeightConfigurationError(ValueError):
    """Raised when category weights are invalid."""


def validate_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    values = dict(CATEGORY_WEIGHTS if weights is None else weights)
    if not values:
        raise WeightConfigurationError("Category weights are empty.")
    for key, weight in values.items():
        if weight < 0:
            raise WeightConfigurationError(f"Category weight for {key} must be non-negative.")
    total = sum(values.values())
    if abs(total - 100) > WEIGHT_TOTAL_TOLERANCE:
        raise WeightConfigurationError(f"Category weights must total 100, got {total}.")
    return values


def configured_total(weights: dict[str, float] | None = None) -> float:
    return float(sum((CATEGORY_WEIGHTS if weights is None else weights).values()))


validate_weights(CATEGORY_WEIGHTS)
