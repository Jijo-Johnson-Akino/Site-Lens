from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.analyzers.accessibility.stub import StubA11yAnalyzer
from backend.analyzers.mobile.stub import StubMobileAnalyzer
from backend.analyzers.performance.stub import StubPerfAnalyzer
from backend.analyzers.uiux.stub import StubUiuxAnalyzer
from backend.api import scans as scans_api
from backend.main import app
from backend.report.config import METHODOLOGY_PARAGRAPHS, REPORT_VERSION
from backend.report.engine import assemble_report
from backend.schemas.scan import ScanRecord
from backend.scoring.repository import attach_health
from backend.scoring.weights import CATEGORY_WEIGHTS
from backend.services.scan_service import ScanService
from backend.services.url_validator import UrlValidator
from backend.services.website_fetcher import WebsiteFetcher
from backend.store.scans import InMemoryScanStore
from backend.store.screenshots import InMemoryScreenshotStore

KEYS = tuple(CATEGORY_WEIGHTS.keys())


def _all_scores(**overrides: object) -> dict:
    result = {key: {"score": 80, "summary": {"passed": 1, "warnings": 0, "failed": 0, "not_applicable": 0}, "narrative": "Stored analysis.", "categories": {}, "checks": [], "issues": []} for key in KEYS}
    result.update(overrides)
    return result


def _issue(issue_id: str, *, title: str, severity: str = "high", priority: str = "high", category: str = "SEO") -> dict:
    return {
        "issue_id": issue_id,
        "issue_key": f"key_{issue_id}",
        "source": "seo",
        "analyzer": "seo",
        "category": category,
        "check_id": "seo_title",
        "title": title,
        "description": f"{title} description",
        "recommendation": "Add a unique title.",
        "check_status": "fail",
        "severity": severity,
        "priority": priority,
        "priority_score": 90 if priority == "critical" else 70,
        "page_url": "https://example.com/pricing",
        "affected_page_count": 1,
        "pages": ["https://example.com/pricing"],
    }


def _issues_payload(items: list[dict]) -> dict:
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    by_priority = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for item in items:
        by_severity[item["severity"]] = by_severity.get(item["severity"], 0) + 1
        by_priority[item["priority"]] = by_priority.get(item["priority"], 0) + 1
    return {
        "version": 1,
        "truncated": False,
        "analyzer_status": {},
        "summary": {
            "total": len(items),
            "by_severity": by_severity,
            "by_priority": by_priority,
            "critical": by_priority["critical"],
            "high": by_priority["high"],
            "medium": by_priority["medium"],
            "low": by_priority["low"],
            "info": 0,
        },
        "issues": items,
        "groups": {},
    }


def _recs_payload(scan_id: str, items: list[dict]) -> dict:
    by_priority = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for item in items:
        by_priority[item["priority"]] = by_priority.get(item["priority"], 0) + 1
    return {
        "version": 1,
        "summary": {"total": len(items), "by_priority": by_priority, "high": by_priority["high"]},
        "recommendations": items,
        "methodology": "Stored recommendations.",
        "analyzer_status": {},
    }


def _rec(scan_id: str, rec_id: str, *, title: str, priority: str = "high") -> dict:
    return {
        "id": rec_id,
        "scan_id": scan_id,
        "recommendation_key": rec_id,
        "grouping_key": rec_id,
        "title": title,
        "summary": "Add unique, descriptive title elements to affected pages.",
        "category": "SEO",
        "priority": priority,
        "effort": "small",
        "impact": "high",
        "affected_page_count": 8,
        "issue_count": 5,
        "action_steps": ["Add unique, descriptive title elements to affected pages."],
    }


