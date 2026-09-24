from __future__ import annotations

from backend.issues.dedupe import merge_findings
from backend.issues.engine import aggregate, analyzer_status_map, summarize_issues
from backend.issues.grouping import group_by_category, group_by_source
from backend.issues.keys import issue_key_for
from backend.issues.normalize import (
    normalize_finding,
    normalize_selector,
    normalize_severity,
    normalize_source,
    normalize_status,
)
from backend.issues.priority import calculate_priority
from backend.issues.urls import normalize_page_url


def _check(**overrides):
    base = {
        "check_id": "SEO-META-001",
        "name": "Meta description exists",
        "status": "fail",
        "severity": "high",
        "message": "No meta description element was found.",
        "recommendation": "Add a concise, unique description that accurately summarizes the page.",
        "page_url": "https://example.com/",
        "group": "metadata",
        "score": 0,
    }
    base.update(overrides)
    return base


def test_issue_key_explicit_and_fallback():
    assert issue_key_for("seo", "SEO-TITLE-001") == "seo.title.missing"
    assert issue_key_for("seo", "SEO-META-001") == "seo.meta_description.missing"
    assert issue_key_for("mobile", "MOBILE-OVERFLOW-001") == "mobile.horizontal_overflow"
    assert issue_key_for("seo", "SEO-TITLE-002") == "seo.title.002"
    assert issue_key_for("unknown", None) == "unknown.unknown"


def test_severity_and_status_normalization():
    assert normalize_severity("serious") == "high"
    assert normalize_severity("moderate") == "medium"
    assert normalize_severity("minor") == "low"
    assert normalize_severity("critical") == "critical"
    assert normalize_severity("mystery") == "medium"
    assert normalize_status("fail") == "fail"
    assert normalize_status("warning") == "warning"
    assert normalize_status("info") == "info"
    assert normalize_status("n/a") == "not_applicable"
    assert normalize_status("passed") == "pass"


def test_source_and_selector_normalization():
    assert normalize_source("UI/UX") == "uiux"
    assert normalize_source("a11y") == "accessibility"
    assert normalize_source("schema") == "structured_data"
    assert normalize_source("weird") == "unknown"
    assert normalize_selector("  button.primary  ") == "button.primary"
    assert normalize_selector("a[href*=token]") == "a"


def test_page_url_normalization():
    assert normalize_page_url("https://example.com") == normalize_page_url("https://example.com/")
    assert normalize_page_url("https://EXAMPLE.com/about/#top") == "https://example.com/about"
    assert normalize_page_url("https://example.com/a?q=1#x") == "https://example.com/a?q=1"
    assert normalize_page_url(None, "https://example.com/") == "https://example.com/"


def test_finding_normalization_preserves_source_fields():
    finding = normalize_finding(
        _check(details={"title_length": 0}),
        source="seo",
        scan_id="scan_1",
        fallback_page="https://example.com/",
        created_at="2026-01-01T00:00:00+00:00",
    )
    assert finding is not None
    assert finding["issue_key"] == "seo.meta_description.missing"
    assert finding["finding_id"].startswith("finding_")
    assert finding["source"] == "seo"
    assert finding["category"] == "SEO"
    assert finding["recommendation"].startswith("Add a concise")
    assert finding["evidence"]["title_length"] == 0
    assert finding["status"] == "fail"


def test_malformed_finding_is_skipped():
    assert normalize_finding("bad", source="seo", scan_id="s", fallback_page=None, created_at=None) is None
    assert normalize_finding({}, source="seo", scan_id="s", fallback_page=None, created_at=None) is None


def test_deduplication_same_issue_trailing_slash():
    a = normalize_finding(_check(page_url="https://example.com/"), source="seo", scan_id="s", fallback_page=None, created_at=None)
    b = normalize_finding(_check(page_url="https://example.com"), source="seo", scan_id="s", fallback_page=None, created_at=None)
    merged = merge_findings([a, b])
    assert len(merged) == 1
    assert merged[0]["page_url"] == "https://example.com/"


def test_cross_analyzer_findings_stay_separate():
    a = normalize_finding(
        {
            "check_id": "A11Y-CTRL-001",
            "name": "Buttons have accessible names",
            "status": "fail",
            "severity": "critical",
            "message": "Button has no accessible name",
            "page_url": "https://example.com/",
            "selector": "button.icon",
        },
        source="accessibility",
        scan_id="s",
        fallback_page=None,
        created_at=None,
    )
    b = normalize_finding(
        {
            "check_id": "MOBILE-TOUCH-001",
            "name": "Touch target size",
            "status": "fail",
            "severity": "medium",
            "message": "Touch target too small",
            "page_url": "https://example.com/",
            "selector": "button.icon",
        },
        source="mobile",
        scan_id="s",
        fallback_page=None,
        created_at=None,
    )
    merged = merge_findings([a, b])
    assert len(merged) == 2
    keys = {item["issue_key"] for item in merged}
    assert keys == {"accessibility.button.name.missing", "mobile.touch_target.small"}


