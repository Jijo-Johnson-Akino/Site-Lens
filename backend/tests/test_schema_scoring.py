from __future__ import annotations

from backend.analyzers.structured_data.config import SchemaScoringConfig
from backend.analyzers.structured_data.models import make_check
from backend.analyzers.structured_data.scoring import apply_weights, category_scores, overall_score
from backend.tests.schema_helpers import ORG, analyze_html, jsonld, wrap


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
    html = wrap("", jsonld(ORG))
    first = analyze_html(html)
    second = analyze_html(html)
    assert first.score == second.score
    assert 0 <= first.score <= 100
    assert first.score == first.score


def test_valid_syntax_scores_higher_than_malformed() -> None:
    valid = analyze_html(wrap("", jsonld(ORG)))
    malformed = analyze_html(wrap("", jsonld("{bad")))
    assert valid.score > malformed.score
    assert 0 <= malformed.score <= 100


def test_not_applicable_excluded() -> None:
    config = SchemaScoringConfig(category_weights={"properties": 0.5, "alignment": 0.5}, check_weights={"SCHEMA-ORG-001": 10, "SCHEMA-CONSIST-001": 6})
    with_na = apply_weights([_check("SCHEMA-ORG-001", "properties", "pass"), _check("SCHEMA-CONSIST-001", "alignment", "not_applicable")])
    without = apply_weights([_check("SCHEMA-ORG-001", "properties", "pass")])
    assert overall_score(with_na, config) == overall_score(without, config) == 100
    assert category_scores(with_na, config)["alignment"] is None


def test_no_schema_is_not_an_automatic_failing_score() -> None:
    result = analyze_html(wrap("<p>Homepage copy about the company.</p>"))
    assert result.score >= 50
    assert 0 <= result.score <= 100


def test_conflicts_reduce_score() -> None:
    clean = analyze_html(wrap("", jsonld(ORG)))
    conflict = analyze_html(
        wrap(
            "",
            jsonld(
                '{"@context":"https://schema.org","@graph":[{"@type":"Organization","@id":"https://example.com/#org","name":"ABC Company"},{"@type":"Organization","@id":"https://example.com/#org","name":"XYZ Company"}]}'
            ),
        )
    )
    assert conflict.score < clean.score


def test_empty_na_does_not_nan() -> None:
    config = SchemaScoringConfig(category_weights={"syntax": 1.0}, check_weights={})
    score = overall_score(apply_weights([_check("SCHEMA-SYNTAX-001", "syntax", "not_applicable")]), config)
    assert score == 0
    assert score == score