def _pages_payload(scan_id: str, *, crawled: int = 2, failed: int = 0, skipped: int = 0) -> dict:
    items = [
        {
            "id": "page_home",
            "scan_id": scan_id,
            "url": "https://example.com/",
            "normalized_url": "https://example.com/",
            "crawl_status": "crawled",
            "is_seed": True,
            "issue_count": 12,
            "page_type": "homepage",
            "page_type_label": "Homepage",
            "indexable": True,
        },
        {
            "id": "page_pricing",
            "scan_id": scan_id,
            "url": "https://example.com/pricing",
            "normalized_url": "https://example.com/pricing",
            "crawl_status": "crawled",
            "issue_count": 8,
            "page_type": "unknown",
            "page_type_label": "Unknown",
        },
    ]
    if crawled < 2:
        items = items[:crawled]
    return {
        "version": 1,
        "summary": {
            "discovered": crawled + failed + skipped,
            "crawled": crawled,
            "failed": failed,
            "skipped": skipped,
            "page_limit_reached": False,
            "depth_limit_reached": False,
        },
        "items": items,
        "internal_links": [
            {
                "id": "link_1",
                "scan_id": scan_id,
                "source_page_id": "page_home",
                "destination_page_id": "page_pricing",
                "source_url": "https://example.com/",
                "destination_url": "https://example.com/pricing",
            }
        ]
        if crawled >= 2
        else [],
        "internal_links_recorded": crawled >= 2,
    }


def _complete_result(scan_id: str = "scan_report_complete") -> dict:
    result = _all_scores(
        seo={
            "score": 82,
            "summary": {"passed": 10, "warnings": 2, "failed": 1, "not_applicable": 0},
            "narrative": "SEO narrative.",
            "categories": {"metadata": 80},
            "checks": [],
            "issues": [{"name": "Missing title", "severity": "high", "status": "fail", "message": "Title is missing.", "recommendation": "Add a title.", "page_url": "https://example.com/"}],
            "page": {"analyzed_url": "https://example.com/", "final_url": "https://example.com/", "title": "Example"},
            "indexable": {"indexable": True, "reason": None},
        },
        performance={
            "score": 68,
            "summary": {"passed": 4, "warnings": 2, "failed": 1, "not_applicable": 0},
            "narrative": "Performance narrative.",
            "categories": {},
            "checks": [],
            "issues": [],
            "environment": {"browser": "chromium", "viewport_name": "desktop", "network_profile": "default", "cache_mode": "cold"},
            "timing": {"ttfb_ms": 120.0, "load_event_ms": 1800.0},
            "vitals": {
                "lcp": {"value": 2400.0, "status": "needs_improvement", "unit": "ms"},
                "cls": {"value": 0.01, "status": "good"},
                "inp": {"value": None, "status": "unavailable", "reason": "No interaction."},
            },
            "resources": {"transfer_bytes": 500000, "js_bytes": 120000, "css_bytes": 40000, "image_bytes": 200000, "third_party_bytes": 10000, "third_party_requests": 2},
            "limitations": ["Lab measurement on a cold cache."],
        },
    )
    result["issues"] = _issues_payload(
        [
            _issue("iss_crit", title="Missing required form labels", severity="critical", priority="critical"),
            _issue("iss_high", title="Large JavaScript payload", severity="high", priority="high"),
        ]
    )
    result["recommendations"] = _recs_payload(scan_id, [_rec(scan_id, "rec_1", title="Improve Missing Page Titles")])
    result["pages"] = _pages_payload(scan_id)
    attach_health(result)
    return result


def public_dns(_host: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


def handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        text="<!doctype html><html lang='en'><head><title>Example</title></head><body><h1>Home</h1></body></html>",
        headers={"content-type": "text/html"},
    )


@pytest.fixture
def client() -> TestClient:
    store = InMemoryScanStore()
    shots = InMemoryScreenshotStore()
    validator = UrlValidator(resolver=public_dns)
    fetcher = WebsiteFetcher(
        validator=validator,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False),
    )
    scans_api.service = ScanService(
        store=store,
        validator=validator,
        fetcher=fetcher,
        uiux_analyzer=StubUiuxAnalyzer(shots),
        a11y_analyzer=StubA11yAnalyzer(),
        perf_analyzer=StubPerfAnalyzer(),
        mobile_analyzer=StubMobileAnalyzer(shots),
        screenshot_store=shots,
    )
    return TestClient(app)


