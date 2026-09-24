from __future__ import annotations

from backend.tests.content_helpers import analyze_html, article_html, by_id, expand_sentences, load_content_fixture


def test_normal_article_has_structure_and_readability() -> None:
    result = analyze_html(load_content_fixture("article.html"))
    assert result.metrics.word_count >= 300
    assert result.metrics.paragraph_count >= 8
    assert result.metrics.heading_count >= 3
    assert result.page_type.type in {"article", "blog"}
    assert result.readability.flesch_reading_ease is not None
    assert result.readability.flesch_kincaid_grade is not None
    assert by_id(result, "CONTENT-DEPTH-001").status == "pass"
    assert result.signals.author_detected
    assert result.signals.publication_date_detected
    assert 0 <= result.score <= 100


def test_thin_page_warns() -> None:
    result = analyze_html(load_content_fixture("thin.html"), url="https://example.com/notes/thin")
    assert result.metrics.word_count < 100
    assert by_id(result, "CONTENT-DEPTH-001").status == "warning"
    assert result.signals.thin_content is True


def test_long_article_is_not_thin() -> None:
    result = analyze_html(article_html(paragraphs=28), url="https://example.com/blog/long")
    assert result.metrics.word_count > 300
    assert by_id(result, "CONTENT-DEPTH-001").status == "pass"


def test_contact_page_skips_author_and_date() -> None:
    html = """<!doctype html><html lang="en"><head><title>Contact us</title>
    <meta name="description" content="Reach the SiteBench team by email or phone during weekday hours."></head>
    <body><h1>Contact us</h1><p>Email support@example.com or call us about your account.</p>
    <form><input type="email"><button>Send</button></form>
    <a href="mailto:hello@example.com">Email</a></body></html>"""
    result = analyze_html(html, url="https://example.com/contact")
    assert result.page_type.type == "contact"
    assert by_id(result, "CONTENT-AUTH-001").status == "not_applicable"
    assert by_id(result, "CONTENT-FRESH-001").status == "not_applicable"
    assert by_id(result, "CONTENT-DEPTH-001").status == "not_applicable"


def test_product_page_classification() -> None:
    html = """<!doctype html><html lang="en"><head><title>Analytics Widget</title>
    <script type="application/ld+json">{"@type":"Product","name":"Analytics Widget"}</script>
    </head><body><h1>Analytics Widget</h1>
    <p>The widget tracks website quality signals and shows a simple dashboard for marketing teams.</p>
    <ul><li>Speed</li><li>SEO</li><li>Content</li></ul>
    <a href="/buy">Buy Now</a></body></html>"""
    result = analyze_html(html, url="https://example.com/product/widget")
    assert result.page_type.type == "product"
    assert result.signals.cta_detected is True
    assert by_id(result, "CONTENT-CTA-001").status == "pass"


def test_article_without_author_warns() -> None:
    result = analyze_html(article_html(author=None), url="https://example.com/blog/no-author")
    assert result.page_type.type in {"article", "blog"}
    assert by_id(result, "CONTENT-AUTH-001").status == "warning"
    assert result.signals.author_detected is False


def test_article_without_date_is_informational_warning() -> None:
    result = analyze_html(article_html(date=None), url="https://example.com/blog/no-date")
    check = by_id(result, "CONTENT-FRESH-001")
    assert check.status == "warning"
    assert check.severity == "info"
    assert result.signals.publication_date_detected is False


def test_repeated_paragraphs() -> None:
    repeated = "This exact paragraph is copied again so the analyzer can measure repetition in primary copy."
    html = article_html(extra_paragraph=repeated)
    html = html.replace("</article>", f"<p>{repeated}</p><p>{repeated}</p></article>", 1)
    result = analyze_html(html)
    assert by_id(result, "CONTENT-REP-001").status == "warning"
    assert result.signals.repeated_content is True


