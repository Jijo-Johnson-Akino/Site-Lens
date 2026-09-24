from __future__ import annotations

from backend.analyzers.aeo.checks._util import DEFINITION_RE, QUESTION_START, is_english, language_of, page_url, primary_name
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, make_check

CONCISE_MIN = 40
CONCISE_MAX = 320


def run(ctx: AeoContext) -> list[CheckResult]:
    page = page_url(ctx)
    english = is_english(language_of(ctx))
    return [
        _direct_answers(ctx, page, english),
        _definitions(ctx, page, english),
        _near_headings(ctx, page),
        _concise_blocks(ctx, page),
    ]


def _question_blocks(ctx: AeoContext) -> list[dict]:
    blocks = []
    for block in ctx.html.get("heading_blocks") or []:
        text = (block.get("text") or "").strip()
        if text.endswith("?") or QUESTION_START.search(text):
            blocks.append(block)
    return blocks


def _direct_answers(ctx: AeoContext, page: str, english: bool) -> CheckResult:
    why = "A short paragraph immediately after a question-style heading is an extractable question/answer pair. This is a heuristic, not evidence of AI citation."
    if not english and not any((block.get("text") or "").endswith("?") for block in ctx.html.get("heading_blocks") or []):
        return make_check(
            check_id="AEO-ANSWER-001",
            name="Direct answer presence",
            group="answer_readiness",
            status="not_applicable",
            severity="medium",
            message="Direct-answer detection relies on question-style headings. The page language is not English, so this check was not scored as a failure.",
            why=why,
            language_dependent=True,
            page_url=page,
        )
    paired = []
    for block in _question_blocks(ctx):
        following = (block.get("following_text") or "").strip()
        if CONCISE_MIN <= len(following) <= 600:
            paired.append(block.get("text"))
    if paired:
        return make_check(
            check_id="AEO-ANSWER-001",
            name="Direct answer presence",
            group="answer_readiness",
            status="pass",
            severity="medium",
            message="Question-style headings are followed by concise answer-like text.",
            why=why,
            detected="; ".join(str(item) for item in paired[:3]),
            language_dependent=True,
            page_url=page,
        )
    if _question_blocks(ctx):
        return make_check(
            check_id="AEO-ANSWER-001",
            name="Direct answer presence",
            group="answer_readiness",
            status="warning",
            severity="medium",
            message="Question-style headings were found, but they are not followed by concise answer text.",
            recommendation="Place a short, direct answer immediately after each question heading.",
            why=why,
            language_dependent=True,
            page_url=page,
        )
    return make_check(
        check_id="AEO-ANSWER-001",
        name="Direct answer presence",
        group="answer_readiness",
        status="fail",
        severity="medium",
        message="No meaningful answer-style content was detected near question headings.",
        recommendation="Where it fits the subject, add a question heading followed by a short factual answer.",
        why=why,
        detected="No question heading with a concise following paragraph was found.",
        language_dependent=True,
        page_url=page,
    )


def _definitions(ctx: AeoContext, page: str, english: bool) -> CheckResult:
    why = "Phrases such as “X is…” or “X provides…” can make definitions easier to extract. This is a positive signal, not a guarantee of AI visibility."
    if not english:
        return make_check(
            check_id="AEO-ANSWER-002",
            name="Definition patterns",
            group="answer_readiness",
            status="not_applicable",
            severity="low",
            message="English definition patterns were not applied because the page language is not English.",
            why=why,
            language_dependent=True,
            page_url=page,
        )
    corpus = " ".join(
        [
            *(ctx.html.get("paragraphs") or [])[:12],
            *((block.get("following_text") or "") for block in (ctx.html.get("heading_blocks") or [])[:12]),
        ]
    )
    name = primary_name(ctx) or ""
    matches = DEFINITION_RE.findall(corpus[:4000])
    if name and re_search_name_definition(name, corpus):
        return make_check(
            check_id="AEO-ANSWER-002",
            name="Definition patterns",
            group="answer_readiness",
            status="pass",
            severity="low",
            message="The page contains definition-style statements about the primary name.",
            why=why,
            detected=f"{name} + definition verb",
            language_dependent=True,
            page_url=page,
        )
    if matches:
        sample = matches[0][0].strip()[:80]
        return make_check(
            check_id="AEO-ANSWER-002",
            name="Definition patterns",
            group="answer_readiness",
            status="pass",
            severity="low",
            message="Definition-style phrasing was detected in the page copy.",
            why=why,
            detected=sample,
            language_dependent=True,
            page_url=page,
        )
    return make_check(
        check_id="AEO-ANSWER-002",
        name="Definition patterns",
        group="answer_readiness",
        status="warning",
        severity="low",
        message="No obvious definition patterns such as “X is…” or “X provides…” were found.",
        recommendation="If the page introduces a product or concept, include one short definition sentence.",
        why=why,
        language_dependent=True,
        page_url=page,
    )


