from __future__ import annotations

from backend.parser.html_parser import parse_html
from backend.tests.aeo_helpers import aeo_by_id, analyze_aeo_html, load_aeo_fixture


def test_entity_schema_name_description_consistency() -> None:
    good = analyze_aeo_html(load_aeo_fixture("aeo_good.html"))
    assert aeo_by_id(good, "AEO-ENTITY-001").status == "pass"
    assert aeo_by_id(good, "AEO-ENTITY-002").status == "pass"
    assert aeo_by_id(good, "AEO-ENTITY-003").status == "pass"
    assert aeo_by_id(good, "AEO-ENTITY-004").status == "pass"
    assert "SiteBench" in (aeo_by_id(good, "AEO-ENTITY-001").detected or "")

    missing = analyze_aeo_html(load_aeo_fixture("aeo_no_entity.html"))
    assert aeo_by_id(missing, "AEO-ENTITY-001").status == "fail"
    assert aeo_by_id(missing, "AEO-ENTITY-002").status == "warning"
    assert aeo_by_id(missing, "AEO-ENTITY-003").status == "fail"


def test_answer_and_question_patterns() -> None:
    result = analyze_aeo_html(load_aeo_fixture("aeo_questions.html"))
    assert aeo_by_id(result, "AEO-QUESTION-001").status == "pass"
    assert aeo_by_id(result, "AEO-ANSWER-001").status == "pass"
    assert aeo_by_id(result, "AEO-ANSWER-002").status == "pass"
    assert aeo_by_id(result, "AEO-QUESTION-003").status == "warning"
    assert "Why use Acme" in (aeo_by_id(result, "AEO-QUESTION-003").detected or "")


def test_faq_schema_and_section() -> None:
    result = analyze_aeo_html(load_aeo_fixture("aeo_faq.html"))
    assert aeo_by_id(result, "AEO-QUESTION-002").status == "pass"
    assert "FAQPage" in (aeo_by_id(result, "AEO-QUESTION-002").detected or "")
    assert aeo_by_id(result, "AEO-SCHEMA-002").status == "pass"


def test_semantic_html() -> None:
    good = analyze_aeo_html(load_aeo_fixture("aeo_good.html"))
    assert aeo_by_id(good, "AEO-SEM-001").status == "pass"
    assert aeo_by_id(good, "AEO-SEM-002").status == "pass"
    assert aeo_by_id(good, "AEO-SEM-003").status == "not_applicable"

    article = analyze_aeo_html(load_aeo_fixture("aeo_article.html"))
    assert aeo_by_id(article, "AEO-SEM-003").status == "pass"


def test_authorship_article_and_homepage() -> None:
    article = analyze_aeo_html(load_aeo_fixture("aeo_article.html"))
    assert aeo_by_id(article, "AEO-AUTHOR-001").status == "pass"
    assert aeo_by_id(article, "AEO-AUTHOR-002").status == "pass"
    assert aeo_by_id(article, "AEO-AUTHOR-003").status == "pass"
    assert "Ada Example" in (aeo_by_id(article, "AEO-AUTHOR-001").detected or "")

    home = analyze_aeo_html(load_aeo_fixture("aeo_good.html"))
    assert aeo_by_id(home, "AEO-AUTHOR-003").status == "not_applicable"


def test_llms_txt_present_missing_error() -> None:
    present = analyze_aeo_html(
        load_aeo_fixture("aeo_good.html"),
        llms_txt={"exists": True, "status_code": 200, "body": "# SiteBench\n> Benchmark websites."},
    )
    assert aeo_by_id(present, "AEO-AI-002").status == "pass"

    missing = analyze_aeo_html(load_aeo_fixture("aeo_good.html"))
    check = aeo_by_id(missing, "AEO-AI-002")
    assert check.status == "warning"
    assert "No llms.txt file was detected." in check.message
    assert "not AI optimized" not in check.message.lower()

    error = analyze_aeo_html(
        load_aeo_fixture("aeo_good.html"),
        llms_txt={"exists": False, "status_code": 503, "body": None},
    )
    assert aeo_by_id(error, "AEO-AI-002").status == "warning"
    assert "error" in (aeo_by_id(error, "AEO-AI-002").detected or "")


