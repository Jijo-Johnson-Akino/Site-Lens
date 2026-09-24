from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.analyzers.accessibility.stub import StubA11yAnalyzer
from backend.analyzers.mobile.stub import StubMobileAnalyzer
from backend.analyzers.performance.stub import StubPerfAnalyzer
from backend.analyzers.uiux.stub import StubUiuxAnalyzer
from backend.api import scans as scans_api
from backend.competitors.comparison import build_comparison
from backend.competitors.config import MAX_COMPETITORS
from backend.competitors.matching import suggest_matches
from backend.competitors.models import CompetitorBenchmark
from backend.competitors.snapshot import snapshot_from_record
from backend.main import app
from backend.pages.models import PageRecord
from backend.schemas.scan import ScanRecord
from backend.services.scan_service import ScanService
from backend.services.url_validator import UrlValidator
from backend.services.website_fetcher import WebsiteFetcher
from backend.store.scans import InMemoryScanStore
from backend.store.screenshots import InMemoryScreenshotStore

FIXTURES = Path(__file__).parent / "fixtures" / "competitors"


def _html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


PAGES = {
    ("alpha.example.com", "/"): _html("site_a.html"),
    ("alpha.example.com", "/about"): _html("site_a_about.html"),
    ("alpha.example.com", "/contact"): _html("site_a_contact.html"),
    ("beta.example.com", "/"): _html("site_b.html"),
    ("gamma.example.com", "/"): _html("site_c.html"),
    ("gamma.example.com", "/services"): _html("site_c_services.html"),
    ("gamma.example.com", "/services/one"): _html("site_c_service_one.html"),
}