def _insert(client: TestClient, scan_id: str, result: dict | None, *, status: str = "completed") -> None:
    scans_api.service._store.create(
        ScanRecord(
            id=scan_id,
            url="https://example.com",
            normalized_url="https://example.com/",
            status=status,
            progress=100 if status == "completed" else 40,
            current_step="Analysis complete" if status == "completed" else "SEO analysis",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc) if status == "completed" else None,
            result=result,
            error={"code": "TIMEOUT", "message": "Connection timed out."} if status == "failed" else None,
        )
    )


def test_complete_report_uses_stored_score_and_counts(client: TestClient) -> None:
    result = _complete_result()
    _insert(client, "scan_report_complete", result)
    response = client.get("/api/scans/scan_report_complete/report")
    assert response.status_code == 200
    body = response.json()
    score = client.get("/api/scans/scan_report_complete/score").json()
    issues = client.get("/api/scans/scan_report_complete/issues").json()
    recs = client.get("/api/scans/scan_report_complete/recommendations").json()
    pages = client.get("/api/scans/scan_report_complete/pages").json()
    assert body["report_version"] == REPORT_VERSION
    assert body["report_status"] == "ready"
    assert body["overview"]["overall_score"] == score["overall"]["score"]
    seo = next(item for item in body["categories"] if item["category"] == "seo")
    score_seo = next(item for item in score["categories"] if item["category"] == "seo")
    assert seo["score"] == score_seo["score"] == 82
    assert seo["score"] != 0
    assert body["issues"]["total"] == issues["summary"]["total"] == 2
    assert body["issues"]["by_severity"]["critical"] == 1
    assert body["recommendations"]["total"] == recs["summary"]["total"] == 1
    assert body["recommendations"]["by_category"]["SEO"] == 1
    assert body["recommendations"]["action_plan_href"] == "/scan/scan_report_complete/action-plan"
    assert body["pages"]["summary"]["crawled"] == pages["summary"]["crawled"]
    assert body["pages"]["distribution"]["have_issues"] == 2
    assert body["pages"]["distribution"]["healthy"] == 0
    assert body["scan"]["viewport"] == "Desktop"
    assert body["architecture"]["available"] is True
    assert body["architecture"]["summary"]["page_count"] == 2
    assert "Potential orphan page based on the crawled internal-link graph." in body["architecture"]["orphan_wording"]
    assert body["performance"]["timing"]["ttfb_ms"] == 120.0
    assert body["performance"]["vitals"]["inp"]["value"] is None
    assert body["competitors"]["included"] is False
    assert body["competitors"]["empty_message"] == "Competitor benchmarking was not included in this scan."
    assert body["methodology"]["paragraphs"] == list(METHODOLOGY_PARAGRAPHS)
    assert body["methodology"]["calculation_version"] == "1.0"
    assert not any(row["score"] == 0 and row["status"] == "unavailable" for row in body["categories"])


def test_partial_report_missing_analyzer(client: TestClient) -> None:
    result = _all_scores()
    result.pop("performance")
    result["performance_error"] = {"code": "PERF_UNAVAILABLE", "message": "Browser analysis unavailable."}
    result["pages"] = _pages_payload("scan_report_partial")
    attach_health(result)
    _insert(client, "scan_report_partial", result)
    body = client.get("/api/scans/scan_report_partial/report").json()
    assert body["report_status"] == "partial"
    perf_cat = next(item for item in body["categories"] if item["category"] == "performance")
    assert perf_cat["score"] is None
    assert perf_cat["status"] in {"unavailable", "failed"}
    assert body["performance"]["available"] is False
    assert "0" != str(perf_cat["score"])
    assert any("Browser analysis unavailable" in item for item in body["limitations"])


