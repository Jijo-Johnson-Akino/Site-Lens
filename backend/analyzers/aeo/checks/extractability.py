from __future__ import annotations

from backend.analyzers.aeo.checks._util import page_url
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, make_check

LOW_RATIO = 0.03
THIN_CHARS = 80
OK_CHARS = 400
FRAGMENT_AVG = 10


def run(ctx: AeoContext) -> list[CheckResult]:
    page = page_url(ctx)
    html = ctx.html
    return [_ratio(html, page), _main_text(html, page), _fragmentation(html, page), _hidden(html, page)]


def _ratio(html: dict, page: str) -> CheckResult:
    why = "Text-to-HTML ratio is a coarse extractability signal. It is not an absolute quality or ranking judgment."
    ratio = float(html.get("text_ratio") or 0.0)
    text_len = int(html.get("visible_text_length") or 0)
    html_len = int(html.get("html_length") or 0)
    detected = f"{text_len} text characters / {html_len} HTML characters ({ratio:.1%})."
    if html_len == 0:
        return make_check(
            check_id="AEO-EXTRACT-001",
            name="Text-to-code ratio",
            group="extractability",
            status="not_applicable",
            severity="low",
            message="Text-to-HTML ratio was not evaluated because no HTML was stored.",
            why=why,
            page_url=page,
        )
    if ratio < LOW_RATIO and text_len < OK_CHARS:
        return make_check(
            check_id="AEO-EXTRACT-001",
            name="Text-to-code ratio",
            group="extractability",
            status="warning",
            severity="low",
            message="The initial HTML contains relatively little visible text compared with markup.",
            recommendation="Ensure primary explanations exist as HTML text, not only in images or client-rendered widgets.",
            why=why,
            detected=detected,
            page_url=page,
        )
    return make_check(
        check_id="AEO-EXTRACT-001",
        name="Text-to-code ratio",
        group="extractability",
        status="pass",
        severity="low",
        message="Visible text is present in the initial HTML in a reasonable proportion to markup.",
        why=why,
        detected=detected,
        page_url=page,
    )


def _main_text(html: dict, page: str) -> CheckResult:
    why = "If the main explanation is missing from the first HTML response, machine readers that do not run scripts will not see it."
    text_len = int(html.get("visible_text_length") or 0)
    words = len((html.get("visible_text") or "").split())
    detected = f"{text_len} characters, about {words} word(s)."
    if text_len >= OK_CHARS or words >= 60:
        return make_check(
            check_id="AEO-EXTRACT-002",
            name="Main content availability",
            group="extractability",
            status="pass",
            severity="high",
            message="Meaningful text is available in the initial HTML.",
            why=why,
            detected=detected,
            page_url=page,
        )
    if text_len >= THIN_CHARS or words >= 25:
        return make_check(
            check_id="AEO-EXTRACT-002",
            name="Main content availability",
            group="extractability",
            status="warning",
            severity="medium",
            message="Some text is available in the initial HTML, but the main copy is thin.",
            recommendation="Include the core explanation as HTML text in the first response.",
            why=why,
            detected=detected,
            page_url=page,
        )
    return make_check(
        check_id="AEO-EXTRACT-002",
        name="Main content availability",
        group="extractability",
        status="fail",
        severity="high",
        message="Very little meaningful text is available in the initial HTML.",
        recommendation="Render primary copy in the HTML response rather than only after client-side scripting.",
        why=why,
        detected=detected,
        page_url=page,
    )


def _fragmentation(html: dict, page: str) -> CheckResult:
    why = "Copy split across many tiny spans and wrappers is harder to extract cleanly. This is a warning signal only."
    nodes = int(html.get("text_node_count") or 0)
    text_len = max(int(html.get("visible_text_length") or 0), 1)
    spans = int(html.get("span_count") or 0)
    avg = (text_len / nodes) if nodes else text_len
    detected = f"{nodes} text nodes, {spans} span(s), ~{avg:.1f} characters per text node."
    if nodes >= 40 and avg < FRAGMENT_AVG and spans >= 25:
        return make_check(
            check_id="AEO-EXTRACT-003",
            name="Excessive text fragmentation",
            group="extractability",
            status="warning",
            severity="low",
            message="Visible copy appears highly fragmented across nested elements and spans.",
            recommendation="Prefer ordinary paragraphs over many single-word wrappers when it does not hurt design.",
            why=why,
            detected=detected,
            page_url=page,
        )
    return make_check(
        check_id="AEO-EXTRACT-003",
        name="Excessive text fragmentation",
        group="extractability",
        status="pass",
        severity="low",
        message="Text does not appear excessively fragmented in the initial HTML.",
        why=why,
        detected=detected,
        page_url=page,
    )


def _hidden(html: dict, page: str) -> CheckResult:
    why = "display:none and visibility:hidden text is sometimes legitimate (menus, templates). Large hidden blocks are worth a review, not an automatic penalty."
    hidden = int(html.get("hidden_text_length") or 0)
    visible = max(int(html.get("visible_text_length") or 0), 1)
    if hidden == 0:
        return make_check(
            check_id="AEO-EXTRACT-004",
            name="Hidden content",
            group="extractability",
            status="pass",
            severity="info",
            message="No obvious display:none or visibility:hidden text was detected.",
            why=why,
            page_url=page,
        )
    ratio = hidden / visible
    if ratio >= 0.5 and hidden >= 200:
        return make_check(
            check_id="AEO-EXTRACT-004",
            name="Hidden content",
            group="extractability",
            status="warning",
            severity="low",
            message="A substantial amount of text is marked hidden in the HTML.",
            recommendation="Review hidden copy. Menus and disclosure widgets are normal; stuffing hidden essays is not.",
            why=why,
            detected=f"{hidden} hidden characters vs {visible} visible ({ratio:.0%}).",
            page_url=page,
        )
    return make_check(
        check_id="AEO-EXTRACT-004",
        name="Hidden content",
        group="extractability",
        status="pass",
        severity="info",
        message="Some hidden text was found, which can be legitimate for navigation or progressive disclosure.",
        why=why,
        detected=f"{hidden} hidden characters.",
        page_url=page,
    )
