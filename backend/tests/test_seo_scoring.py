from __future__ import annotations

from backend.analyzers.seo.models import make_check
from backend.analyzers.seo.scoring import (
    SEOScoringConfig,
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
            _check("SEO-TITLE-001", "metadata", "pass"),
            _check("SEO-META-001", "metadata", "pass"),
            _check("SEO-INDEX-003", "indexability", "pass"),
            _check("SEO-H1-001", "headings", "pass"),
            _check("SEO-CAN-001", "canonical", "pass"),
            _check("SEO-IMG-001", "images", "pass"),
            _check("SEO-LINK-001", "links", "pass"),
            _check("SEO-URL-001", "technical", "pass"),
            _check("SEO-SOCIAL-001", "social", "pass"),
            _check("SEO-ROBOTS-001", "robots_sitemap", "pass"),
        ]
    )
    categories = category_scores(checks)
    assert overall_score(categories) == 100
    assert all(value == 100 for value in categories.values() if value is not None)


def test_warnings_reduce_score_but_not_to_zero() -> None:
    checks = apply_weights(
        [
            _check("SEO-TITLE-001", "metadata", "pass"),
            _check("SEO-META-001", "metadata", "warning"),
            _check("SEO-INDEX-003", "indexability", "pass"),
        ]
    )
    score = overall_score(category_scores(checks))
    assert 0 < score < 100


def test_critical_failure_hurts_more_than_low_priority() -> None:
    failed_title = apply_weights(
        [
            _check("SEO-TITLE-001", "metadata", "fail", "critical"),
            _check("SEO-SOCIAL-004", "social", "pass", "low"),
        ]
    )
    failed_twitter = apply_weights(
        [
            _check("SEO-TITLE-001", "metadata", "pass", "critical"),
            _check("SEO-SOCIAL-004", "social", "fail", "low"),
        ]
    )
    title_score = overall_score(category_scores(failed_title))
    twitter_score = overall_score(category_scores(failed_twitter))
    assert title_score < twitter_score


def test_not_applicable_excluded_from_score() -> None:
    with_na = apply_weights(
        [
            _check("SEO-TITLE-001", "metadata", "pass"),
            _check("SEO-TITLE-003", "metadata", "not_applicable"),
        ]
    )
    without_na = apply_weights([_check("SEO-TITLE-001", "metadata", "pass")])
    assert overall_score(category_scores(with_na)) == overall_score(category_scores(without_na)) == 100
    summary = summarize(with_na)
    assert summary.not_applicable == 1
    assert summary.passed == 1


def test_custom_scoring_config() -> None:
    config = SEOScoringConfig(
        category_weights={"metadata": 1.0},
        check_weights={"SEO-TITLE-001": 1, "SEO-META-001": 1},
    )
    checks = apply_weights(
        [
            _check("SEO-TITLE-001", "metadata", "pass"),
            _check("SEO-META-001", "metadata", "fail"),
        ],
        config,
    )
    categories = category_scores(checks, config)
    assert categories["metadata"] == 50
    assert overall_score(categories, config) == 50