def test_missing_score_issues_recommendations_pages(client: TestClient) -> None:
    result = {
        "seo": {
            "score": 70,
            "summary": {"passed": 1, "warnings": 0, "failed": 0, "not_applicable": 0},
            "narrative": "SEO only.",
            "categories": {},
            "checks": [],
            "issues": [],
        },
        "issues": _issues_payload([]),
        "recommendations": _recs_payload("scan_report_sparse", []),
    }
    _insert(client, "scan_report_sparse", result)
    body = client.get("/api/scans/scan_report_sparse/report").json()
    assert body["report_status"] in {"partial", "unavailable"}
    assert body["score"] is None
    assert body["overview"]["overall_score"] is None
    seo = next(item for item in body["categories"] if item["category"] == "seo")
    assert seo["score"] is None
    assert seo["status"] == "unavailable"
    assert body["issues"]["total"] == 0
    assert body["issues"]["empty_message"]
    assert body["recommendations"]["total"] == 0
    assert body["pages"]["available"] is False
    assert body["architecture"]["available"] is False
    assert body["competitors"]["included"] is False


def test_page_distribution_uses_stored_page_records(client: TestClient) -> None:
    from backend.pages.reasons import FAIL_CODES, SKIP_CODES

    result = _all_scores()
    pages = _pages_payload("scan_report_dist", crawled=2)
    pages["items"].append(
        {
            "id": "page_ok",
            "scan_id": "scan_report_dist",
            "url": "https://example.com/about",
            "normalized_url": "https://example.com/about",
            "crawl_status": "crawled",
            "issue_count": 0,
        }
    )
    pages["items"].append(
        {
            "id": "page_broken",
            "scan_id": "scan_report_dist",
            "url": "https://example.com/gone",
            "normalized_url": "https://example.com/gone",
            "crawl_status": "failed",
            "failure_reason": FAIL_CODES["WEBSITE_UNREACHABLE"],
            "issue_count": 0,
        }
    )
    pages["items"].append(
        {
            "id": "page_redirect",
            "scan_id": "scan_report_dist",
            "url": "https://example.com/out",
            "normalized_url": "https://example.com/out",
            "crawl_status": "skipped",
            "skip_reason": SKIP_CODES["EXTERNAL_REDIRECT"],
            "issue_count": 0,
        }
    )
    pages["items"].append(
        {
            "id": "page_blocked",
            "scan_id": "scan_report_dist",
            "url": "https://example.com/admin",
            "normalized_url": "https://example.com/admin",
            "crawl_status": "skipped",
            "skip_reason": SKIP_CODES["BLOCKED_URL"],
            "issue_count": 0,
        }
    )
    pages["summary"]["crawled"] = 3
    pages["summary"]["failed"] = 1
    pages["summary"]["skipped"] = 2
    pages["summary"]["discovered"] = 6
    result["pages"] = pages
    attach_health(result)
    _insert(client, "scan_report_dist", result)
    body = client.get("/api/scans/scan_report_dist/report").json()
    dist = body["pages"]["distribution"]
    assert dist["healthy"] == 1
    assert dist["have_issues"] == 2
    assert dist["broken"] == 1
    assert dist["redirects"] == 1
    assert dist["blocked"] == 1


def test_missing_competitors_and_architecture_notes(client: TestClient) -> None:
    result = _all_scores()
    attach_health(result)
    _insert(client, "scan_report_nopages", result)
    body = client.get("/api/scans/scan_report_nopages/report").json()
    assert body["architecture"]["available"] is False
    assert "Architecture data is unavailable" in (body["architecture"]["empty_message"] or "")
    assert body["competitors"]["included"] is False
    assert any("Competitor benchmarking was not included" in item for item in body["limitations"])


