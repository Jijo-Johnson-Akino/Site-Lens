from backend.analyzers.cro.checks._util import cro_check
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.models import CheckResult


def run(ctx: PageCroContext) -> list[CheckResult]:
    contact = ctx.signals.get("contact") or {}
    local = bool(contact.get("emails") or contact.get("phones") or contact.get("links") or contact.get("form"))
    if local or ctx.site_has_contact:
        return [
            cro_check(
                ctx,
                check_id="cro.contact.method.missing",
                name="Contact method",
                group="contact",
                status="pass",
                severity="medium",
                message=(
                    "A contact method was detected on this page."
                    if local
                    else "A contact method was detected elsewhere in the crawled site."
                ),
                detected="email" if contact.get("emails") else ("form" if contact.get("form") else "link"),
            )
        ]
    if ctx.page_type in {"article", "blog", "login"}:
        return [
            cro_check(
                ctx,
                check_id="cro.contact.method.missing",
                name="Contact method",
                group="contact",
                status="not_applicable",
                severity="low",
                message="A contact method is not required on this page type.",
            )
        ]
    return [
        cro_check(
            ctx,
            check_id="cro.contact.method.missing",
            name="Contact method",
            group="contact",
            status="warning",
            severity="medium",
            message="No obvious contact method was detected on this page.",
        )
    ]
