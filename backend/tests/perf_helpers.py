from __future__ import annotations

from pathlib import Path

from backend.analyzers.performance.analyzer import analyze_snapshot
from backend.analyzers.performance.models import PerfResult, PerformanceSnapshot
from backend.analyzers.performance.stub import fast_snapshot

FIXTURES = Path(__file__).parent / "fixtures" / "perf"


def load_perf_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def by_id(result: PerfResult, check_id: str):
    return next(check for check in result.checks if check.check_id == check_id)


def snapshot_with(**overrides) -> PerformanceSnapshot:
    data = fast_snapshot().model_dump()
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            merged = dict(data[key])
            merged.update(value)
            data[key] = merged
        else:
            data[key] = value
    return PerformanceSnapshot.model_validate(data)


def analyze_dom(snapshot: PerformanceSnapshot | None = None) -> PerfResult:
    return analyze_snapshot(snapshot or fast_snapshot())
