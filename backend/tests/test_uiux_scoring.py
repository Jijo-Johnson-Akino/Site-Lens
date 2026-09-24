from __future__ import annotations

from backend.analyzers.uiux.config import UIUXScoringConfig
from backend.analyzers.uiux.models import make_check
from backend.analyzers.uiux.scoring import apply_weights, category_scores, overall_score, summarize, viewport_score
from backend.analyzers.uiux.stub import good_snapshots, snapshot_from_parts
from backend.analyzers.uiux.analyzer import analyze_snapshots


def _check(check_id: str, group: str, status: str, viewport: str = "desktop"):
    return make_check(
        check_id=check_id,
        name=check_id,
        group=group,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        severity="medium",
        message=status,
        page_url="https://example.com/",
        viewport=viewport,
    )


def test_all_pass_scores_100() -> None:
    result = analyze_snapshots(good_snapshots())
    assert result.score == 100
    assert result.summary.failed == 0


def test_not_applicable_excluded() -> None:
    with_na = apply_weights(
        [
            _check("UX-NAV-001", "navigation", "pass", "desktop"),
            _check("UX-FORM-001", "forms", "not_applicable", "desktop"),
        ]
    )
    without = apply_weights([_check("UX-NAV-001", "navigation", "pass", "desktop")])
    config = UIUXScoringConfig(
        category_weights={"navigation": 1.0, "forms": 0.0},
        check_weights={"UX-NAV-001": 10, "UX-FORM-001": 2},
        viewport_weights={"desktop": 1.0},
    )
    assert overall_score(with_na, config) == overall_score(without, config) == 100
    assert summarize(with_na).not_applicable == 1


def test_viewport_weights_prevent_one_issue_from_zeroing_score() -> None:
    desktop = snapshot_from_parts("desktop")
    tablet = snapshot_from_parts("tablet")
    mobile = snapshot_from_parts(
        "mobile",
        overflow=True,
        overflow_px=46,
        overflowing=[{"selector": ".hero-container", "overflow_px": 46, "width": 436}],
    )
    result = analyze_snapshots([desktop, tablet, mobile])
    assert 0 < result.score < 100
    assert result.viewports["desktop"].score > result.viewports["mobile"].score


def test_custom_viewport_weights() -> None:
    checks = apply_weights(
        [
            _check("UX-RESP-001", "responsive", "pass", "desktop"),
            _check("UX-RESP-001", "responsive", "fail", "mobile"),
        ]
    )
    config = UIUXScoringConfig(
        category_weights={"responsive": 1.0},
        check_weights={"UX-RESP-001": 10},
        viewport_weights={"desktop": 1.0, "mobile": 0.0},
    )
    assert overall_score(checks, config) == 100
    assert viewport_score([checks[1]], config) == 0


def test_category_scores_match_groups() -> None:
    checks = apply_weights(
        [
            _check("UX-NAV-001", "navigation", "pass", "desktop"),
            _check("UX-NAV-001", "navigation", "fail", "mobile"),
        ]
    )
    config = UIUXScoringConfig(
        category_weights={"navigation": 1.0},
        check_weights={"UX-NAV-001": 10},
        viewport_weights={"desktop": 0.5, "mobile": 0.5},
    )
    scores = category_scores(checks, config)
    assert scores["navigation"] == 50
