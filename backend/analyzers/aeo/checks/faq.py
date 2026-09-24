from __future__ import annotations

from backend.analyzers.aeo.checks._util import FAQ_TEXT, QUESTION_START, is_english, language_of, page_url, types_present
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, make_check


def run(ctx: AeoContext) -> list[CheckResult]:
    page = page_url(ctx)
    english = is_english(language_of(ctx))
    questions = _question_headings(ctx, english)
    return [
        _question_headings_check(questions, page, english),
        _faq_content(ctx, questions, page, english),
        _pairing(ctx, questions, page, english),
    ]


def _question_headings(ctx: AeoContext, english: bool) -> list[dict]:
    found = []
    for block in ctx.html.get("heading_blocks") or []:
        text = (block.get("text") or "").strip()
        if not text:
            continue
        if text.endswith("?"):
            found.append(block)
        elif english and QUESTION_START.search(text):
            found.append(block)
    return found


def _question_headings_check(questions: list[dict], page: str, english: bool) -> CheckResult:
    why = "Question-oriented headings make the relationship between a question and an answer explicit for automated readers. This does not predict AI search selection."
    if questions:
        return make_check(
            check_id="AEO-QUESTION-001",
            name="Question headings",
            group="question_coverage",
            status="pass",
            severity="medium",
            message="Question-style headings were found.",
            why=why,
            detected="; ".join(str(item.get("text")) for item in questions[:5]),
            language_dependent=True,
            page_url=page,
        )
    if not english:
        return make_check(
            check_id="AEO-QUESTION-001",
            name="Question headings",
            group="question_coverage",
            status="not_applicable",
            severity="medium",
            message="English question-word patterns were not applied because the page language is not English, and no “?” headings were found.",
            why=why,
            language_dependent=True,
            page_url=page,
        )
    return make_check(
        check_id="AEO-QUESTION-001",
        name="Question headings",
        group="question_coverage",
        status="warning",
        severity="medium",
        message="No question-style headings were found.",
        recommendation="Consider adding useful user questions and concise answers where they naturally fit the subject matter.",
        why=why,
        detected="No headings starting with What/Why/How/… or ending with “?”.",
        language_dependent=True,
        page_url=page,
    )


def _faq_content(ctx: AeoContext, questions: list[dict], page: str, english: bool) -> CheckResult:
    why = "FAQ sections and FAQPage schema expose explicit question/answer groups. FAQ schema is not required for every site."
    has_schema = "FAQPage" in types_present(ctx)
    headings = [block.get("text") or "" for block in (ctx.html.get("heading_blocks") or [])]
    has_faq_heading = any(FAQ_TEXT.search(text) for text in headings) if english else False
    if has_schema or has_faq_heading or (len(questions) >= 2 and english):
        detected = []
        if has_schema:
            detected.append("FAQPage schema")
        if has_faq_heading:
            detected.append("FAQ heading")
        if len(questions) >= 2:
            detected.append(f"{len(questions)} question headings")
        return make_check(
            check_id="AEO-QUESTION-002",
            name="FAQ content",
            group="question_coverage",
            status="pass",
            severity="low",
            message="FAQ or repeated question/answer structure was detected.",
            why=why,
            detected=", ".join(detected),
            language_dependent=not has_schema,
            page_url=page,
        )
    if not english and not has_schema:
        return make_check(
            check_id="AEO-QUESTION-002",
            name="FAQ content",
            group="question_coverage",
            status="not_applicable",
            severity="low",
            message="English FAQ heading patterns were not applied because the page language is not English, and no FAQPage schema was found.",
            why=why,
            language_dependent=True,
            page_url=page,
        )
    return make_check(
        check_id="AEO-QUESTION-002",
        name="FAQ content",
        group="question_coverage",
        status="warning",
        severity="low",
        message="No FAQ section or FAQPage schema was detected.",
        recommendation="If people ask recurring questions, group them in an FAQ with short answers. Schema is optional.",
        why=why,
        language_dependent=True,
        page_url=page,
    )


def _pairing(ctx: AeoContext, questions: list[dict], page: str, english: bool) -> CheckResult:
    why = "A question heading is most useful when a textual answer follows it, rather than only an image or button."
    if not questions:
        return make_check(
            check_id="AEO-QUESTION-003",
            name="Question-answer pairing",
            group="question_coverage",
            status="not_applicable",
            severity="medium",
            message="Question/answer pairing was not evaluated because no question headings were found.",
            why=why,
            language_dependent=True,
            page_url=page,
        )
    weak = []
    strong = []
    for block in questions:
        following = block.get("following_length") or 0
        media_or_controls = ((block.get("media_count") or 0) + (block.get("control_count") or 0)) > 0
        if following >= 40:
            strong.append(block.get("text"))
        elif media_or_controls or following < 20:
            weak.append(block.get("text"))
    if strong and not weak:
        return make_check(
            check_id="AEO-QUESTION-003",
            name="Question-answer pairing",
            group="question_coverage",
            status="pass",
            severity="medium",
            message="Question headings are followed by meaningful text.",
            why=why,
            detected="; ".join(str(item) for item in strong[:4]),
            language_dependent=True,
            page_url=page,
        )
    if weak:
        return make_check(
            check_id="AEO-QUESTION-003",
            name="Question-answer pairing",
            group="question_coverage",
            status="warning",
            severity="medium",
            message="At least one question heading is followed by little text, an image, or a button instead of an answer.",
            recommendation="Follow each question heading with a short written answer.",
            why=why,
            detected="; ".join(str(item) for item in weak[:4]),
            language_dependent=True,
            page_url=page,
        )
    return make_check(
        check_id="AEO-QUESTION-003",
        name="Question-answer pairing",
        group="question_coverage",
        status="warning",
        severity="medium",
        message="Question headings were found, but following answers are thin.",
        why=why,
        language_dependent=True,
        page_url=page,
    )
