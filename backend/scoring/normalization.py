"""Normalize analyzer scores onto a 0–100 scale without inventing values."""

from __future__ import annotations

from typing import Any


class InvalidScoreError(ValueError):
    """Analyzer returned a score that cannot be used."""


def infer_source_scale(payload: dict[str, Any] | None) -> float:
    """Use an explicit analyzer scale when present. Default is 0–100 (current analyzers)."""
    if not isinstance(payload, dict):
        return 100.0
    for key in ("score_scale", "score_max", "max_score"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if value > 0:
            return float(value)
    return 100.0


def extract_raw_score(payload: dict[str, Any] | None) -> Any:
    if not isinstance(payload, dict):
        return None
    for key in ("score", "weighted_score", "overall_score"):
        if key in payload and payload.get(key) is not None:
            return payload.get(key)
    nested = payload.get("summary")
    if isinstance(nested, dict) and nested.get("score") is not None:
        return nested.get("score")
    return None


def normalize_score(raw_score: Any, source_scale: float = 100) -> dict[str, Any]:
    """Return {score, available} or raise InvalidScoreError for out-of-range values."""
    if raw_score is None or isinstance(raw_score, bool):
        return {"score": None, "available": False, "raw": None}
    if not isinstance(raw_score, (int, float)):
        try:
            raw_score = float(str(raw_score).strip())
        except (TypeError, ValueError):
            raise InvalidScoreError("Analyzer score is not numeric.") from None
    if source_scale <= 0:
        raise InvalidScoreError("Score source scale must be positive.")
    if raw_score < 0 or raw_score > source_scale:
        raise InvalidScoreError("Analyzer score is outside the expected range.")
    scaled = (float(raw_score) / source_scale) * 100.0
    return {"score": scaled, "available": True, "raw": float(raw_score)}


def display_score(value: float | None) -> int | None:
    if value is None:
        return None
    return int(round(value))


def display_contribution(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)
