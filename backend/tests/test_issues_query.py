from __future__ import annotations

from backend.issues.engine import aggregate
from backend.issues.models import UnifiedIssue
from backend.issues.query import parse_page_size, parse_search, query_issues


def _issue(**overrides) -> UnifiedIssue:
    data = {
        "issue_id": "issue_1",
        "issue_key": "seo.meta_description.missing",
        "source": "seo",
        "analyzer": "SEO Analyzer",
        "category": "SEO",
        "check_id": "SEO-META-001",
        "title": "Meta description exists",
        "description": "No meta description element was found.",
        "recommendation": "Add a concise, unique description.",
        "status": "open",
        "check_status": "fail",
        "severity": "high",
        "priority": "high",
        "priority_score": 70,
        "page_url": "https://example.com/",
        "affected_page_count": 1,
        "affected_element_count": 0,
        "pages": ["https://example.com/"],
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    data.update(overrides)
    return UnifiedIssue.model_validate(data)


def test_pagination_bounds():
    assert parse_page_size("25") == 25
    assert parse_page_size("1000") == 100
    assert parse_page_size("0") == 1
    issues = [_issue(issue_id=f"issue_{index}", title=f"Issue {index}") for index in range(30)]
    page, meta = query_issues(issues, {"page": 2, "page_size": 10})
    assert len(page) == 10
    assert meta["page"] == 2
    assert meta["page_size"] == 10
    assert meta["total"] == 30
    assert meta["pages"] == 3


def test_filtering_search_and_sort():
    issues = [
        _issue(issue_id="issue_seo", title="Missing Meta Description", priority="high", priority_score=70, category="SEO", source="seo"),
        _issue(
            issue_id="issue_js",
            issue_key="performance.javascript.large_payload",
            title="Large JavaScript Payload",
            description="JavaScript transfer is 1.8 MB.",
            category="Performance",
            source="performance",
            check_id="PERF-JS-002",
            priority="medium",
            priority_score=40,
            severity="medium",
            check_status="warning",
            recommendation="Split bundles.",
        ),
        _issue(
            issue_id="issue_pass",
            title="Title exists",
            check_status="pass",
            priority="low",
            priority_score=10,
            severity="low",
        ),
    ]
    filtered, meta = query_issues(issues, {"category": "Performance"})
    assert [item.issue_id for item in filtered] == ["issue_js"]
    searched, _ = query_issues(issues, {"search": "javascript"})
    assert [item.issue_id for item in searched] == ["issue_js"]
    default, _ = query_issues(issues, {})
    assert [item.issue_id for item in default] == ["issue_seo", "issue_js"]
    passed, _ = query_issues(issues, {"check_status": "pass"})
    assert [item.issue_id for item in passed] == ["issue_pass"]
    sorted_items, _ = query_issues(issues, {"sort": "priority", "order": "desc"})
    assert sorted_items[0].issue_id == "issue_seo"
    assert parse_search("x" * 500) == "x" * 200
    assert meta["total"] == 1


def test_aggregate_then_query_summary_counts():
    payload = aggregate(
        "scan_q",
        {
            "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
            "seo": {
                "checks": [
                    {
                        "check_id": "SEO-META-001",
                        "name": "Meta description exists",
                        "status": "fail",
                        "severity": "high",
                        "message": "Missing",
                        "page_url": "https://example.com/",
                    },
                    {
                        "check_id": "SEO-TITLE-001",
                        "name": "Page title exists",
                        "status": "pass",
                        "severity": "critical",
                        "message": "Title present",
                        "page_url": "https://example.com/",
                    },
                ]
            },
        },
    )
    assert payload.summary.total == 1
    assert payload.summary.failures == 1
    items, meta = query_issues(payload.issues, {"page": 1, "page_size": 25})
    assert meta["total"] == 1
    assert items[0].issue_key == "seo.meta_description.missing"
    by_key, _ = query_issues(payload.issues, {"issue_key": "seo.meta_description.missing"})
    assert [item.issue_id for item in by_key] == [items[0].issue_id]
    by_ids, _ = query_issues(payload.issues, {"issue_ids": items[0].issue_id})
    assert [item.issue_id for item in by_ids] == [items[0].issue_id]
    missing, _ = query_issues(payload.issues, {"issue_ids": "issue_does_not_exist"})
    assert missing == []
