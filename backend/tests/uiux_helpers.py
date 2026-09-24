from __future__ import annotations

from pathlib import Path

from backend.analyzers.uiux.analyzer import analyze_snapshots, collect_checks
from backend.analyzers.uiux.models import UiuxResult
from backend.analyzers.uiux.stub import snapshot_from_parts

FIXTURES = Path(__file__).parent / "fixtures" / "uiux"


def load_uiux_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def by_id(result: UiuxResult, check_id: str, viewport: str):
    return next(check for check in result.checks if check.check_id == check_id and check.viewport == viewport)


def analyze_one(snapshot) -> UiuxResult:
    return analyze_snapshots([snapshot])


__all__ = ["analyze_one", "analyze_snapshots", "by_id", "collect_checks", "load_uiux_fixture", "snapshot_from_parts"]
