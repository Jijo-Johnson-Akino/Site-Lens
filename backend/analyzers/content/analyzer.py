from __future__ import annotations

from backend.analyzers.content.checks import (
    run_authorship,
    run_completeness,
    run_cta,
    run_depth,
    run_duplication,
    run_freshness,
    run_headings,
    run_language,
    run_paragraphs,
    run_readability,
    run_relationships,
    run_structure,
)
from backend.analyzers.content.config import DEFAULT_SCORING, LIMITATIONS, ContentScoringConfig
from backend.analyzers.content.context import ContentContext
from backend.analyzers.content.extract import extract_page, word_count
from backend.analyzers.content.models import (
    CheckResult,
    ContentCategoryScore,
    ContentMetrics,
    ContentPageInfo,
    ContentResult,
    ContentSignals,
    DuplicatePair,
)
from backend.analyzers.content.page_type import classify_page
from backend.analyzers.content.readability import measure_readability
from backend.analyzers.content.scoring import (
    CATEGORY_LABELS,
    apply_weights,
    category_scores,
    collect_issues,
    narrative_summary,
    overall_score,
    severity_counts,
    summarize,
)
from backend.analyzers.content.similarity import fingerprint, similarity
from backend.errors import ScanError


def analyze_content(ctx: ContentContext, config: ContentScoringConfig | None = None) -> ContentResult:
    scoring = config or DEFAULT_SCORING
    try:
        page = extract_page(ctx.html_source, ctx.final_url or ctx.page_url, config=scoring, parsed=ctx.html)
    except Exception as exc:
        raise ScanError("CONTENT_FAILED", "Content analysis could not be completed.") from exc

    extras = []
    for extra in ctx.extra_pages[: scoring.max_dup_pages]:
        try:
            extras.append(extract_page(extra.html_source, extra.url, config=scoring))
        except Exception:
            continue

    page_type = classify_page(page)
    checks: list[CheckResult] = []
    checks.extend(run_structure(page, page_type, scoring))
    checks.extend(run_depth(page, page_type, scoring))
    checks.extend(run_readability(page, page_type, scoring))
    checks.extend(run_headings(page, page_type, scoring))
    checks.extend(run_paragraphs(page, page_type, scoring))
    checks.extend(run_duplication(page, page_type, scoring, extras))
    checks.extend(run_freshness(page, page_type, scoring))
    checks.extend(run_authorship(page, page_type, scoring))
    checks.extend(run_completeness(page, page_type, scoring))
    checks.extend(run_cta(page, page_type))
    checks.extend(run_relationships(page, page_type, len(extras)))
    checks.extend(run_language(page))
    checks = apply_weights(checks, scoring)

    categories = category_scores(checks, scoring)
    score = overall_score(checks, scoring)
    cards = [
        ContentCategoryScore(
            id=group,
            name=CATEGORY_LABELS.get(group, group),
            score=categories.get(group),
            finding_count=sum(1 for check in checks if check.group == group and check.status in {"fail", "warning"}),
        )
        for group in scoring.category_weights
    ]

    readability = measure_readability(page.main_text or page.visible_text, page.language)
    paras = page.paragraphs
    avg_para = (sum(word_count(item) for item in paras) / len(paras)) if paras else 0.0
    avg_section = (page.main_word_count / page.section_count) if page.section_count else float(page.main_word_count)
    boiler_words = word_count(page.boilerplate_text)
    boiler_ratio = (boiler_words / page.word_count) if page.word_count else 0.0
    from backend.analyzers.content.extract import repeated_blocks

    _count, repeat_ratio, _samples = repeated_blocks(page.paragraphs, page.headings)

    duplicates: list[DuplicatePair] = []
    for other in extras:
        exact = fingerprint(page.main_text) == fingerprint(other.main_text) and bool((page.main_text or "").strip())
        sim = 1.0 if exact else similarity(page.main_text, other.main_text)
        if exact or sim >= scoring.near_dup:
            duplicates.append(DuplicatePair(url=other.url, similarity=round(sim, 3), kind="exact" if exact else "near"))

    limitations = list(LIMITATIONS)
    if page.truncated:
        limitations.insert(0, "Content analysis was bounded due to configured limits.")
    if not extras:
        limitations.append("Site-wide duplicate analysis requires multiple crawled pages.")

    depth_warning = any(check.check_id == "CONTENT-DEPTH-001" and check.status == "warning" for check in checks)
    return ContentResult(
        score=score,
        summary=summarize(checks),
        narrative=narrative_summary(score, checks),
        categories=categories,
        category_cards=cards,
        checks=checks,
        findings=checks,
        issues=collect_issues(checks),
        page=ContentPageInfo(
            analyzed_url=ctx.page_url,
            final_url=ctx.final_url or ctx.page_url,
            title=page.title,
            language=page.language,
        ),
        page_type=page_type,
        metrics=ContentMetrics(
            word_count=page.word_count,
            main_word_count=page.main_word_count,
            character_count=page.character_count,
            paragraph_count=len(page.paragraphs),
            heading_count=len(page.headings),
            section_count=page.section_count,
            list_count=len(page.lists),
            table_count=page.table_count,
            average_paragraph_length=round(avg_para, 1),
            average_section_length=round(avg_section, 1),
            h1_count=sum(1 for item in page.headings if item["level"] == 1),
            h2_count=sum(1 for item in page.headings if item["level"] == 2),
            h3_count=sum(1 for item in page.headings if item["level"] == 3),
            internal_content_links=page.internal_content_links,
        ),
        readability=readability,
        signals=ContentSignals(
            main_content_detected=page.main_detected,
            thin_content=depth_warning,
            repeated_content=_count >= 2,
            duplicate_content=bool(duplicates),
            author_detected=bool(page.author_candidates),
            publication_date_detected=bool(page.dates),
            cta_detected=bool(page.cta_labels),
            boilerplate_ratio=round(min(1.0, boiler_ratio), 3),
            repeated_content_ratio=round(repeat_ratio, 3),
        ),
        structure={
            "h1_count": sum(1 for item in page.headings if item["level"] == 1),
            "h2_count": sum(1 for item in page.headings if item["level"] == 2),
            "h3_count": sum(1 for item in page.headings if item["level"] == 3),
            "sections": page.section_count,
            "main_content_found": page.main_detected,
            "lists": len(page.lists),
            "tables": page.table_count,
            "internal_content_links": page.internal_content_links,
            "cta_detected": bool(page.cta_labels),
        },
        duplicates=duplicates,
        limitations=limitations,
        severity_counts=severity_counts(checks),
        truncated=page.truncated,
    )
