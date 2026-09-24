"""Serialize Health Score payloads for the scan API."""

from __future__ import annotations

from typing import Any

from backend.scoring.methodology import methodology_payload
from backend.scoring.models import HealthResult
from backend.scoring.weights import CALCULATION_VERSION, CATEGORY_WEIGHTS, SCORE_BANDS


def score_response(scan_id: str, health: HealthResult) -> dict[str, Any]:
    payload = health.model_dump(mode="json")
    payload["scan_id"] = scan_id
    return payload


def methodology_response(scan_id: str | None = None, health: HealthResult | None = None) -> dict[str, Any]:
    methodology = health.methodology if health else methodology_payload()
    body: dict[str, Any] = {
        "calculation_version": methodology.calculation_version or CALCULATION_VERSION,
        "weights": methodology.weights or dict(CATEGORY_WEIGHTS),
        "formula": methodology.formula,
        "score_range": methodology.score_range,
        "unavailable_behavior": methodology.unavailable_behavior,
        "rounding": methodology.rounding,
        "bands": methodology.bands or {label: f"{low}–{high}" for low, high, label in SCORE_BANDS},
        "coverage_rules": methodology.coverage_rules,
        "limitations": health.limitations if health else [],
        "score_note": health.score_note if health else None,
    }
    if scan_id:
        body["scan_id"] = scan_id
    if health:
        body["coverage"] = health.coverage.model_dump(mode="json")
    return body
