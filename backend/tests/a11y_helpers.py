from __future__ import annotations

from pathlib import Path

from backend.analyzers.accessibility.analyzer import analyze_snapshot, collect_dom_checks
from backend.analyzers.accessibility.models import A11yResult, AccessibleSnapshot, CheckResult
from backend.analyzers.accessibility.stub import accessible_snapshot

FIXTURES = Path(__file__).parent / "fixtures" / "a11y"


def load_a11y_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def by_id(result: A11yResult | list[CheckResult], check_id: str) -> CheckResult:
    checks = result if isinstance(result, list) else result.checks
    return next(check for check in checks if check.check_id == check_id)


def snapshot_with(**overrides) -> AccessibleSnapshot:
    data = accessible_snapshot().model_dump()
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            merged = dict(data[key])
            merged.update(value)
            data[key] = merged
        else:
            data[key] = value
    return AccessibleSnapshot.model_validate(data)


def analyze_dom(snapshot: AccessibleSnapshot | None = None, axe: dict | None = None) -> A11yResult:
    return analyze_snapshot(snapshot or accessible_snapshot(), axe)


__all__ = [
    "analyze_dom",
    "analyze_snapshot",
    "by_id",
    "collect_dom_checks",
    "load_a11y_fixture",
    "snapshot_with",
]
