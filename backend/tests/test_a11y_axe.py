from __future__ import annotations

from backend.analyzers.accessibility.axe_runner import axe_to_checks, wcag_from_tags
from backend.analyzers.accessibility.config import IMPACT_SEVERITY


def test_axe_impact_maps_to_severity() -> None:
    assert IMPACT_SEVERITY["critical"] == "critical"
    assert IMPACT_SEVERITY["serious"] == "high"
    assert IMPACT_SEVERITY["moderate"] == "medium"
    assert IMPACT_SEVERITY["minor"] == "low"


def test_wcag_tag_is_preserved() -> None:
    assert wcag_from_tags(["wcag2aa", "wcag143"]) == "WCAG 1.4.3"


def test_violation_normalizes_to_fail() -> None:
    checks = axe_to_checks(
        {
            "violations": [
                {
                    "id": "image-alt",
                    "impact": "serious",
                    "help": "Images must have alternate text",
                    "description": "Ensure img elements have alternate text",
                    "helpUrl": "https://dequeuniversity.com/rules/axe/4.10/image-alt",
                    "tags": ["wcag2a", "wcag111"],
                    "nodes": [{"target": ["img"], "html": "<img>", "failureSummary": "Fix all of the following"}],
                }
            ]
        },
        "https://example.com/",
    )
    assert len(checks) == 1
    check = checks[0]
    assert check.check_id == "A11Y-IMG-001"
    assert check.status == "fail"
    assert check.severity == "high"
    assert check.source == "axe"
    assert check.wcag_reference == "WCAG 1.1.1"
    assert check.affected_element_count == 1
    assert check.help_url


def test_incomplete_is_warning_manual_review() -> None:
    checks = axe_to_checks(
        {
            "incomplete": [
                {
                    "id": "color-contrast",
                    "impact": "serious",
                    "help": "Elements must have sufficient color contrast",
                    "description": "Ensure contrast",
                    "tags": ["wcag2aa", "wcag143"],
                    "nodes": [{"target": ["p.low"], "html": "<p>", "failureSummary": "needs review"}],
                }
            ]
        },
        "https://example.com/",
    )
    assert checks[0].check_id == "A11Y-CONTRAST-001"
    assert checks[0].status == "warning"
    assert checks[0].manual_review is True
    assert "manual review" in checks[0].message.lower()


def test_violation_wins_over_incomplete_for_same_check() -> None:
    checks = axe_to_checks(
        {
            "violations": [
                {
                    "id": "color-contrast",
                    "impact": "serious",
                    "help": "Elements must have sufficient color contrast",
                    "tags": ["wcag143"],
                    "nodes": [{"target": ["p"], "html": "<p>", "failureSummary": "fail"}],
                }
            ],
            "incomplete": [
                {
                    "id": "color-contrast",
                    "impact": "serious",
                    "help": "Elements must have sufficient color contrast",
                    "tags": ["wcag143"],
                    "nodes": [{"target": ["span"], "html": "<span>", "failureSummary": "maybe"}],
                }
            ],
        },
        "https://example.com/",
    )
    contrast = [item for item in checks if item.check_id == "A11Y-CONTRAST-001"]
    assert len(contrast) == 1
    assert contrast[0].status == "fail"


def test_unmapped_axe_rule_keeps_axe_id() -> None:
    checks = axe_to_checks(
        {
            "violations": [
                {
                    "id": "region",
                    "impact": "moderate",
                    "help": "All page content should be contained by landmarks",
                    "tags": ["cat.structure"],
                    "nodes": [{"target": ["div"], "html": "<div>", "failureSummary": "landmark"}],
                }
            ]
        },
        "https://example.com/",
    )
    assert checks[0].check_id == "A11Y-AXE-region"
    assert checks[0].source == "axe"
    assert checks[0].severity == "medium"
