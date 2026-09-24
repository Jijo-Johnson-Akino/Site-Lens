from __future__ import annotations

from backend.tests.schema_helpers import (
    ARTICLE,
    BROKEN,
    CONFLICT,
    DUP,
    GRAPH,
    MICRO,
    MISMATCH,
    NO_CONTEXT,
    OG,
    ORG,
    PRODUCT,
    RDFA,
    TW,
    UNKNOWN,
    WEBSITE,
    analyze_html,
    by_id,
    jsonld,
    wrap,
)


def test_valid_organization() -> None:
    result = analyze_html(wrap("", jsonld(ORG)))
    assert any(entity.types == ["Organization"] or "Organization" in entity.types for entity in result.entities)
    assert by_id(result, "SCHEMA-SYNTAX-001").status == "pass"
    assert by_id(result, "SCHEMA-ORG-001").status == "pass"
    org = next(entity for entity in result.entities if "Organization" in entity.types)
    assert org.name == "Example Company"


def test_valid_website_webpage_graph() -> None:
    result = analyze_html(wrap("", jsonld(WEBSITE) + jsonld(ORG)))
    types = {name for entity in result.entities for name in entity.types}
    assert {"WebSite", "WebPage", "Organization"} <= types
    assert by_id(result, "SCHEMA-SYNTAX-001").status == "pass"


def test_valid_article_properties() -> None:
    result = analyze_html(wrap("<p class='byline'>By Ada Example</p><time datetime='2024-04-12'>2024-04-12</time>", jsonld(ARTICLE)))
    assert by_id(result, "SCHEMA-ARTICLE-001").status == "pass"
    article = next(entity for entity in result.entities if "Article" in entity.types)
    assert article.properties.get("headline") == "How measurements work"
    assert article.properties.get("author")


def test_product_offer_relationship() -> None:
    result = analyze_html(wrap("<p>Buy for $12.00</p>", jsonld(PRODUCT)))
    assert by_id(result, "SCHEMA-PRODUCT-001").status == "pass"
    assert by_id(result, "SCHEMA-OFFER-001").status == "pass"
    predicates = {rel.predicate for rel in result.relationships}
    assert "offers" in predicates


def test_malformed_jsonld() -> None:
    result = analyze_html(wrap("", jsonld("{bad")))
    assert by_id(result, "SCHEMA-SYNTAX-001").status == "fail"
    assert result.json_ld[0].valid is False


def test_missing_context() -> None:
    result = analyze_html(wrap("", jsonld(NO_CONTEXT)))
    assert by_id(result, "SCHEMA-CONTEXT-001").status == "warning"


def test_unknown_schema_type_preserved() -> None:
    result = analyze_html(wrap("", jsonld(UNKNOWN)))
    assert "CustomType" in result.summary.schema_types
    assert by_id(result, "SCHEMA-TYPE-001").status == "info"


def test_duplicate_id() -> None:
    result = analyze_html(wrap("", jsonld(DUP)))
    assert by_id(result, "SCHEMA-ID-001").status == "warning"


def test_conflicting_id() -> None:
    result = analyze_html(wrap("", jsonld(CONFLICT)))
    assert by_id(result, "SCHEMA-ID-002").status == "warning"


def test_broken_reference() -> None:
    result = analyze_html(wrap("", jsonld(BROKEN)))
    assert by_id(result, "SCHEMA-REL-001").status == "warning"


def test_missing_core_property() -> None:
    result = analyze_html(wrap("", jsonld('{"@context":"https://schema.org","@type":"Organization","url":"https://example.com/"}')))
    assert by_id(result, "SCHEMA-ORG-001").status == "warning"


def test_missing_recommended_property() -> None:
    result = analyze_html(wrap("", jsonld('{"@context":"https://schema.org","@type":"Organization","name":"Example Company"}')))
    assert by_id(result, "SCHEMA-REC-001").status == "warning"


def test_microdata_extracted() -> None:
    result = analyze_html(wrap(MICRO))
    assert result.summary.microdata_items >= 1
    assert any("Organization" in entity.types for entity in result.entities)
    assert by_id(result, "SCHEMA-DETECT-002").status == "pass"


def test_rdfa_extracted() -> None:
    result = analyze_html(wrap(RDFA))
    assert result.summary.rdfa_items >= 1
    assert any("Organization" in entity.types for entity in result.entities)
    assert by_id(result, "SCHEMA-DETECT-003").status == "pass"


def test_multiple_jsonld_blocks() -> None:
    result = analyze_html(wrap("", jsonld(ORG) + jsonld("{bad") + jsonld(ARTICLE)))
    assert len(result.json_ld) == 3
    assert sum(1 for block in result.json_ld if block.valid) == 2
    assert by_id(result, "SCHEMA-SYNTAX-001").status == "fail"
    types = {name for entity in result.entities for name in entity.types}
    assert "Organization" in types
    assert "Article" in types


def test_graph_entities_and_relationships() -> None:
    result = analyze_html(wrap("", jsonld(GRAPH)))
    types = {name for entity in result.entities for name in entity.types}
    assert "Organization" in types and "WebPage" in types
    assert any(rel.predicate == "publisher" for rel in result.relationships)
    assert by_id(result, "SCHEMA-REL-001").status == "pass"


def test_visible_mismatch_and_match() -> None:
    mismatch = analyze_html(wrap("", jsonld(MISMATCH)))
    assert by_id(mismatch, "SCHEMA-CONSIST-001").status == "warning"
    match = analyze_html(wrap("", jsonld(ORG)))
    assert by_id(match, "SCHEMA-CONSIST-001").status == "pass"


def test_open_graph_and_twitter() -> None:
    result = analyze_html(wrap("", OG + TW))
    assert result.open_graph.properties.get("og:title") == "Example Company"
    assert result.twitter.properties.get("twitter:card") == "summary_large_image"
    assert by_id(result, "SCHEMA-OG-001").status == "pass"
    assert by_id(result, "SCHEMA-TW-001").status == "pass"


def test_no_structured_data_is_informational() -> None:
    result = analyze_html(wrap("<p>Hello there enough words for a homepage.</p>"))
    assert by_id(result, "SCHEMA-DETECT-001").status == "info"
    assert by_id(result, "SCHEMA-SYNTAX-001").status == "not_applicable"
    assert result.score >= 50
    assert 0 <= result.score <= 100
