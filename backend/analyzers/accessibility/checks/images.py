from __future__ import annotations

from backend.analyzers.accessibility.checks._util import a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult

MEANINGLESS = {"image", "img", "photo", "picture", "graphic", "icon"}


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    images = [item for item in (snapshot.images or []) if item.get("visible") is not False]
    inputs = snapshot.image_inputs or []
    checks: list[CheckResult] = []
    if not images and not inputs:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-001", name="Images have alternative text", group="images", status="not_applicable", severity="high", message="No images were present to evaluate."))
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-002", name="Decorative images may use empty alt", group="images", status="not_applicable", severity="low", message="Decorative image handling was not evaluated because no images were present."))
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-003", name="Image inputs have accessible names", group="images", status="not_applicable", severity="medium", message="No image buttons were present."))
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-004", name="Linked images have accessible names", group="images", status="not_applicable", severity="medium", message="No linked images were present."))
        return checks

    missing = [item for item in images if not item.get("has_alt")]
    decorative = [item for item in images if item.get("has_alt") and (item.get("alt") == "")]
    meaningless = [item for item in images if str(item.get("alt") or "").strip().lower() in MEANINGLESS]
    if missing:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-001", name="Images have alternative text", group="images", status="fail", severity="high", message=f"{len(missing)} image(s) do not have an alt attribute.", recommendation="Provide meaningful alt text for informative images and use empty alt text for decorative images.", selector=missing[0].get("selector"), affected_element_count=len(missing), wcag_reference="WCAG 1.1.1"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-001", name="Images have alternative text", group="images", status="pass", severity="high", message="Visible images expose an alt attribute.", wcag_reference="WCAG 1.1.1"))

    if decorative and not missing:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-002", name="Decorative images may use empty alt", group="images", status="pass", severity="low", message="Empty alt text is present on some images, which is appropriate for decorative images.", affected_element_count=len(decorative)))
    elif meaningless:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-002", name="Decorative images may use empty alt", group="images", status="warning", severity="low", message="Some alt text looks non-descriptive. Manual review of alt quality is recommended.", source="manual-review", manual_review=True, affected_element_count=len(meaningless)))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-002", name="Decorative images may use empty alt", group="images", status="pass", severity="low", message="No decorative-image conflicts were detected. Alt quality still requires manual review for meaning."))

    unnamed_inputs = [item for item in inputs if not item.get("named")]
    if not inputs:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-003", name="Image inputs have accessible names", group="images", status="not_applicable", severity="medium", message="No image buttons were present."))
    elif unnamed_inputs:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-003", name="Image inputs have accessible names", group="images", status="fail", severity="high", message="An image input is missing an accessible name.", selector=unnamed_inputs[0].get("selector"), affected_element_count=len(unnamed_inputs), wcag_reference="WCAG 1.1.1"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-003", name="Image inputs have accessible names", group="images", status="pass", severity="medium", message="Image inputs expose accessible names."))

    unnamed_linked = [item for item in images if item.get("in_link") and not item.get("has_alt")]
    if not any(item.get("in_link") for item in images):
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-004", name="Linked images have accessible names", group="images", status="not_applicable", severity="medium", message="No images inside links or buttons were detected."))
    elif unnamed_linked:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-004", name="Linked images have accessible names", group="images", status="fail", severity="high", message="An image used as a link or control is missing alternative text.", selector=unnamed_linked[0].get("selector"), affected_element_count=len(unnamed_linked), wcag_reference="WCAG 1.1.1"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-IMG-004", name="Linked images have accessible names", group="images", status="pass", severity="medium", message="Images inside links or buttons expose alternative text."))
    return checks