def test_structured_data_valid_invalid_and_types() -> None:
    valid = analyze_aeo_html(load_aeo_fixture("aeo_good.html"))
    assert aeo_by_id(valid, "AEO-SCHEMA-001").status == "pass"
    assert aeo_by_id(valid, "AEO-ORG-003").status == "pass"
    assert "name" in (aeo_by_id(valid, "AEO-ORG-003").detected or "")

    invalid = analyze_aeo_html(
        """<html lang="en"><head><title>Broken JSON-LD</title>
        <script type="application/ld+json">{not json</script></head>
        <body><h1>Broken JSON-LD</h1><p>This page has a long enough description of the product for entity checks to have copy to read.</p></body></html>"""
    )
    assert aeo_by_id(invalid, "AEO-SCHEMA-001").status == "fail"

    product = analyze_aeo_html(
        """<html lang="en"><head><title>Gadget</title>
        <script type="application/ld+json">{"@type":"Product","name":"Gadget"}</script>
        </head><body><h1>Gadget</h1><p>Gadget is a sample product used to verify Product JSON-LD detection in tests.</p></body></html>"""
    )
    assert "Product" in (aeo_by_id(product, "AEO-SCHEMA-002").detected or "")


def test_robots_ai_crawler_mentions() -> None:
    result = analyze_aeo_html(
        load_aeo_fixture("aeo_good.html"),
        robots_txt={"exists": True, "status_code": 200, "body": "User-agent: GPTBot\nDisallow: /"},
    )
    assert aeo_by_id(result, "AEO-AI-001").status == "pass"
    assert "GPTBot" in (aeo_by_id(result, "AEO-AI-001").detected or "")
    assert "guarantee" in (aeo_by_id(result, "AEO-AI-001").why or "").lower() or "not a ranking" in (aeo_by_id(result, "AEO-AI-001").recommendation or "").lower()


def test_non_english_question_patterns_are_not_failures() -> None:
    html = """<html lang="fr"><head><title>Société Exemple</title>
    <meta name="description" content="Société Exemple fournit des outils d'analyse de sites web pour les équipes produit.">
    </head><body><header><a href="/">Société Exemple</a></header>
    <main><h1>Société Exemple</h1>
    <p>Société Exemple fournit des outils d'analyse de sites web pour les équipes produit et marketing.</p>
    </main></body></html>"""
    result = analyze_aeo_html(html)
    assert aeo_by_id(result, "AEO-QUESTION-001").status == "not_applicable"
    assert aeo_by_id(result, "AEO-ANSWER-002").status == "not_applicable"
    assert aeo_by_id(result, "AEO-QUESTION-001").language_dependent is True


def test_hidden_and_lists_and_tables() -> None:
    html = """<html lang="en"><head><title>Signals</title></head><body>
    <h1>Signals</h1>
    <p>Signals is a research site that publishes structured notes about public web pages and extractability.</p>
    <ul><li>One</li><li>Two</li><li>Three</li></ul>
    <table><tr><th>A</th><td>B</td></tr></table>
    <p style="display:none">Lots of hidden promotional text that should not dominate the page copy for extractors.</p>
    </body></html>"""
    result = analyze_aeo_html(html)
    assert aeo_by_id(result, "AEO-STRUCT-003").status == "pass"
    assert aeo_by_id(result, "AEO-STRUCT-004").status == "pass"
    assert aeo_by_id(result, "AEO-EXTRACT-004").status in {"pass", "warning"}


def test_good_fixture_has_no_hardcoded_score() -> None:
    result = analyze_aeo_html(load_aeo_fixture("aeo_good.html"))
    assert 0 <= result.score <= 100
    assert result.score != 0
    assert len(result.checks) >= 30
    assert result.insight.startswith("AI READINESS SUMMARY")
    assert "ChatGPT" not in result.narrative
    assert "AI Overview" not in result.narrative
    parsed = parse_html(load_aeo_fixture("aeo_good.html"))
    assert parsed["json_ld"]["valid"] is True
    assert "Organization" in parsed["json_ld"]["types"]
