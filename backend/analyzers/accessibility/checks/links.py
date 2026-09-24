from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult

GENERIC = {"click here", "here", "read more", "more", "link"}


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    links = [item for item in (snapshot.links or []) if item.get("visible") is not False]
    checks: list[CheckResult] = []
    if not links:
        checks.append(a11y_check(snapshot, check_id="A11Y-LINK-001", name="Links have accessible names", group="links", status="not_applicable", severity="high", message="No links were present to evaluate."))
        checks.append(a11y_check(snapshot, check_id="A11Y-LINK-002", name="Link text is not generic-only", group="links", status="not_applicable", severity="low", message="Generic link text was not evaluated because no links were present."))
        return checks
    unnamed = [item for item in links if not item.get("named")]
    if unnamed:
        checks.append(a11y_check(snapshot, check_id="A11Y-LINK-001", name="Links have accessible names", group="links", status="fail", severity="high", message=f"{len(unnamed)} link(s) have no accessible name.", recommendation="Provide visible text, aria-label, or an image with alt text inside the link.", selector=unnamed[0].get("selector"), affected_element_count=len(unnamed), wcag_reference="WCAG 2.4.4"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-LINK-001", name="Links have accessible names", group="links", status="pass", severity="high", message="Visible links expose accessible names.", wcag_reference="WCAG 2.4.4"))
    generic = [item for item in links if str(item.get("name") or "").strip().lower() in GENERIC]
    if generic:
        checks.append(a11y_check(snapshot, check_id="A11Y-LINK-002", name="Link text is not generic-only", group="links", status="warning", severity="low", message="Some link text is generic. Context determines whether this is an issue.", recommendation="Prefer link text that describes the destination. \"Click here\" is not automatically an accessibility failure.", source="manual-review", manual_review=True, affected_element_count=len(generic), wcag_reference="WCAG 2.4.4"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-LINK-002", name="Link text is not generic-only", group="links", status="pass", severity="low", message="No generic-only link text was detected. Purpose in context still benefits from manual review."))
    return checks
