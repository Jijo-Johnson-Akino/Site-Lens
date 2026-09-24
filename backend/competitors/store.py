"""Persist competitor records on the primary scan result. Does not store copied analyzer data."""

from __future__ import annotations

from typing import Any

from backend.competitors.models import CompetitorBenchmark, CompetitorListPayload


def load_payload(result: dict[str, Any] | None) -> CompetitorListPayload:
    stored = (result or {}).get("competitors")
    if not isinstance(stored, dict):
        return CompetitorListPayload()
    items = stored.get("items")
    if not isinstance(items, list):
        return CompetitorListPayload(version=int(stored.get("version") or 1))
    parsed: list[CompetitorBenchmark] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        try:
            parsed.append(CompetitorBenchmark.model_validate(raw))
        except Exception:
            continue
    return CompetitorListPayload(version=int(stored.get("version") or 1), items=parsed)


def dump_payload(payload: CompetitorListPayload) -> dict[str, Any]:
    return payload.model_dump(mode="json")


def merge_into_result(result: dict[str, Any] | None, payload: CompetitorListPayload) -> dict[str, Any]:
    merged = dict(result or {})
    merged["competitors"] = dump_payload(payload)
    return merged
