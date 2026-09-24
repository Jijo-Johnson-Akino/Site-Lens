from __future__ import annotations

from typing import Any

from backend.analyzers.mobile.models import CheckResult, MobileSnapshot, make_check
from backend.analyzers.uiux.sanitizer import sanitize_selector


def page_url(snapshot: MobileSnapshot) -> str:
    return str(snapshot.page.get("final_url") or snapshot.page.get("url") or "")


def viewport_label(snapshot: MobileSnapshot) -> str:
    width = snapshot.viewport.get("width") or 390
    height = snapshot.viewport.get("height") or 844
    return f"{int(width)}x{int(height)}"


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def finding(
    snapshot: MobileSnapshot,
    *,
    check_id: str,
    name: str,
    group,
    status,
    severity,
    message: str,
    recommendation: str | None = None,
    why: str | None = None,
    detected: str | None = None,
    selector: str | None = None,
    affected_element_count: int = 0,
    measured_value: str | float | int | None = None,
    expected_value: str | float | int | None = None,
    details: dict[str, Any] | None = None,
) -> CheckResult:
    return make_check(
        check_id=check_id,
        name=name,
        group=group,
        status=status,
        severity=severity,
        message=message,
        page_url=page_url(snapshot),
        viewport=viewport_label(snapshot),
        recommendation=recommendation,
        why=why,
        detected=detected,
        selector=sanitize_selector(selector),
        affected_element=sanitize_selector(selector),
        affected_element_count=affected_element_count,
        measured_value=measured_value,
        expected_value=expected_value,
        details=details,
    )
