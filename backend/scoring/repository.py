"""Persist Health Score on the existing scan result payload. No separate table."""

from __future__ import annotations

from typing import Any

from backend.scoring.engine import score_scan_result
from backend.scoring.models import HealthResult


def health_from_result(result: dict[str, Any] | None) -> HealthResult | None:
    payload = (result or {}).get("health")
    if isinstance(payload, dict) and payload.get("overall") is not None:
        return HealthResult.model_validate(payload)
    return None


def attach_health(result: dict[str, Any]) -> HealthResult:
    health = score_scan_result(result)
    result["health"] = health.model_dump(mode="json")
    result.pop("health_error", None)
    return health