def test_competitor_comparison_is_neutral(client: TestClient) -> None:
    primary = _complete_result("scan_report_primary")
    competitor = _all_scores(seo={"score": 78, "summary": {"passed": 1, "warnings": 0, "failed": 0, "not_applicable": 0}, "narrative": "", "categories": {}, "checks": [], "issues": []})
    competitor["pages"] = _pages_payload("scan_report_comp")
    attach_health(competitor)
    primary["competitors"] = {
        "version": 1,
        "items": [
            {
                "id": "comp_one",
                "scan_id": "scan_report_primary",
                "name": "Competitor A",
                "url": "https://competitor.example",
                "normalized_url": "https://competitor.example/",
                "competitor_scan_id": "scan_report_comp",
                "status": "completed",
            }
        ],
    }
    _insert(client, "scan_report_primary", primary)
    _insert(client, "scan_report_comp", competitor)
    body = client.get("/api/scans/scan_report_primary/report").json()
    assert body["competitors"]["included"] is True
    assert body["competitors"]["competitor_count"] == 1
    assert body["competitors"]["note"]
    dumped = str(body["competitors"]).lower()
    assert "winner" not in dumped
    assert "loser" not in dumped
    assert "#1" not in dumped
    seo_row = next(item for item in body["competitors"]["categories"] if item["id"] == "seo")
    scores = {cell["column_id"]: cell["score"] for cell in seo_row["values"]}
    assert scores["primary"] == 82
    assert 78 in scores.values()


def test_invalid_and_unauthorized_scan_access(client: TestClient) -> None:
    missing = client.get("/api/scans/scan_does_not_exist/report")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "SCAN_NOT_FOUND"

    owner = _complete_result("scan_report_owner")
    other = _all_scores(seo={"score": 12, "summary": {"passed": 0, "warnings": 0, "failed": 0, "not_applicable": 0}, "narrative": "", "categories": {}, "checks": [], "issues": []})
    attach_health(other)
    _insert(client, "scan_report_owner", owner)
    _insert(client, "scan_report_other", other)
    owned = client.get("/api/scans/scan_report_owner/report").json()
    stolen = client.get("/api/scans/scan_report_other/report").json()
    assert owned["overview"]["overall_score"] != stolen["overview"]["overall_score"]
    owner_seo = next(item for item in owned["categories"] if item["category"] == "seo")
    other_seo = next(item for item in stolen["categories"] if item["category"] == "seo")
    assert owner_seo["score"] == 82
    assert other_seo["score"] == 12

    _insert(client, "scan_report_running", None, status="running")
    running = client.get("/api/scans/scan_report_running/report")
    assert running.status_code == 409
    assert running.json()["error"]["code"] == "SCAN_NOT_READY"

    _insert(client, "scan_report_failed", None, status="failed")
    failed = client.get("/api/scans/scan_report_failed/report")
    assert failed.status_code == 409
    assert failed.json()["error"]["code"] == "SCAN_FAILED"


def test_report_does_not_recalculate_health() -> None:
    result = _all_scores(seo={"score": 10, "summary": {"passed": 0, "warnings": 0, "failed": 1, "not_applicable": 0}, "narrative": "", "categories": {}, "checks": [], "issues": []})
    attach_health(result)
    stored_overall = result["health"]["overall"]["score"]
    result["seo"]["score"] = 99
    record = ScanRecord(
        id="scan_report_frozen",
        url="https://example.com",
        normalized_url="https://example.com/",
        status="completed",
        created_at=datetime.now(timezone.utc),
        result=result,
    )
    report = assemble_report(record)
    seo = next(item for item in report["categories"] if item["category"] == "seo")
    health_seo = next(item for item in result["health"]["categories"] if item["category"] == "seo")
    assert report["overview"]["overall_score"] == stored_overall
    assert seo["score"] == health_seo["score"]
    assert seo["score"] != 99


def test_methodology_generation_and_version() -> None:
    result = _all_scores()
    attach_health(result)
    record = ScanRecord(
        id="scan_report_method",
        url="https://example.com",
        normalized_url="https://example.com/",
        status="completed",
        created_at=datetime.now(timezone.utc),
        result=result,
    )
    report = assemble_report(record)
    assert report["report_version"] == "1.0"
    assert report["methodology"]["report_version"] == "1.0"
    assert "SiteLens analyzes publicly accessible website content and behavior." in report["methodology"]["paragraphs"]
    assert report["methodology"]["score"]["calculation_version"] == "1.0"
    assert "renormal" in report["methodology"]["score"]["unavailable_behavior"].lower()
