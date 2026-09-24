from __future__ import annotations

from backend.analyzers.mobile.config import MobileScoringConfig
from backend.analyzers.mobile.models import make_check
from backend.analyzers.mobile.scoring import apply_weights, category_scores, overall_score
from backend.analyzers.mobile.stub import snapshot_from_parts
from backend.analyzers.mobile.analyzer import analyze_snapshot


def _check(check_id: str, group: str, status: str):
    return make_check(
        check_id=check_id,
        name=check_id,
        group=group,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        severity="medium",
        message=status,
        page_url="https://example.com/",
        viewport="390x844",
    )


def test_score_is_deterministic_and_bounded() -> None:
    first = analyze_snapshot(snapshot_from_parts())
    second = analyze_snapshot(snapshot_from_parts())
    assert first.score == second.score
    assert 0 <= first.score <= 100
    assert first.score == first.score


def test_not_applicable_excluded() -> None:
    config = MobileScoringConfig(category_weights={"forms": 0.5, "overflow": 0.5}, check_weights={"MOBILE-FORM-001": 10, "MOBILE-OVERFLOW-001": 10})
    with_na = apply_weights([_check("MOBILE-FORM-001", "forms", "not_applicable"), _check("MOBILE-OVERFLOW-001", "overflow", "pass")], config)
    without = apply_weights([_check("MOBILE-OVERFLOW-001", "overflow", "pass")], config)
    assert overall_score(with_na, config) == overall_score(without, config) == 100
    assert category_scores(with_na, config)["forms"] is None


def test_overflow_and_touch_and_viewport_affect_score() -> None:
    clean = analyze_snapshot(snapshot_from_parts())
    overflow = analyze_snapshot(
        snapshot_from_parts(
            overflow=True,
            overflow_px=200,
            overflowing=[{"selector": ".pricing-table", "overflow_px": 200, "cause": "fixed_width", "isolated_scroll": False}],
        )
    )
    touch = analyze_snapshot(
        snapshot_from_parts(
            interactive_elements=1,
            touch_items=[{"selector": "button.tiny", "width": 20, "height": 20, "min_dim": 20, "below_baseline": True, "very_small": True, "in_paragraph": False}],
        )
    )
    missing = analyze_snapshot(snapshot_from_parts(viewport_present=False, viewport_content=""))
    assert overflow.score < clean.score
    assert touch.score < clean.score
    assert missing.score < clean.score
    for result in (clean, overflow, touch, missing):
        assert 0 <= result.score <= 100
        assert result.score == result.score


def test_empty_na_does_not_nan() -> None:
    config = MobileScoringConfig(category_weights={"forms": 1.0}, check_weights={})
    score = overall_score(apply_weights([_check("MOBILE-FORM-001", "forms", "not_applicable")], config), config)
    assert score == 0
    assert score == score
