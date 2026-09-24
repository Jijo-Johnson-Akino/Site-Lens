from __future__ import annotations

from backend.analyzers.accessibility.checks._util import LANG_RE, a11y_check
from backend.analyzers.accessibility.models import AccessibleSnapshot, CheckResult


def run(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    doc = snapshot.document or {}
    lang = str(doc.get("lang") or "").strip()
    title = str(doc.get("title") or "").strip()
    direction = str(doc.get("dir") or "").strip().lower()
    checks: list[CheckResult] = []

    lang_present = bool(doc.get("lang_present")) or bool(lang)
    if not lang and lang_present:
        checks.append(a11y_check(snapshot, check_id="A11Y-DOC-001", name="HTML lang attribute exists", group="document", status="warning", severity="medium", message="The html lang attribute is present but empty.", recommendation="Set lang to a valid BCP 47 tag for the page language. English is not required.", why="Assistive technologies use the language to select pronunciation and translations.", wcag_reference="WCAG 3.1.1", selector="html"))
    elif not lang:
        checks.append(a11y_check(snapshot, check_id="A11Y-DOC-001", name="HTML lang attribute exists", group="document", status="fail", severity="high", message="The html element does not declare a language.", recommendation="Add a lang attribute on the html element, such as lang=\"en\" or the page's actual language. English is not required.", why="Assistive technologies use the language to select pronunciation and translations.", wcag_reference="WCAG 3.1.1", selector="html"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-DOC-001", name="HTML lang attribute exists", group="document", status="pass", severity="high", message=f"The page declares lang=\"{lang}\".", detected=lang, selector="html", wcag_reference="WCAG 3.1.1"))

    if not lang:
        checks.append(a11y_check(snapshot, check_id="A11Y-DOC-003", name="Document language is valid", group="document", status="not_applicable", severity="medium", message="Language validity was not evaluated because no lang attribute was present."))
    elif not LANG_RE.match(lang):
        checks.append(a11y_check(snapshot, check_id="A11Y-DOC-003", name="Document language is valid", group="document", status="warning", severity="medium", message="The lang attribute is present but does not look like a valid language tag.", recommendation="Use a BCP 47 language tag such as en, en-US, or fr.", detected=lang, selector="html"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-DOC-003", name="Document language is valid", group="document", status="pass", severity="medium", message="The declared language tag is well-formed. Content language match was not verified automatically.", detected=lang, selector="html"))

    if not title:
        checks.append(a11y_check(snapshot, check_id="A11Y-DOC-002", name="Document title exists", group="document", status="fail", severity="high", message="The document title is missing or empty.", recommendation="Provide a descriptive title element.", wcag_reference="WCAG 2.4.2", selector="title"))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-DOC-002", name="Document title exists", group="document", status="pass", severity="high", message="The document has a title.", detected=title, selector="title", wcag_reference="WCAG 2.4.2"))

    if direction in {"rtl", "ltr"}:
        checks.append(a11y_check(snapshot, check_id="A11Y-DOC-004", name="Page text direction", group="document", status="pass", severity="info", message=f"The page declares dir=\"{direction}\".", detected=direction))
    else:
        checks.append(a11y_check(snapshot, check_id="A11Y-DOC-004", name="Page text direction", group="document", status="pass", severity="info", message="No dir attribute was found. Browsers default to left-to-right. This is not a failure."))
    return checks
