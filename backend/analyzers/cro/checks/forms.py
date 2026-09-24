from backend.analyzers.cro.checks._util import cro_check
from backend.analyzers.cro.config import FORM_FIELD_HIGH_THRESHOLD, FORM_FIELD_WARNING_THRESHOLD, FORM_PAGE_TYPES
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.extraction import VAGUE_CTA
from backend.analyzers.cro.models import CheckResult


def run(ctx: PageCroContext) -> list[CheckResult]:
    forms = ctx.forms
    expected = ctx.page_type in FORM_PAGE_TYPES
    if not forms:
        return [
            cro_check(
                ctx,
                check_id="cro.form.missing",
                name="Form presence",
                group="forms",
                status="warning" if expected else "not_applicable",
                severity="medium" if expected else "low",
                message="No form was detected on this page." if expected else "A form is not required on this page type.",
            ),
            cro_check(
                ctx,
                check_id="cro.form.large",
                name="Form length",
                group="forms",
                status="not_applicable",
                severity="medium",
                message="Form length was not evaluated because no form was detected.",
            ),
            cro_check(
                ctx,
                check_id="cro.form.unclear_purpose",
                name="Form purpose",
                group="forms",
                status="not_applicable",
                severity="low",
                message="Form purpose was not evaluated because no form was detected.",
            ),
            cro_check(
                ctx,
                check_id="cro.form.submit_unclear",
                name="Form submit wording",
                group="forms",
                status="not_applicable",
                severity="low",
                message="Submit wording was not evaluated because no form was detected.",
            ),
        ]
    largest = max(forms, key=lambda item: int(item.get("fields") or 0))
    field_count = int(largest.get("fields") or 0)
    checks = [
        cro_check(
            ctx,
            check_id="cro.form.missing",
            name="Form presence",
            group="forms",
            status="pass",
            severity="low",
            message=f"{len(forms)} form{'s' if len(forms) != 1 else ''} detected.",
            selector=largest.get("selector"),
        )
    ]
    if field_count >= FORM_FIELD_HIGH_THRESHOLD:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.form.large",
                name="Form length",
                group="forms",
                status="warning",
                severity="medium",
                message=f"Form contains {field_count} input controls, which may represent higher interaction effort.",
                detected=f"{field_count} fields",
                selector=largest.get("selector"),
                evidence={"fields": field_count, "threshold": FORM_FIELD_HIGH_THRESHOLD},
            )
        )
    elif field_count >= FORM_FIELD_WARNING_THRESHOLD:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.form.large",
                name="Form length",
                group="forms",
                status="warning",
                severity="low",
                message=f"Form contains {field_count} fields. Longer forms may require more user interaction.",
                detected=f"{field_count} fields",
                selector=largest.get("selector"),
                evidence={"fields": field_count, "threshold": FORM_FIELD_WARNING_THRESHOLD},
            )
        )
    else:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.form.large",
                name="Form length",
                group="forms",
                status="pass",
                severity="low",
                message=f"Form contains {field_count} input control{'s' if field_count != 1 else ''}.",
                detected=f"{field_count} fields",
            )
        )
    unknown = [item for item in forms if item.get("purpose") in {None, "unknown"}]
    if unknown and expected:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.form.unclear_purpose",
                name="Form purpose",
                group="forms",
                status="warning",
                severity="low",
                message="Form purpose could not be inferred from nearby heading or copy.",
                selector=unknown[0].get("selector"),
            )
        )
    else:
        purpose = largest.get("purpose") or "unknown"
        checks.append(
            cro_check(
                ctx,
                check_id="cro.form.unclear_purpose",
                name="Form purpose",
                group="forms",
                status="pass" if purpose != "unknown" else "not_applicable",
                severity="low",
                message=f"Form purpose inferred as {purpose}." if purpose != "unknown" else "Form purpose was not inferred.",
            )
        )
    unclear_submit = []
    for form in forms:
        submit = str(form.get("submit_text") or "").strip()
        if not submit:
            unclear_submit.append(form)
            continue
        if VAGUE_CTA.match(submit) and form.get("purpose") in {None, "unknown"}:
            unclear_submit.append(form)
    if unclear_submit:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.form.submit_unclear",
                name="Form submit wording",
                group="forms",
                status="warning",
                severity="low",
                message="Form submit control uses generic or missing wording without surrounding form context.",
                detected=str(unclear_submit[0].get("submit_text") or "missing"),
                selector=unclear_submit[0].get("selector"),
            )
        )
    else:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.form.submit_unclear",
                name="Form submit wording",
                group="forms",
                status="pass",
                severity="low",
                message="Form submit wording is present and usable in context.",
            )
        )
    return checks
