from backend.analyzers.cro.checks._util import cro_check
from backend.analyzers.cro.config import CTA_TEXT_MIN_LENGTH
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.extraction import VAGUE_CTA
from backend.analyzers.cro.models import CheckResult


def run(ctx: PageCroContext) -> list[CheckResult]:
    labeled = [item for item in ctx.ctas if item.get("text")]
    if not labeled:
        return [
            cro_check(
                ctx,
                check_id="cro.cta.text.vague",
                name="CTA wording",
                group="cta_clarity",
                status="not_applicable",
                severity="medium",
                message="CTA wording was not evaluated because no CTA text was detected.",
            ),
            cro_check(
                ctx,
                check_id="cro.cta.inconsistent_label",
                name="CTA consistency",
                group="cta_clarity",
                status="not_applicable",
                severity="low",
                message="CTA label consistency was not evaluated.",
            ),
        ]
    vague = []
    for item in labeled:
        text = str(item.get("text") or "").strip()
        in_form = item.get("kind") == "submit" and ctx.forms
        if VAGUE_CTA.match(text) or (text and len(text) < CTA_TEXT_MIN_LENGTH):
            if in_form and text.lower() == "submit" and any(form.get("purpose") not in {None, "unknown"} for form in ctx.forms):
                continue
            vague.append(item)
    if vague:
        first = vague[0]
        checks = [
            cro_check(
                ctx,
                check_id="cro.cta.text.vague",
                name="CTA wording",
                group="cta_clarity",
                status="warning",
                severity="medium",
                message="CTA text is generic and may not describe the intended action.",
                recommendation="Use action wording that names the next step, such as a trial, demo, or quote request.",
                detected=str(first.get("text") or ""),
                selector=first.get("selector"),
                affected_element_count=len(vague),
            )
        ]
    else:
        checks = [
            cro_check(
                ctx,
                check_id="cro.cta.text.vague",
                name="CTA wording",
                group="cta_clarity",
                status="pass",
                severity="low",
                message="Detected CTA labels describe an action.",
            )
        ]
    strong_labels = [str(item.get("text") or "").strip() for item in labeled if item.get("strong") or item.get("primary_candidate")]
    unique = {label.lower() for label in strong_labels if label}
    if len(unique) >= 2:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.inconsistent_label",
                name="CTA consistency",
                group="cta_clarity",
                status="warning",
                severity="low",
                message="Multiple CTA labels were detected for similar conversion actions.",
                detected=", ".join(sorted({label for label in strong_labels}))[:180],
            )
        )
    else:
        checks.append(
            cro_check(
                ctx,
                check_id="cro.cta.inconsistent_label",
                name="CTA consistency",
                group="cta_clarity",
                status="pass" if unique else "not_applicable",
                severity="low",
                message="Conversion actions use consistent labels." if unique else "Not enough conversion labels were present to compare.",
            )
        )
    return checks