def test_exact_duplicate_pages() -> None:
    html = article_html()
    result = analyze_html(html, extra=[("https://example.com/blog/copy", html)])
    check = by_id(result, "CONTENT-DUP-001")
    assert check.status == "warning"
    assert result.duplicates
    assert result.duplicates[0].kind == "exact"
    assert result.signals.duplicate_content is True


def test_near_duplicate_pages() -> None:
    original = article_html()
    other = original.replace(
        "Visible word count is measured from extracted text after scripts and styles are removed.",
        "Visible word totals come from extracted copy after scripts and styles have been removed.",
        1,
    )
    result = analyze_html(original, extra=[("https://example.com/blog/similar", other)])
    check = by_id(result, "CONTENT-DUP-001")
    assert check.status == "warning"
    assert result.duplicates[0].kind == "near"
    assert result.duplicates[0].similarity >= 0.85


def test_non_english_skips_flesch() -> None:
    result = analyze_html(load_content_fixture("french.html"), url="https://example.com/fr/analyse")
    assert result.readability.flesch_reading_ease is None
    assert result.readability.supported is False
    assert by_id(result, "CONTENT-READ-001").status == "not_applicable"


def test_very_long_paragraph() -> None:
    long = " ".join(expand_sentences(40))
    html = article_html(paragraphs=4, extra_paragraph=long)
    result = analyze_html(html)
    assert by_id(result, "CONTENT-PARA-001").status == "warning"


def test_structured_headings_pass() -> None:
    result = analyze_html(article_html())
    assert by_id(result, "CONTENT-HEAD-002").status == "pass"
    assert by_id(result, "CONTENT-HEAD-004").status == "pass"


def test_cta_page_and_informational_na() -> None:
    with_cta = analyze_html(article_html(cta=True))
    assert by_id(with_cta, "CONTENT-CTA-001").status == "pass"
    informational = analyze_html(article_html(cta=False))
    assert by_id(informational, "CONTENT-CTA-001").status == "not_applicable"


def test_single_page_duplicate_is_not_applicable() -> None:
    result = analyze_html(article_html())
    assert by_id(result, "CONTENT-DUP-001").status == "not_applicable"
    assert by_id(result, "CONTENT-LINK-001").status == "not_applicable"


def test_scripts_and_styles_are_not_counted() -> None:
    html = """<!doctype html><html lang="en"><head><title>Visible only</title>
    <style>unusedSelectorToken { color: red; }</style>
    <script>var secretScriptTokenUnique = 1;</script></head>
    <body><p>Visible sentence about extraction safety for SiteBench content analysis.</p></body></html>"""
    result = analyze_html(html, url="https://example.com/visible")
    joined = " ".join(check.message for check in result.checks)
    assert "secretScriptTokenUnique" not in joined
    assert "unusedSelectorToken" not in joined
    assert result.metrics.word_count < 40


def test_unique_pages_are_not_duplicates() -> None:
    contact = """<!doctype html><html lang="en"><head><title>Contact us</title></head>
    <body><h1>Contact us</h1><p>Email hello@example.com for support during weekday hours.</p></body></html>"""
    result = analyze_html(article_html(), extra=[("https://example.com/contact", contact)])
    assert by_id(result, "CONTENT-DUP-001").status == "pass"
    assert result.duplicates == []


def test_empty_and_malformed_html_stay_bounded() -> None:
    empty = analyze_html("", url="https://example.com/")
    broken = analyze_html("<html><title>Broken<body><p>" + ("word " * 40), url="https://example.com/broken")
    assert 0 <= empty.score <= 100
    assert 0 <= broken.score <= 100
    assert empty.score == empty.score
    assert broken.metrics.word_count > 0


def test_resource_limits_truncate_analysis() -> None:
    from backend.analyzers.content.config import ContentScoringConfig

    result = analyze_html(
        article_html(paragraphs=24),
        config=ContentScoringConfig(max_paragraphs=4, max_words=25, max_content_chars=120),
    )
    assert result.truncated is True
    assert any("bounded" in item.lower() for item in result.limitations)
