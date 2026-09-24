from __future__ import annotations

from backend.analyzers.aeo.checks._util import page_url
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, make_check


def run(ctx: AeoContext) -> list[CheckResult]:
    page = page_url(ctx)
    html = ctx.html
    return [
        _hierarchy(html.get("heading_outline") or [], page),
        _sections(html, page),
        _lists(html.get("lists") or [], page),
        _tables(int(html.get("table_count") or 0), page),
    ]


def _hierarchy(outline: list[int], page: str) -> CheckResult:
    why = "A readable heading outline (without large jumps such as H1 to H4) helps machines follow the page structure. This reuses the shared heading parse."
    if not outline:
        return make_check(
            check_id="AEO-STRUCT-001",
            name="Clear heading hierarchy",
            group="content_structure",
            status="fail",
            severity="medium",
            message="No headings were found, so the page has no heading hierarchy.",
            recommendation="Add an H1 and supporting H2 headings that match the visible sections.",
            why=why,
            page_url=page,
        )
    jumps = []
    previous = None
    for level in outline:
        if previous is not None and level - previous >= 2:
            jumps.append(f"H{previous} → H{level}")
        previous = level
    if jumps:
        return make_check(
            check_id="AEO-STRUCT-001",
            name="Clear heading hierarchy",
            group="content_structure",
            status="warning",
            severity="low",
            message="The heading outline skips intermediate levels.",
            recommendation="Review whether heading levels match the visible structure of the page.",
            why=why,
            detected="; ".join(jumps),
            page_url=page,
        )
    return make_check(
        check_id="AEO-STRUCT-001",
        name="Clear heading hierarchy",
        group="content_structure",
        status="pass",
        severity="low",
        message="The heading outline does not contain large level jumps.",
        why=why,
        detected=", ".join(f"H{level}" for level in outline[:12]),
        page_url=page,
    )


def _sections(html: dict, page: str) -> CheckResult:
    why = "Pages divided into headings, paragraphs, and lists are easier to segment than a single undifferentiated block."
    h2 = int(html.get("h2_count") or 0)
    h3 = int(html.get("h3_count") or 0)
    paragraphs = len(html.get("paragraphs") or [])
    lists = len(html.get("lists") or [])
    scorecard = f"H2={h2}, H3={h3}, paragraphs={paragraphs}, lists={lists}"
    if h2 >= 2 and paragraphs >= 2:
        return make_check(
            check_id="AEO-STRUCT-002",
            name="Content sections",
            group="content_structure",
            status="pass",
            severity="medium",
            message="The page is divided into multiple heading-led sections with paragraph content.",
            why=why,
            detected=scorecard,
            page_url=page,
        )
    if h2 >= 1 or paragraphs >= 2 or lists:
        return make_check(
            check_id="AEO-STRUCT-002",
            name="Content sections",
            group="content_structure",
            status="warning",
            severity="medium",
            message="Some section structure is present, but the page has limited heading/paragraph division.",
            recommendation="Group related content under H2 headings with supporting paragraphs or lists.",
            why=why,
            detected=scorecard,
            page_url=page,
        )
    return make_check(
        check_id="AEO-STRUCT-002",
        name="Content sections",
        group="content_structure",
        status="fail",
        severity="medium",
        message="The page does not appear to be divided into meaningful sections.",
        recommendation="Introduce H2 sections, paragraphs, and lists that match the topics on the page.",
        why=why,
        detected=scorecard,
        page_url=page,
    )


def _lists(lists: list[dict], page: str) -> CheckResult:
    why = "Lists can expose features, steps, or requirements as discrete items. This is an informational structure signal, not a ranking factor."
    meaningful = [item for item in lists if int(item.get("count") or 0) >= 3]
    if meaningful:
        sample = meaningful[0]
        return make_check(
            check_id="AEO-STRUCT-003",
            name="Lists for structured information",
            group="content_structure",
            status="pass",
            severity="info",
            message="The page contains lists that can expose discrete facts or steps.",
            why=why,
            detected=f"{len(meaningful)} list(s) with 3+ items; first has {sample.get('count')} items.",
            page_url=page,
        )
    if lists:
        return make_check(
            check_id="AEO-STRUCT-003",
            name="Lists for structured information",
            group="content_structure",
            status="warning",
            severity="info",
            message="Lists were found, but they are very short.",
            why=why,
            detected=f"{len(lists)} short list(s).",
            page_url=page,
        )
    return make_check(
        check_id="AEO-STRUCT-003",
        name="Lists for structured information",
        group="content_structure",
        status="warning",
        severity="info",
        message="No content lists were detected outside navigation chrome.",
        recommendation="Use a list when describing steps, features, or requirements.",
        why=why,
        page_url=page,
    )


def _tables(count: int, page: str) -> CheckResult:
    why = "Tables can expose comparable facts. Their presence is reported as structure, not as an AI-visibility boost."
    if count:
        return make_check(
            check_id="AEO-STRUCT-004",
            name="Tables",
            group="content_structure",
            status="pass",
            severity="info",
            message="Structured tabular information is present.",
            why=why,
            detected=f"{count} table(s).",
            page_url=page,
        )
    return make_check(
        check_id="AEO-STRUCT-004",
        name="Tables",
        group="content_structure",
        status="pass",
        severity="info",
        message="No tables were found. Tables are not required on every page.",
        why=why,
        detected="0 tables.",
        page_url=page,
    )
