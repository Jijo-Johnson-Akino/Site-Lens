from __future__ import annotations

from backend.analyzers.uiux.models import CheckResult, ViewportSnapshot, make_check
from backend.analyzers.uiux.sanitizer import sanitize_selector


def page_url(snapshot: ViewportSnapshot) -> str:
    return str(snapshot.page.get("final_url") or snapshot.page.get("url") or "")


def viewport_name(snapshot: ViewportSnapshot) -> str:
    return str(snapshot.viewport.get("name") or "desktop")


def viewport_width(snapshot: ViewportSnapshot) -> int:
    try:
        return int(snapshot.viewport.get("width") or 0)
    except (TypeError, ValueError):
        return 0


def ux_check(
    snapshot: ViewportSnapshot,
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
    affected_element: str | None = None,
) -> CheckResult:
    return make_check(
        check_id=check_id,
        name=name,
        group=group,
        status=status,
        severity=severity,
        message=message,
        page_url=page_url(snapshot),
        viewport=viewport_name(snapshot),
        recommendation=recommendation,
        why=why,
        detected=detected,
        affected_element=sanitize_selector(affected_element),
    )
