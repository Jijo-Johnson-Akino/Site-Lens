from __future__ import annotations

from pathlib import Path

from backend.analyzers.mobile.analyzer import analyze_snapshot
from backend.analyzers.mobile.models import MobileResult
from backend.analyzers.mobile.stub import snapshot_from_parts

FIXTURES = Path(__file__).parent / "fixtures" / "mobile"


def load_mobile_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def by_id(result: MobileResult, check_id: str):
    return next(check for check in result.checks if check.check_id == check_id)


__all__ = ["FIXTURES", "analyze_snapshot", "by_id", "load_mobile_fixture", "snapshot_from_parts"]
