from __future__ import annotations

from backend.analyzers.content.config import ContentScoringConfig
from backend.analyzers.content.models import make_check
from backend.analyzers.content.scoring import apply_weights, category_scores, overall_score
from backend.tests.content_helpers import analyze_html, article_html


def _check(check_id: str, group: str, status: str):
    return make_check(
        check_id=check_id,
        name=check_id,
        group=group,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        severity="medium",
        message=status,
        page_url="https://example.com/",
    )


def test_score_is_deterministic_and_bounded() -> None:
    first = analyze_html(article_html())
    second = analyze_html(article_html())
    assert first.score == second.score
    assert 0 <= first.score <= 100


def test_not_applicable_excluded() -> None:
    config = ContentScoringConfig(category_weights={"depth": 0.5, "authorship": 0.5}, check_weights={"CONTENT-DEPTH-001": 12, "CONTENT-AUTH-001": 6})
    with_na = apply_weights([_check("CONTENT-DEPTH-001", "depth", "pass"), _check("CONTENT-AUTH-001", "authorship", "not_applicable")])
    without = apply_weights([_check("CONTENT-DEPTH-001", "depth", "pass")])
    assert overall_score(with_na, config) == overall_score(without, config) == 100
    assert category_scores(with_na, config)["authorship"] is None


def test_contact_and_article_scores_differ() -> None:
    article = analyze_html(article_html())
    contact = analyze_html(
        """<!doctype html><html lang="en"><head><title>Contact us</title></head>
        <body><h1>Contact</h1><p>Email hello@example.com</p><a href="mailto:hello@example.com">Email</a></body></html>""",
        url="https://example.com/contact",
    )
    assert article.page_type.type != contact.page_type.type
    assert article.categories.get("authorship") is not None
    assert contact.categories.get("authorship") is None
    assert 0 <= contact.score <= 100


def test_unsupported_language_does_not_invent_readability_penalty() -> None:
    french = analyze_html(
        """<!doctype html><html lang="fr"><head><title>Bonjour</title></head>
        <body><main><h1>Bonjour</h1><p>Le texte francais n est pas evalue avec une formule anglaise.</p></main></body></html>""",
        url="https://example.com/fr",
    )
    assert french.readability.flesch_reading_ease is None
    assert french.categories.get("readability") is None


def test_empty_checks_do_not_nan() -> None:
    config = ContentScoringConfig(category_weights={"readability": 1.0}, check_weights={})
    score = overall_score(apply_weights([_check("CONTENT-READ-001", "readability", "not_applicable")]), config)
    assert score == 0
    assert score == score


def test_score_excludes_na_and_stays_in_range() -> None:
    article = analyze_html(article_html())
    contact = analyze_html(
        """<!doctype html><html lang="en"><head><title>Contact us</title></head>
        <body><h1>Contact</h1><p>Email hello@example.com</p></body></html>""",
        url="https://example.com/contact",
    )
    assert article.categories.get("duplication") is not None  # repetition still scores
    assert contact.categories.get("freshness") is None
    assert contact.categories.get("authorship") is None
    assert 0 <= article.score <= 100
    assert 0 <= contact.score <= 100
    assert article.score == article.score
    assert contact.score == contact.score
