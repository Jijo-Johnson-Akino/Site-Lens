from __future__ import annotations

from backend.analyzers.aeo.models import make_check
from backend.analyzers.aeo.scoring import (
    AEOScoringConfig,
    apply_weights,
    category_scores,
    overall_score,
    summarize,
)


def _check(check_id: str, group: str, status: str, severity: str = "medium"):
    return make_check(
        check_id=check_id,
        name=check_id,
        group=group,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        message=status,
        page_url="https://example.com/",
    )


def test_all_pass_scores_100() -> None:
    checks = apply_weights(
        [
            _check("AEO-ENTITY-001", "entity_understanding", "pass"),
            _check("AEO-ANSWER-001", "answer_readiness", "pass"),
            _check("AEO-QUESTION-001", "question_coverage", "pass"),
            _check("AEO-STRUCT-001", "content_structure", "pass"),
            _check("AEO-SEM-002", "semantic_structure", "pass"),
            _check("AEO-AUTHOR-001", "authorship", "pass"),
            _check("AEO-ORG-001", "organization_information", "pass"),
            _check("AEO-SCHEMA-001", "structured_information", "pass"),
            _check("AEO-EXTRACT-002", "extractability", "pass"),
        ]
    )
    assert overall_score(category_scores(checks)) == 100


def test_mixed_results_between_zero_and_hundred() -> None:
    checks = apply_weights(
        [
            _check("AEO-ENTITY-001", "entity_understanding", "pass"),
            _check("AEO-ANSWER-001", "answer_readiness", "fail"),
            _check("AEO-QUESTION-001", "question_coverage", "warning"),
        ]
    )
    score = overall_score(category_scores(checks))
    assert 0 < score < 100


def test_not_applicable_excluded() -> None:
    with_na = apply_weights(
        [
            _check("AEO-ENTITY-001", "entity_understanding", "pass"),
            _check("AEO-AUTHOR-003", "authorship", "not_applicable"),
        ]
    )
    without = apply_weights([_check("AEO-ENTITY-001", "entity_understanding", "pass")])
    assert overall_score(category_scores(with_na)) == overall_score(category_scores(without)) == 100
    assert summarize(with_na).not_applicable == 1


def test_zero_applicable_checks_scores_zero() -> None:
    checks = apply_weights([_check("AEO-AUTHOR-003", "authorship", "not_applicable")])
    categories = category_scores(checks)
    assert overall_score(categories) == 0


def test_custom_aeo_config() -> None:
    config = AEOScoringConfig(
        category_weights={"entity_understanding": 1.0},
        check_weights={"AEO-ENTITY-001": 1, "AEO-ENTITY-002": 1},
    )
    checks = apply_weights(
        [
            _check("AEO-ENTITY-001", "entity_understanding", "pass"),
            _check("AEO-ENTITY-002", "entity_understanding", "fail"),
        ],
        config,
    )
    assert overall_score(category_scores(checks, config), config) == 50