def test_multi_page_grouping():
    findings = []
    for path in ("/", "/about", "/services"):
        findings.append(
            normalize_finding(
                _check(page_url=f"https://example.com{path}"),
                source="seo",
                scan_id="s",
                fallback_page=None,
                created_at=None,
            )
        )
    payload = aggregate(
        "scan_multi",
        {
            "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
            "seo": {"checks": [_check(page_url=item["page_url"]) for item in findings]},
        },
    )
    issues = [item for item in payload.issues if item.issue_key == "seo.meta_description.missing"]
    assert len(issues) == 1
    assert issues[0].affected_page_count == 3
    assert len(issues[0].occurrences) == 3
    assert set(issues[0].pages) == {"https://example.com/", "https://example.com/about", "https://example.com/services"}


def test_related_issue_detection():
    payload = aggregate(
        "scan_rel",
        {
            "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
            "accessibility": {
                "checks": [
                    {
                        "check_id": "A11Y-FORM-001",
                        "name": "Form controls have accessible names",
                        "status": "fail",
                        "severity": "high",
                        "message": "Missing label",
                        "page_url": "https://example.com/",
                        "group": "forms",
                    }
                ]
            },
            "uiux": {
                "checks": [
                    {
                        "check_id": "UX-FORM-002",
                        "name": "Form fields have labels",
                        "status": "warning",
                        "severity": "medium",
                        "message": "A visible form has fields without an associated label",
                        "page_url": "https://example.com/",
                        "group": "forms",
                    }
                ]
            },
        },
    )
    by_key = {item.issue_key: item for item in payload.issues}
    assert by_key["accessibility.form.label.missing"].related_issue_ids
    assert by_key["uiux.form.usability"].issue_id in by_key["accessibility.form.label.missing"].related_issue_ids


def test_priority_calculation_does_not_overprioritize_social():
    social = {
        "issue_key": "seo.social.004",
        "status": "warning",
        "severity": "low",
        "group": "social",
        "page_url": "https://example.com/",
        "affected_element_count": 0,
        "evidence": {"detected": "Not found."},
    }
    score, label = calculate_priority(social, affected_page_count=1, primary_page="https://example.com/")
    assert score <= 34
    assert label == "low"

    a11y = {
        "issue_key": "accessibility.button.name.missing",
        "status": "fail",
        "severity": "critical",
        "group": "controls",
        "source": "accessibility",
        "check_id": "A11Y-CTRL-001",
        "page_url": "https://example.com/",
        "affected_element_count": 4,
        "evidence": {"axe_rule": "button-name", "impact": "critical"},
    }
    _, a11y_label = calculate_priority(a11y, affected_page_count=1, primary_page="https://example.com/")
    assert a11y_label in {"critical", "high"}


def test_category_and_source_grouping():
    payload = aggregate(
        "scan_group",
        {
            "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
            "seo": {"checks": [_check()]},
            "mobile": {
                "checks": [
                    {
                        "check_id": "MOBILE-OVERFLOW-001",
                        "name": "Horizontal overflow",
                        "status": "fail",
                        "severity": "high",
                        "message": "Page overflows horizontally.",
                        "page_url": "https://example.com/",
                        "details": {"document_width": 574, "viewport_width": 390, "overflow_px": 184},
                    }
                ]
            },
        },
    )
    by_category = group_by_category(payload.issues)
    by_source = group_by_source(payload.issues)
    assert "SEO" in by_category
    assert "Mobile" in by_category
    assert "seo" in by_source
    assert "mobile" in by_source
    summary = summarize_issues(payload.issues)
    assert summary.by_category["SEO"] >= 1
    assert summary.by_source["mobile"] >= 1
    assert summary.total == summary.failures + summary.warnings


def test_partial_analyzer_failure_does_not_fabricate_performance_issues():
    payload = aggregate(
        "scan_partial",
        {
            "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
            "seo": {"checks": [_check()]},
            "mobile": {
                "checks": [
                    {
                        "check_id": "MOBILE-OVERFLOW-001",
                        "name": "Horizontal overflow",
                        "status": "fail",
                        "severity": "medium",
                        "message": "Overflow",
                        "page_url": "https://example.com/",
                    }
                ]
            },
            "performance": None,
            "performance_error": {"code": "PERF_FAILED", "message": "Performance analysis could not be completed."},
        },
    )
    statuses = analyzer_status_map(
        {
            "seo": {"checks": []},
            "mobile": {"checks": []},
            "performance_error": {"code": "PERF_FAILED"},
        }
    )
    assert payload.analyzer_status["seo"] == "completed"
    assert payload.analyzer_status["mobile"] == "completed"
    assert payload.analyzer_status["performance"] == "failed"
    assert statuses["performance"] == "failed"
    sources = {item.source for item in payload.issues}
    assert "performance" not in sources
    assert "seo" in sources
    assert "mobile" in sources


def test_empty_analyzers_create_no_fake_issues():
    payload = aggregate(
        "scan_empty",
        {
            "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
            "seo": {"checks": [_check(status="pass", message="Meta description is present.")]},
        },
    )
    actionable = [item for item in payload.issues if item.check_status in {"fail", "warning"}]
    assert actionable == []
    assert payload.summary.total == 0
