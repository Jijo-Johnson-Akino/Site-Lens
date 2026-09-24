from __future__ import annotations

from backend.analyzers.content.extract import extract_page
from backend.analyzers.content.models import ContentPageType
from backend.analyzers.content.page_type import classify_page
from backend.analyzers.structured_data.checks import (
    run_alignment,
    run_context,
    run_detection,
    run_identity,
    run_properties,
    run_relationships,
    run_social,
    run_syntax,
    run_types,
    run_urls,
)
from backend.analyzers.structured_data.config import DEFAULT_SCORING, LIMITATIONS, SchemaScoringConfig
from backend.analyzers.structured_data.context import StructuredDataContext
from backend.analyzers.structured_data.entities import mark_broken_relationships
from backend.analyzers.structured_data.jsonld import parse_json_ld
from backend.analyzers.structured_data.microdata import parse_microdata
from backend.analyzers.structured_data.models import SchemaCategoryScore, SchemaPageInfo, SchemaResult
from backend.analyzers.structured_data.rdfa import parse_rdfa
from backend.analyzers.structured_data.scoring import (
    CATEGORY_LABELS,
    apply_weights,
    category_scores,
    collect_issues,
    narrative_summary,
    overall_score,
    severity_counts,
    summarize,
)
from backend.analyzers.structured_data.social import parse_social
from backend.errors import ScanError


def _page_type(ctx: StructuredDataContext) -> ContentPageType:
    if ctx.page_type is not None:
        return ctx.page_type
    try:
        extracted = extract_page(ctx.html_source, ctx.final_url or ctx.page_url, parsed=ctx.html)
        return classify_page(extracted)
    except Exception:
        return ContentPageType(type="unknown", confidence=0.2, reasons=["classifier unavailable"])


def analyze_structured_data(ctx: StructuredDataContext, config: SchemaScoringConfig | None = None) -> SchemaResult:
    scoring = config or DEFAULT_SCORING
    page_url = ctx.final_url or ctx.page_url
    try:
        blocks, json_entities, json_rels, json_truncated = parse_json_ld(ctx.html_source, config=scoring)
        micro_items, micro_entities, _micro_rels, micro_truncated = parse_microdata(ctx.html_source, config=scoring)
        rdfa_items, rdfa_entities, _rdfa_rels, rdfa_truncated = parse_rdfa(ctx.html_source, config=scoring)
        og, twitter = parse_social(ctx.html_source)
        page_type = _page_type(ctx)
    except Exception as exc:
        raise ScanError("SCHEMA_FAILED", "Structured data analysis could not be completed.") from exc

    entities = [*json_entities, *micro_entities, *rdfa_entities][: scoring.max_entities]
    relationships = mark_broken_relationships(entities, json_rels, page_url)
    truncated = json_truncated or micro_truncated or rdfa_truncated or len(json_entities) + len(micro_entities) + len(rdfa_entities) > scoring.max_entities

    types: list[str] = []
    seen: set[str] = set()
    for entity in entities:
        for name in entity.types:
            if name not in seen:
                seen.add(name)
                types.append(name)

    checks = []
    checks.extend(run_detection(page_url, len(blocks), len(micro_items), len(rdfa_items), page_type))
    checks.extend(run_syntax(page_url, blocks))
    checks.extend(run_context(page_url, blocks))
    checks.extend(run_types(page_url, entities, page_type))
    checks.extend(run_identity(page_url, entities, page_url))
    checks.extend(run_properties(page_url, entities))
    checks.extend(run_relationships(page_url, relationships, entities))
    checks.extend(run_urls(page_url, entities, page_url))
    checks.extend(run_alignment(page_url, entities, ctx.html or {}))
    checks.extend(run_social(page_url, og, twitter))
    checks = apply_weights(checks, scoring)[: scoring.max_findings]

    finding_ids_by_entity: dict[str, list[str]] = {}
    for check in checks:
        if check.affected_entity:
            finding_ids_by_entity.setdefault(check.affected_entity, []).append(check.check_id)
    entities = [
        entity.model_copy(update={"findings": finding_ids_by_entity.get(entity.id or entity.internal_id, [])[:8]})
        for entity in entities
    ]

    categories = category_scores(checks, scoring)
    score = overall_score(checks, scoring)
    cards = [
        SchemaCategoryScore(
            id=group,
            name=CATEGORY_LABELS.get(group, group),
            score=categories.get(group),
            finding_count=sum(1 for check in checks if check.group == group and check.status in {"fail", "warning"}),
        )
        for group in scoring.category_weights
    ]
    limitations = list(LIMITATIONS)
    if truncated:
        limitations.insert(0, "Structured data analysis was bounded due to configured limits.")

    html = ctx.html or {}
    return SchemaResult(
        score=score,
        summary=summarize(
            checks,
            jsonld_blocks=len(blocks),
            microdata_items=len(micro_items),
            rdfa_items=len(rdfa_items),
            entities=len(entities),
            schema_types=types,
        ),
        narrative=narrative_summary(score, checks),
        categories=categories,
        category_cards=cards,
        checks=checks,
        findings=checks,
        issues=collect_issues(checks),
        page=SchemaPageInfo(analyzed_url=ctx.page_url, final_url=page_url, title=html.get("title")),
        json_ld=blocks,
        microdata=micro_items,
        rdfa=rdfa_items,
        entities=entities,
        relationships=relationships[:60],
        open_graph=og,
        twitter=twitter,
        consistency={
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "broken_references": sum(1 for rel in relationships if rel.broken),
        },
        limitations=limitations,
        severity_counts=severity_counts(checks),
        truncated=truncated,
        page_type={"type": page_type.type, "confidence": page_type.confidence},
    )
