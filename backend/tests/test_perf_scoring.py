from __future__ import annotations

from backend.analyzers.performance.config import PerfScoringConfig
from backend.analyzers.performance.models import make_check
from backend.analyzers.performance.scoring import apply_weights, category_scores, overall_score, summarize
from backend.tests.perf_helpers import analyze_dom, snapshot_with


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
    first = analyze_dom()
    second = analyze_dom()
    assert first.score == second.score
    assert 0 <= first.score <= 100


def test_not_applicable_excluded() -> None:
    with_na = apply_weights([_check("PERF-TTFB-001", "server", "pass"), _check("PERF-VITAL-003", "vitals", "not_applicable")])
    without = apply_weights([_check("PERF-TTFB-001", "server", "pass")])
    config = PerfScoringConfig(category_weights={"server": 0.5, "vitals": 0.5}, check_weights={"PERF-TTFB-001": 12, "PERF-VITAL-003": 6})
    assert overall_score(with_na, config) == overall_score(without, config) == 100
    assert summarize(with_na).not_applicable == 1
    assert category_scores(with_na, config)["vitals"] is None


def test_unavailable_metric_does_not_destroy_score() -> None:
    with_lcp = analyze_dom()
    without_lcp = analyze_dom(snapshot_with(vitals={"lcp": None, "cls": 0.01, "inp": None}))
    assert without_lcp.score > 0
    assert without_lcp.vitals.lcp.value is None
    assert with_lcp.score >= without_lcp.score or abs(with_lcp.score - without_lcp.score) <= 15


def test_fail_lowers_score() -> None:
    config = PerfScoringConfig(category_weights={"server": 1.0}, check_weights={"PERF-TTFB-001": 12})
    passing = overall_score(apply_weights([_check("PERF-TTFB-001", "server", "pass")]), config)
    failing = overall_score(apply_weights([_check("PERF-TTFB-001", "server", "fail")]), config)
    assert passing == 100
    assert failing == 0


def test_no_nan_or_division_by_zero_when_empty() -> None:
    config = PerfScoringConfig(category_weights={"vitals": 1.0}, check_weights={})
    score = overall_score(apply_weights([_check("PERF-VITAL-003", "vitals", "not_applicable")]), config)
    assert score == 0
    assert score == score  # not NaN
