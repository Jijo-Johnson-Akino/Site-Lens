from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    iframes = snapshot.iframes or []
    dialogs = snapshot.dialogs or []
    live = snapshot.live or []
    meta = snapshot.viewport_meta or {}
    content = str(meta.get("content") or "").lower()
    checks: list[CheckResult] = []

    unnamed_frames = [item for item in iframes if not item.get("named") and not item.get("title")]
    if not iframes:
        checks.append(a11y_check(snapshot, check_id="A11Y-IFRAME-001", name="Iframes have accessible names", group="other", status="not_applicable", severity="medium", message="No iframes were present. Third-party iframe content is not audited."))
    elif unnamed_frames:
        checks.append(a11y_check(snapshot, check_id="A11Y-IFRAME-001", name="Iframes have accessible names", group="other", status="fail", severity="medium", message=f"{len(unnamed_frames)} iframe(s) are missing a title or accessible name.", recommendation="Add a title (or aria-label) that describes the embedded content.", selector=unnamed_frames[0].get("selector"), affected_element_count=len(unnamed_frames), wcag_reference="WCAG 4.1.2"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-IFRAME-001", name="Iframes have accessible names", group="other", status="pass", severity="medium", message="Iframes expose a title or accessible name. Embedded third-party content was not audited."))

    unnamed_dialogs = [item for item in dialogs if item.get("open") and not item.get("named")]
    if not dialogs:
        checks.append(a11y_check(snapshot, check_id="A11Y-DIALOG-001", name="Dialogs have accessible names", group="other", status="not_applicable", severity="medium", message="No dialogs were detected. Dialogs were not opened automatically."))
    elif unnamed_dialogs:
        checks.append(a11y_check(snapshot, check_id="A11Y-DIALOG-001", name="Dialogs have accessible names", group="other", status="fail", severity="high", message="A visible dialog does not expose an accessible name.", selector=unnamed_dialogs[0].get("selector"), affected_element_count=len(unnamed_dialogs), wcag_reference="WCAG 4.1.2"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-DIALOG-001", name="Dialogs have accessible names", group="other", status="pass", severity="medium", message="Detected dialogs expose accessible names. Focus management was not fully exercised."))

    if "user-scalable=no" in content or "user-scalable=0" in content or "maximum-scale=1" in content.replace(" ", ""):
        checks.append(a11y_check(snapshot, check_id="A11Y-VIEW-001", name="Viewport allows user scaling", group="other", status="warning", severity="medium", message="The viewport meta appears to restrict user scaling.", recommendation="Avoid disabling zoom. Mobile accessibility and zoom behavior may still need manual validation.", detected=str(meta.get("content") or ""), wcag_reference="WCAG 1.4.4"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-VIEW-001", name="Viewport allows user scaling", group="other", status="pass", severity="low", message="No viewport rule disabling user scaling was detected. Zoom behavior still benefits from manual checks."))

    if live:
        checks.append(a11y_check(snapshot, check_id="A11Y-LIVE-001", name="Live regions", group="other", status="pass", severity="info", message=f"{len(live)} live region(s) were detected. Dynamic updates were not exercised.", affected_element_count=len(live)))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-LIVE-001", name="Live regions", group="other", status="not_applicable", severity="info", message="No aria-live or status regions were detected."))

    return checks
