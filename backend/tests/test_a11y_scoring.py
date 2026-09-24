from __future__ import annotations

from backend.analyzers.accessibility.config import A11yScoringConfig
from backend.analyzers.accessibility.models import make_check
from backend.analyzers.accessibility.scoring import apply_weights, category_scores, merge_findings, overall_score, summarize
from backend.tests.a11y_helpers import analyze_dom, by_id, snapshot_with


def _check(check_id: str, group: str, status: str, **extra):
    return make_check(
        check_id=check_id,
        name=check_id,
        group=group,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        severity="medium",
        message=status,
        page_url="https://example.com/",
        **extra,
    )


def test_accessible_snapshot_score_is_high() -> None:
    result = analyze_dom()
    assert result.score >= 90
    assert 0 <= result.score <= 100


def test_same_snapshot_is_deterministic() -> None:
    first = analyze_dom()
    second = analyze_dom()
    assert first.score == second.score
    assert [item.check_id for item in first.checks] == [item.check_id for item in second.checks]
    assert [item.status for item in first.checks] == [item.status for item in second.checks]


def test_not_applicable_does_not_lower_score() -> None:
    with_na = apply_weights(
        [
            _check("A11Y-DOC-001", "document", "pass"),
            _check("A11Y-TABLE-001", "tables", "not_applicable"),
        ]
    )
    without = apply_weights([_check("A11Y-DOC-001", "document", "pass")])
    config = A11yScoringConfig(
        category_weights={"document": 0.5, "tables": 0.5},
        check_weights={"A11Y-DOC-001": 10, "A11Y-TABLE-001": 7},
    )
    assert overall_score(with_na, config) == overall_score(without, config) == 100
    assert summarize(with_na).not_applicable == 1
    assert category_scores(with_na, config)["tables"] is None


def test_critical_fail_lowers_score() -> None:
    passing = apply_weights([_check("A11Y-FORM-001", "forms", "pass")])
    failing = apply_weights([_check("A11Y-FORM-001", "forms", "fail")])
    config = A11yScoringConfig(category_weights={"forms": 1.0}, check_weights={"A11Y-FORM-001": 12})
    assert overall_score(passing, config) == 100
    assert overall_score(failing, config) == 0


def test_warning_scores_between_pass_and_fail() -> None:
    config = A11yScoringConfig(category_weights={"links": 1.0}, check_weights={"A11Y-LINK-002": 3})
    passing = overall_score(apply_weights([_check("A11Y-LINK-002", "links", "pass")]), config)
    warning = overall_score(apply_weights([_check("A11Y-LINK-002", "links", "warning")]), config)
    failing = overall_score(apply_weights([_check("A11Y-LINK-002", "links", "fail")]), config)
    assert failing < warning < passing


def test_tables_na_does_not_change_overall_when_other_categories_pass() -> None:
    no_tables = analyze_dom(snapshot_with(tables=[]))
    with_table = analyze_dom(
        snapshot_with(tables=[{"selector": "table", "headers": 2, "caption": True, "role": ""}])
    )
    assert by_id(no_tables, "A11Y-TABLE-001").status == "not_applicable"
    assert by_id(with_table, "A11Y-TABLE-001").status == "pass"
    assert no_tables.score == with_table.score


def test_merge_prefers_axe_fail_without_duplicating_ids() -> None:
    dom = [_check("A11Y-IMG-001", "images", "pass")]
    axe = [_check("A11Y-IMG-001", "images", "fail", source="axe")]
    merged = merge_findings(dom, axe)
    ids = [item.check_id for item in merged]
    assert ids.count("A11Y-IMG-001") == 1
    assert merged[0].status == "fail"
    assert merged[0].source == "axe"


def test_incomplete_axe_does_not_override_dom_fail() -> None:
    dom = [_check("A11Y-CONTRAST-001", "contrast", "fail")]
    axe = [_check("A11Y-CONTRAST-001", "contrast", "warning", source="axe", manual_review=True)]
    merged = merge_findings(dom, axe)
    assert merged[0].status == "fail"
