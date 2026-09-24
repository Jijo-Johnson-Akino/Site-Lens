from __future__ import annotations

from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult, make_check
from backend.analyzers.uiux.sanitizer import sanitize_selector

LANG_RE = __import__("re").compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


def page_url(snapshot: AccessibleSnapshot) -> str:
    return str(snapshot.page.get("final_url") or snapshot.page.get("url") or "")


def a11y_check(snapshot: AccessibleSnapshot, **kwargs) -> CheckResult:
    return make_check(page_url=page_url(snapshot), selector=sanitize_selector(kwargs.pop("selector", None)), **kwargs)