def re_search_name_definition(name: str, corpus: str) -> bool:
    import re

    escaped = re.escape(name.split("|")[0].strip())
    if len(escaped) < 3:
        return False
    pattern = re.compile(rf"\b{escaped}\b.{{0,40}}\b(is|are|refers to|means|helps|provides)\b", re.I)
    return bool(pattern.search(corpus))


def _near_headings(ctx: AeoContext, page: str) -> CheckResult:
    why = "Major headings are more useful to extractors when they are followed by meaningful text rather than empty space, images, or buttons only."
    majors = [block for block in (ctx.html.get("heading_blocks") or []) if block.get("level") in {1, 2} and block.get("text")]
    if not majors:
        return make_check(
            check_id="AEO-ANSWER-003",
            name="Important information near headings",
            group="answer_readiness",
            status="not_applicable",
            severity="medium",
            message="Heading-adjacent content was not evaluated because no H1 or H2 headings were found.",
            why=why,
            page_url=page,
        )
    weak = []
    for block in majors:
        following = block.get("following_length") or 0
        media_only = following < 20 and ((block.get("media_count") or 0) + (block.get("control_count") or 0)) > 0
        empty = following < 20
        very_long = following > 2500
        if media_only or empty or very_long:
            weak.append(block.get("text"))
    if len(weak) == len(majors):
        return make_check(
            check_id="AEO-ANSWER-003",
            name="Important information near headings",
            group="answer_readiness",
            status="fail",
            severity="medium",
            message="Major headings are not followed by meaningful text.",
            recommendation="Follow H1 and H2 headings with a short paragraph that states the point of the section.",
            why=why,
            detected="; ".join(str(item) for item in weak[:5]),
            page_url=page,
        )
    if weak:
        return make_check(
            check_id="AEO-ANSWER-003",
            name="Important information near headings",
            group="answer_readiness",
            status="warning",
            severity="medium",
            message="Some major headings are followed by little text, media only, or a very long unrelated block.",
            recommendation="Keep a concise explanatory paragraph next to each important heading.",
            why=why,
            detected="; ".join(str(item) for item in weak[:5]),
            page_url=page,
        )
    return make_check(
        check_id="AEO-ANSWER-003",
        name="Important information near headings",
        group="answer_readiness",
        status="pass",
        severity="medium",
        message="Major headings are followed by meaningful text.",
        why=why,
        detected=f"{len(majors)} H1/H2 heading(s) with following copy.",
        page_url=page,
    )


def _concise_blocks(ctx: AeoContext, page: str) -> CheckResult:
    why = "Short paragraphs that define a concept are easier to quote than long undifferentiated copy. There is no universally required word count."
    paragraphs = ctx.html.get("paragraphs") or []
    concise = [text for text in paragraphs if CONCISE_MIN <= len(text) <= CONCISE_MAX]
    if concise:
        return make_check(
            check_id="AEO-ANSWER-004",
            name="Concise answer blocks",
            group="answer_readiness",
            status="pass",
            severity="low",
            message="The page includes short paragraphs that can serve as extractable answer blocks.",
            why=why,
            detected=f"{len(concise)} paragraph(s) between {CONCISE_MIN} and {CONCISE_MAX} characters.",
            page_url=page,
        )
    if paragraphs:
        return make_check(
            check_id="AEO-ANSWER-004",
            name="Concise answer blocks",
            group="answer_readiness",
            status="warning",
            severity="low",
            message="Paragraphs were found, but none fall in a concise answer-length range.",
            recommendation="Consider one or two short paragraphs that state the main point directly.",
            why=why,
            detected=f"{len(paragraphs)} paragraph(s); none between {CONCISE_MIN} and {CONCISE_MAX} characters.",
            page_url=page,
        )
    return make_check(
        check_id="AEO-ANSWER-004",
        name="Concise answer blocks",
        group="answer_readiness",
        status="fail",
        severity="low",
        message="No paragraph-level answer blocks were found.",
        recommendation="Add short paragraphs that state what the page is about.",
        why=why,
        page_url=page,
    )