def public_dns(_host: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


def handler(request: httpx.Request) -> httpx.Response:
    host = request.url.host
    path = request.url.path or "/"
    if path in {"/robots.txt", "/sitemap.xml", "/llms.txt"}:
        return httpx.Response(404, text="missing")
    if host == "down.example.com":
        return httpx.Response(200, content=b"\x00\x01", headers={"content-type": "application/octet-stream"})
    body = PAGES.get((host, path))
    if body is None and path.endswith("/") and (host, path.rstrip("/") or "/") in PAGES:
        body = PAGES[(host, path.rstrip("/") or "/")]
    if body is None:
        return httpx.Response(404, text="missing", headers={"content-type": "text/html"})
    return httpx.Response(200, text=body, headers={"content-type": "text/html"})


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


def _scan(client: TestClient, url: str) -> str:
    created = client.post("/api/scans", json={"url": url})
    assert created.status_code == 202
    return created.json()["scan_id"]


def test_competitor_crud_and_independent_scans(client: TestClient) -> None:
    primary = _scan(client, "https://alpha.example.com/")
    listed = client.get(f"/api/scans/{primary}/competitors")
    assert listed.status_code == 200
    assert listed.json()["competitors"] == []
    assert listed.json()["max_competitors"] == MAX_COMPETITORS
    assert "up to" in listed.json()["limit_note"].lower()

    added = client.post(f"/api/scans/{primary}/competitors", json={"name": "Site B", "url": "beta.example.com"})
    assert added.status_code == 202
    competitor = added.json()["competitor"]
    assert competitor["competitor_scan_id"] != primary
    assert competitor["normalized_url"].startswith("https://beta.example.com")

    again = client.get(f"/api/scans/{primary}/competitors")
    assert len(again.json()["competitors"]) == 1
    competitor_id = again.json()["competitors"][0]["id"]
    competitor_scan_id = again.json()["competitors"][0]["competitor_scan_id"]

    primary_body = client.get(f"/api/scans/{primary}").json()
    competitor_body = client.get(f"/api/scans/{competitor_scan_id}").json()
    assert competitor_body["status"] == "completed"
    assert competitor_body["result"]["html"]["title"] != primary_body["result"]["html"]["title"]
    assert competitor_body["result"]["seo"]["score"] != primary_body["result"]["seo"]["score"]

    duplicate_primary = client.post(
        f"/api/scans/{primary}/competitors",
        json={"name": "Self", "url": "https://alpha.example.com/"},
    )
    assert duplicate_primary.status_code == 400
    assert duplicate_primary.json()["error"]["code"] == "DUPLICATE_PRIMARY"

    duplicate = client.post(
        f"/api/scans/{primary}/competitors",
        json={"name": "Site B again", "url": "https://beta.example.com"},
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["error"]["code"] == "DUPLICATE_COMPETITOR"

    invalid = client.post(f"/api/scans/{primary}/competitors", json={"name": "", "url": "https://beta.example.com"})
    assert invalid.status_code == 400

    localhost = client.post(f"/api/scans/{primary}/competitors", json={"name": "Local", "url": "http://localhost"})
    assert localhost.status_code == 400

    extra = client.post(
        f"/api/scans/{primary}/competitors",
        json={"name": "X", "url": "https://gamma.example.com", "score": 1},
    )
    assert extra.status_code == 400

    second = client.post(
        f"/api/scans/{primary}/competitors",
        json={"name": "Site C", "url": "https://gamma.example.com/"},
    )
    assert second.status_code == 202
    assert second.json()["competitor"]["competitor_scan_id"] != competitor_scan_id

    comparison = client.get(f"/api/scans/{primary}/competitors/comparison")
    assert comparison.status_code == 200
    payload = comparison.json()
    joined = str(payload).lower()
    assert "winner" not in joined
    assert "better website" not in joined
    assert "advantage" not in joined
    scores = {row["id"]: row for row in payload["metrics"] if row["id"].startswith("score_")}
    seo_values = {cell["column_id"]: cell["value"] for cell in scores["score_seo"]["values"] if cell["available"]}
    assert len(seo_values) >= 2
    assert seo_values["primary"] != seo_values[competitor_id]
    issue_keys = {row["issue_key"] for row in payload["issues"]}
    assert "seo.title.missing" in issue_keys
    pages = {
        cell["column_id"]: cell["value"]
        for cell in next(row["values"] for row in payload["metrics"] if row["id"] == "pages_crawled")
        if cell["available"]
    }
    assert pages["primary"] >= 2
    assert pages[competitor_id] == 1
    assert payload["methodology"]["max_pages"]
    assert payload["primary"]["completed_at"]

    detail = client.get(f"/api/scans/{primary}/competitors/{competitor_id}")
    assert detail.status_code == 200
    assert detail.json()["competitor"]["competitor_scan_id"] == competitor_scan_id
    assert detail.json()["snapshot"]["categories"]["seo"]["available"] is True
    assert client.get(f"/api/scans/{primary}/competitors/comp_does_not_exist").status_code == 404
    assert client.get("/api/scans/scan_does_not_exist/competitors").status_code == 404


def test_competitor_limit_and_removal(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.competitors.service.MAX_COMPETITORS", 2)
    monkeypatch.setattr("backend.api.scans.MAX_COMPETITORS", 2)
    primary = _scan(client, "https://alpha.example.com/")
    first = client.post(f"/api/scans/{primary}/competitors", json={"name": "B", "url": "https://beta.example.com/"})
    second = client.post(f"/api/scans/{primary}/competitors", json={"name": "C", "url": "https://gamma.example.com/"})
    assert first.status_code == 202
    assert second.status_code == 202
    third = client.post(f"/api/scans/{primary}/competitors", json={"name": "Down", "url": "https://down.example.com/"})
    assert third.status_code == 400
    assert third.json()["error"]["code"] == "COMPETITOR_LIMIT"

    competitor_id = first.json()["competitor"]["id"]
    removed = client.delete(f"/api/scans/{primary}/competitors/{competitor_id}")
    assert removed.status_code == 200
    remaining = client.get(f"/api/scans/{primary}/competitors").json()["competitors"]
    assert len(remaining) == 1
    assert remaining[0]["id"] != competitor_id
    comparison = client.get(f"/api/scans/{primary}/competitors/comparison").json()
    assert len(comparison["competitors"]) == 1
    other = client.delete(f"/api/scans/{remaining[0]['competitor_scan_id']}/competitors/{remaining[0]['id']}")
    assert other.status_code == 404


def test_failed_competitor_and_rescan(client: TestClient) -> None:
    primary = _scan(client, "https://alpha.example.com/")
    failed = client.post(f"/api/scans/{primary}/competitors", json={"name": "Down", "url": "https://down.example.com/"})
    assert failed.status_code == 202
    competitor_id = failed.json()["competitor"]["id"]
    listed = client.get(f"/api/scans/{primary}/competitors").json()
    card = listed["competitors"][0]
    assert card["status"] == "failed"
    assert card["error"]
    assert "traceback" not in str(card["error"]).lower()
    assert client.get(f"/api/scans/{primary}").json()["status"] == "completed"

    comparison = client.get(f"/api/scans/{primary}/competitors/comparison").json()
    assert any("failed" in obs["text"].lower() for obs in comparison["observations"])
    perf_row = next(row for row in comparison["metrics"] if row["id"] == "score_performance")
    failed_cell = next(cell for cell in perf_row["values"] if cell["column_id"] == competitor_id)
    assert failed_cell["available"] is False
    assert failed_cell["value"] is None

    rescanned = client.post(f"/api/scans/{primary}/competitors/{competitor_id}/rescan")
    assert rescanned.status_code == 200
    listed_after = client.get(f"/api/scans/{primary}/competitors").json()["competitors"]
    assert len(listed_after) == 1
    assert listed_after[0]["id"] == competitor_id
    assert listed_after[0]["competitor_scan_id"] != card["competitor_scan_id"]


def test_page_comparison_and_suggestions(client: TestClient) -> None:
    primary = _scan(client, "https://alpha.example.com/")
    added = client.post(f"/api/scans/{primary}/competitors", json={"name": "Site C", "url": "https://gamma.example.com/"})
    competitor_id = added.json()["competitor"]["id"]
    competitor_scan_id = added.json()["competitor"]["competitor_scan_id"]
    pages = client.get(f"/api/scans/{primary}/pages").json()["items"]
    other_pages = client.get(f"/api/scans/{competitor_scan_id}/pages").json()["items"]
    primary_page = next(item for item in pages if item.get("is_seed") or str(item["url"]).endswith("/"))
    competitor_page = next(item for item in other_pages if item.get("is_seed") or str(item["url"]).endswith("/"))
    suggestions = client.get(
        f"/api/scans/{primary}/competitors/page-comparison",
        params={"primary_page_id": primary_page["id"], "competitor_id": competitor_id},
    )
    assert suggestions.status_code == 200
    assert suggestions.json()["suggestions"]
    assert suggestions.json()["suggestions"][0]["label"] == "Suggested match"
    compared = client.get(
        f"/api/scans/{primary}/competitors/page-comparison",
        params={
            "primary_page_id": primary_page["id"],
            "competitor_id": competitor_id,
            "competitor_page_id": competitor_page["id"],
        },
    )
    assert compared.status_code == 200
    titles = {row["id"]: row for row in compared.json()["metrics"]}
    assert titles["title"]["primary"] != titles["title"]["competitor"]
    missing = client.get(
        f"/api/scans/{primary}/competitors/page-comparison",
        params={"primary_page_id": "page_missing", "competitor_id": competitor_id, "competitor_page_id": competitor_page["id"]},
    )
    assert missing.status_code == 404


def test_partial_analyzer_snapshot_is_unavailable() -> None:
    now = datetime.now(timezone.utc)
    primary = ScanRecord(
        id="scan_primary",
        url="https://alpha.example.com/",
        normalized_url="https://alpha.example.com/",
        status="completed",
        progress=100,
        current_step="Analysis complete",
        created_at=now,
        completed_at=now,
        result={
            "methodology": {"version": "16", "max_pages": 50, "max_depth": 3},
            "seo": {
                "score": 80,
                "summary": {"passed": 10, "warnings": 1, "failed": 1, "not_applicable": 0},
                "checks": [{"check_id": "SEO-TITLE-001", "status": "pass"}],
            },
            "performance_error": {"code": "PERF_FAILED", "message": "Performance analysis could not be completed."},
            "issues": {
                "analyzer_status": {"seo": "completed", "performance": "failed"},
                "summary": {"total": 0, "occurrences": 0, "by_severity": {}, "by_source": {"seo": 0}},
                "issues": [],
            },
            "pages": {
                "summary": {"crawled": 1, "discovered": 1, "failed": 0, "skipped": 0, "max_pages": 50, "max_depth": 3},
                "items": [],
                "internal_links": [],
                "internal_links_recorded": False,
            },
        },
    )
    competitor = ScanRecord(
        id="scan_comp",
        url="https://beta.example.com/",
        normalized_url="https://beta.example.com/",
        status="completed",
        progress=100,
        current_step="Analysis complete",
        created_at=now,
        completed_at=now,
        result={
            "methodology": {"version": "15", "max_pages": 50, "max_depth": 3},
            "seo": {
                "score": 40,
                "summary": {"passed": 2, "warnings": 0, "failed": 4, "not_applicable": 0},
                "checks": [{"check_id": "SEO-TITLE-001", "status": "fail"}],
            },
            "performance": {
                "score": 70,
                "timing": {"ttfb_ms": 120},
                "vitals": {"lcp": {"value": 800, "unit": "ms"}},
                "resources": {"resource_bytes": 1000},
                "environment": {"browser": "chromium", "cache_mode": "cold"},
            },
            "issues": {
                "analyzer_status": {"seo": "completed", "performance": "completed"},
                "summary": {"total": 1, "occurrences": 1, "by_severity": {"high": 1}, "by_source": {"seo": 1}},
                "issues": [
                    {
                        "issue_key": "seo.title.missing",
                        "title": "Title exists",
                        "category": "SEO",
                        "source": "seo",
                        "affected_page_count": 1,
                        "occurrences": [{}],
                    }
                ],
            },
            "pages": {
                "summary": {"crawled": 1, "discovered": 1, "failed": 0, "skipped": 0, "max_pages": 50, "max_depth": 3},
                "items": [],
                "internal_links": [],
                "internal_links_recorded": False,
            },
        },
    )
    snap = snapshot_from_record(primary, column_id="primary", label="Your site", role="primary")
    assert snap["categories"]["performance"]["available"] is False
    assert snap["categories"]["performance"]["score"] is None
    benchmark = CompetitorBenchmark(
        id="comp_1",
        scan_id="scan_primary",
        name="Site B",
        url="https://beta.example.com/",
        normalized_url="https://beta.example.com/",
        competitor_scan_id="scan_comp",
        status="completed",
    )
    payload = build_comparison(primary, [(benchmark, competitor)])
    perf = next(row for row in payload["metrics"] if row["id"] == "score_performance")
    primary_cell = next(cell for cell in perf["values"] if cell["column_id"] == "primary")
    assert primary_cell["available"] is False
    assert primary_cell["value"] is None
    assert any("methodology" in warning.lower() for warning in payload["warnings"])


def test_stale_scan_and_page_matching() -> None:
    now = datetime.now(timezone.utc)
    earlier = now - timedelta(days=4)
    primary = ScanRecord(
        id="scan_p",
        url="https://alpha.example.com/",
        normalized_url="https://alpha.example.com/",
        status="completed",
        progress=100,
        created_at=now,
        completed_at=now,
        result={
            "seo": {"score": 10, "checks": []},
            "issues": {"summary": {"total": 0}, "issues": []},
            "pages": {"summary": {"crawled": 1, "discovered": 1, "max_pages": 50, "max_depth": 3}, "items": []},
        },
    )
    competitor = ScanRecord(
        id="scan_c",
        url="https://beta.example.com/",
        normalized_url="https://beta.example.com/",
        status="completed",
        progress=100,
        created_at=earlier,
        completed_at=earlier,
        result={
            "seo": {"score": 11, "checks": []},
            "issues": {"summary": {"total": 0}, "issues": []},
            "pages": {"summary": {"crawled": 1, "discovered": 1, "max_pages": 50, "max_depth": 3}, "items": []},
        },
    )
    benchmark = CompetitorBenchmark(
        id="comp_stale",
        scan_id="scan_p",
        name="Old",
        url="https://beta.example.com/",
        normalized_url="https://beta.example.com/",
        competitor_scan_id="scan_c",
        status="completed",
    )
    payload = build_comparison(primary, [(benchmark, competitor)])
    assert payload["competitors"][0]["stale"]
    assert "4 day" in payload["competitors"][0]["stale"]

    home = PageRecord(
        id="p1",
        scan_id="a",
        url="https://a.test/",
        normalized_url="https://a.test/",
        title="Pricing",
        page_type="product",
        crawl_status="crawled",
    )
    match = PageRecord(
        id="c1",
        scan_id="b",
        url="https://b.test/pricing",
        normalized_url="https://b.test/pricing",
        title="Pricing plans",
        page_type="product",
        crawl_status="crawled",
    )
    other = PageRecord(
        id="c2",
        scan_id="b",
        url="https://b.test/about",
        normalized_url="https://b.test/about",
        title="About",
        page_type="about",
        crawl_status="crawled",
    )
    suggestions = suggest_matches(home, [match, other])
    assert suggestions[0]["page_id"] == "c1"
    assert suggestions[0]["label"] == "Suggested match"


def test_incomplete_primary_cannot_add(client: TestClient) -> None:
    scans_api.service._store.create(
        ScanRecord(
            id="scan_running",
            url="https://alpha.example.com/",
            normalized_url="https://alpha.example.com/",
            status="running",
            progress=40,
            current_step="Fetching homepage",
            created_at=datetime.now(timezone.utc),
        )
    )
    added = client.post("/api/scans/scan_running/competitors", json={"name": "B", "url": "https://beta.example.com/"})
    assert added.status_code == 409

