from __future__ import annotations

from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult, make_check
from backend.analyzers.uiux.sanitizer import sanitize_selector


def cro_check(
    ctx: PageCroContext,
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
    viewport: str | None = None,
    affected_element_count: int = 0,
    evidence: dict | None = None,
    details: dict | None = None,
) -> CheckResult:
    return make_check(
        check_id=check_id,
        name=name,
        group=group,
        status=status,
        severity=severity,
        message=message,
        page_url=ctx.url,
        page_id=ctx.page.id,
        recommendation=recommendation,
        why=why,
        detected=detected,
        selector=sanitize_selector(selector) if selector else None,
        viewport=viewport,
        affected_element_count=affected_element_count,
        evidence=evidence,
        details=details,
    )


def primary_ctas(ctx: PageCroContext) -> list[dict]:
    primaries = [item for item in ctx.ctas if item.get("primary_candidate") and not item.get("potential")]
    if primaries:
        primaries.sort(key=lambda item: int(item.get("confidence") or 0), reverse=True)
        return primaries
    return []


def actionable_status(checks: list[CheckResult], group: str) -> str | None:
    subset = [item for item in checks if item.group == group]
    if not subset:
        return None
    if any(item.status == "fail" for item in subset):
        return "fail"
    if any(item.status == "warning" for item in subset):
        return "warning"
    if any(item.status == "pass" for item in subset):
        return "pass"
    return "not_applicable"
