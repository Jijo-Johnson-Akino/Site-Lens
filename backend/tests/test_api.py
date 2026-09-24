from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.analyzers.accessibility.stub import StubA11yAnalyzer
from backend.analyzers.mobile.stub import StubMobileAnalyzer
from backend.analyzers.performance.stub import StubPerfAnalyzer
from backend.analyzers.uiux.stub import StubUiuxAnalyzer
from backend.api import scans as scans_api
from backend.errors import ScanError
from backend.main import app
from backend.services.scan_service import ScanService
from backend.services.url_validator import UrlValidator
from backend.services.website_fetcher import WebsiteFetcher
from backend.store.scans import InMemoryScanStore
from backend.store.screenshots import InMemoryScreenshotStore

HTML = """<!doctype html><html lang="en"><head>
<title>Example</title>
<meta name="description" content="Hi">
<link rel="canonical" href="https://example.com/">
</head><body><h1>Home</h1><a href="/a">A</a><img src="/i.png"></body></html>"""


def public_dns(_host: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path in {"/robots.txt", "/sitemap.xml", "/llms.txt"}:
        return httpx.Response(404, text="missing")
    return httpx.Response(200, text=HTML, headers={"content-type": "text/html"})


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


def test_create_and_get_scan(client: TestClient) -> None:
    created = client.post("/api/scans", json={"url": "https://example.com"})
    assert created.status_code == 202
    body = created.json()
    assert body["status"] == "queued"
    assert body["scan_id"].startswith("scan_")
    assert body["scan_id"] != "demo-12345"

    fetched = client.get(f"/api/scans/{body['scan_id']}")
    assert fetched.status_code == 200
    payload = fetched.json()
    assert payload["status"] == "completed"
    assert payload["progress"] == 100
    assert payload["current_step"] == "Analysis complete"
    assert payload["created_at"]
    assert payload["result"]["html"]["title"] == "Example"
    assert "score" not in payload["result"]
    assert isinstance(payload["result"]["seo"]["score"], int)
    assert isinstance(payload["result"]["aeo"]["score"], int)
    assert isinstance(payload["result"]["uiux"]["score"], int)
    assert isinstance(payload["result"]["accessibility"]["score"], int)
    assert isinstance(payload["result"]["performance"]["score"], int)
    assert isinstance(payload["result"]["content"]["score"], int)
    assert isinstance(payload["result"]["structured_data"]["score"], int)
    assert isinstance(payload["result"]["mobile"]["score"], int)
    assert payload["result"].get("cro") is None or isinstance(payload["result"]["cro"]["score"], (int, type(None)))
    if payload["result"].get("cro"):
        cro_score = payload["result"]["cro"]["score"]
        if cro_score is not None:
            assert 0 <= cro_score <= 100
        cro_text = str(payload["result"]["cro"]).lower()
        assert "conversion probability" not in cro_text
        assert "revenue increase" not in cro_text
        cro = client.get(f"/api/scans/{body['scan_id']}/cro")
        assert cro.status_code == 200
        cro_body = cro.json()
        assert cro_body["scan_id"] == body["scan_id"]
        assert cro_body["score"] == cro_score
        assert cro_body["summary"]["pages_analyzed"] >= 1
        assert "does not measure actual conversion rates" in (cro_body.get("methodology") or "")
    assert payload["result"].get("trust") is None or isinstance(payload["result"]["trust"]["score"], (int, type(None)))
    if payload["result"].get("trust"):
        trust_score = payload["result"]["trust"]["score"]
        if trust_score is not None:
            assert 0 <= trust_score <= 100
        trust_text = str(payload["result"]["trust"]).lower()
        assert "this company is trustworthy" not in trust_text
        assert "website is secure" not in trust_text
        trust = client.get(f"/api/scans/{body['scan_id']}/trust")
        assert trust.status_code == 200
        trust_body = trust.json()
        assert trust_body["scan_id"] == body["scan_id"]
        assert trust_body["score"] == trust_score
        assert trust_body["summary"]["pages_analyzed"] >= 1
        assert "does not verify the truth" in (trust_body.get("methodology") or "")
    assert 0 <= payload["result"]["seo"]["score"] <= 100
    assert 0 <= payload["result"]["aeo"]["score"] <= 100
    assert 0 <= payload["result"]["uiux"]["score"] <= 100
    assert 0 <= payload["result"]["accessibility"]["score"] <= 100
    assert 0 <= payload["result"]["performance"]["score"] <= 100
    assert 0 <= payload["result"]["content"]["score"] <= 100
    assert 0 <= payload["result"]["structured_data"]["score"] <= 100
    assert 0 <= payload["result"]["mobile"]["score"] <= 100
    assert payload["result"]["seo"]["summary"]["not_applicable"] >= 2
    health_blob = payload["result"].get("health")
    assert isinstance(health_blob, dict)
    assert health_blob.get("calculation_version") == "1.0"
    overall_score = health_blob["overall"]["score"]
    if overall_score is not None:
        assert isinstance(overall_score, int)
        assert 0 <= overall_score <= 100
    health_text = str(health_blob).lower()
    assert "conversion probability" not in health_text
    assert "revenue increase" not in health_text
    assert "this company is trustworthy" not in health_text
    assert "predicted traffic" not in health_text
    assert "not a prediction of search rankings" in health_blob["score_note"].lower()
    score = client.get(f"/api/scans/{body['scan_id']}/score")
    assert score.status_code == 200
    score_body = score.json()
    assert score_body["scan_id"] == body["scan_id"]
    assert score_body["overall"]["score"] == overall_score
    assert len(score_body["categories"]) == 10
    assert {item["category"] for item in score_body["categories"]} == {
        "seo",
        "aeo",
        "uiux",
        "accessibility",
        "performance",
        "content",
        "structured_data",
        "mobile",
        "cro",
        "trust",
    }
    assert score_body["architecture"]["included_in_score"] is False
    usable = [item for item in score_body["categories"] if item["available"] and item["score"] is not None]
    available_weight = sum(item["weight"] for item in usable)
    assert available_weight == score_body["coverage"]["available_weight"]
    if usable and available_weight:
        expected = sum(item["score"] * item["weight"] for item in usable) / available_weight
        assert score_body["overall"]["score"] == int(round(expected))
    for item in score_body["categories"]:
        analyzer = payload["result"].get(item["category"])
        raw = analyzer.get("score") if isinstance(analyzer, dict) else None
        if isinstance(raw, int):
            assert item["score"] == raw
            assert item["available"] is True
        elif raw is None:
            assert item["score"] is None
            assert item["available"] is False
    method = client.get(f"/api/scans/{body['scan_id']}/score/methodology")
    assert method.status_code == 200
    assert method.json()["calculation_version"] == "1.0"
    assert abs(sum(method.json()["weights"].values()) - 100) < 1e-6

    seo = client.get(f"/api/scans/{body['scan_id']}/seo")
    assert seo.status_code == 200
    seo_body = seo.json()
    assert seo_body["scan_id"] == body["scan_id"]
    assert seo_body["score"] == payload["result"]["seo"]["score"]
    assert len(seo_body["checks"]) >= 40
    assert "passed" in seo_body["summary"]
    ids = {item["check_id"] for item in seo_body["checks"]}
    assert "SEO-TITLE-001" in ids
    assert seo_body["page"]["title"] == "Example"

    aeo = client.get(f"/api/scans/{body['scan_id']}/aeo")
    assert aeo.status_code == 200
    aeo_body = aeo.json()
    assert aeo_body["scan_id"] == body["scan_id"]
    assert aeo_body["score"] == payload["result"]["aeo"]["score"]
    assert len(aeo_body["checks"]) >= 30
    assert "AEO-ENTITY-001" in {item["check_id"] for item in aeo_body["checks"]}
    assert "insight" in aeo_body
    assert "ChatGPT" not in (aeo_body.get("narrative") or "")

    uiux = client.get(f"/api/scans/{body['scan_id']}/uiux")
    assert uiux.status_code == 200
    uiux_body = uiux.json()
    assert uiux_body["scan_id"] == body["scan_id"]
    assert uiux_body["score"] == payload["result"]["uiux"]["score"]
    assert len(uiux_body["checks"]) >= 90
    assert "UX-RESP-001" in {item["check_id"] for item in uiux_body["checks"]}
    assert set(uiux_body["viewports"]) >= {"desktop", "tablet", "mobile"}
    assert len(uiux_body["screenshots"]) == 3
    assert "path" not in uiux_body["screenshots"][0]
    shot = client.get(f"/api/scans/{body['scan_id']}/uiux/screenshots/mobile")
    assert shot.status_code == 200
    assert shot.headers["content-type"].startswith("image/png")
    assert shot.content[:8] == b"\x89PNG\r\n\x1a\n"

    a11y = client.get(f"/api/scans/{body['scan_id']}/accessibility")
    assert a11y.status_code == 200
    a11y_body = a11y.json()
    assert a11y_body["scan_id"] == body["scan_id"]
    assert a11y_body["status"] == "completed"
    assert a11y_body["score"] == payload["result"]["accessibility"]["score"]
    assert a11y_body["tool"]["name"] == "axe-core"
    assert a11y_body["standard"]["automated_only"] is True
    assert a11y_body["findings"]
    assert a11y_body["checks"]
    assert "A11Y-DOC-001" in {item["check_id"] for item in a11y_body["checks"]}
    assert a11y_body["limitations"]
    joined = " ".join(a11y_body["limitations"]).lower()
    assert "wcag" in joined
    assert "compliant" in joined or "compliance" in joined
    assert "fully accessible" not in joined

    perf = client.get(f"/api/scans/{body['scan_id']}/performance")
    assert perf.status_code == 200
    perf_body = perf.json()
    assert perf_body["scan_id"] == body["scan_id"]
    assert perf_body["status"] == "completed"
    assert perf_body["score"] == payload["result"]["performance"]["score"]
    assert perf_body["environment"]["browser"] == "chromium"
    assert perf_body["environment"]["cache_mode"] == "cold"
    assert perf_body["vitals"]["inp"]["value"] is None
    assert perf_body["vitals"]["inp"]["status"] == "unavailable"
    assert perf_body["timing"]["ttfb_ms"] is not None
    assert "PERF-TTFB-001" in {item["check_id"] for item in perf_body["checks"]}
    assert perf_body["limitations"]
    assert "real-world" in " ".join(perf_body["limitations"]).lower() or "automated" in " ".join(perf_body["limitations"]).lower()

    content = client.get(f"/api/scans/{body['scan_id']}/content")
    assert content.status_code == 200
    content_body = content.json()
    assert content_body["scan_id"] == body["scan_id"]
    assert content_body["status"] == "completed"
    assert content_body["score"] == payload["result"]["content"]["score"]
    assert content_body["page_type"]["type"]
    assert isinstance(content_body["metrics"]["word_count"], int)
    assert "CONTENT-DEPTH-001" in {item["check_id"] for item in content_body["checks"]}
    assert content_body["limitations"]
    assert "editorial" in " ".join(content_body["limitations"]).lower()
    assert content_body["readability"]["flesch_reading_ease"] is None or isinstance(content_body["readability"]["flesch_reading_ease"], (int, float))

    schema = client.get(f"/api/scans/{body['scan_id']}/structured-data")
    assert schema.status_code == 200
    schema_body = schema.json()
    assert schema_body["scan_id"] == body["scan_id"]
    assert schema_body["status"] == "completed"
    assert schema_body["score"] == payload["result"]["structured_data"]["score"]
    assert "SCHEMA-DETECT-001" in {item["check_id"] for item in schema_body["checks"]}
    assert schema_body["limitations"]
    assert "rich results" in " ".join(schema_body["limitations"]).lower() or "ranking" in " ".join(schema_body["limitations"]).lower()
    assert schema_body["open_graph"] is not None
    assert schema_body["twitter"] is not None

    mobile = client.get(f"/api/scans/{body['scan_id']}/mobile")
    assert mobile.status_code == 200
    mobile_body = mobile.json()
    assert mobile_body["scan_id"] == body["scan_id"]
    assert mobile_body["status"] == "completed"
    assert mobile_body["score"] == payload["result"]["mobile"]["score"]
    assert mobile_body["environment"]["browser"] == "chromium"
    assert mobile_body["environment"]["device_profile"] == "mobile"
    assert mobile_body["environment"]["touch_enabled"] is True
    assert mobile_body["viewport"]["width"] == 390
    assert "MOBILE-VIEW-001" in {item["check_id"] for item in mobile_body["checks"]}
    assert mobile_body["limitations"]
    assert "certified" not in " ".join(mobile_body["limitations"]).lower()
    assert mobile_body["findings"]
    shot = client.get(f"/api/scans/{body['scan_id']}/mobile/screenshots/mobile_390")
    assert shot.status_code == 200
    assert shot.headers["content-type"].startswith("image/png")
    assert shot.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert "path" not in mobile_body["screenshots"][0]

    issues = client.get(f"/api/scans/{body['scan_id']}/issues")
    assert issues.status_code == 200
    issues_body = issues.json()
    assert issues_body["scan_id"] == body["scan_id"]
    assert "items" in issues_body
    assert issues_body["pagination"]["page"] == 1
    assert issues_body["pagination"]["page_size"] == 25
    assert issues_body["pagination"]["total"] >= 0
    assert "summary" in issues_body
    assert issues_body["analyzer_status"]["seo"] == "completed"
    assert issues_body["analyzer_status"]["mobile"] == "completed"
    assert issues_body["analyzer_status"]["cro"] in {"completed", "failed", "missing"}
    assert issues_body["analyzer_status"]["trust"] in {"completed", "failed", "missing"}
    assert "score" not in issues_body
    for item in issues_body["items"]:
        assert item["check_status"] in {"fail", "warning"}
        assert item["status"] == "open"
        assert item["issue_key"]
        assert item["issue_id"].startswith("issue_")

    summary = client.get(f"/api/scans/{body['scan_id']}/issues/summary")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["summary"]["total"] == issues_body["summary"]["total"]
    assert "by_category" in summary_body["summary"]
    assert "SEO" in summary_body["summary"]["by_category"]

    filtered = client.get(f"/api/scans/{body['scan_id']}/issues", params={"category": "SEO"})
    assert filtered.status_code == 200
    assert all(item["category"] == "SEO" for item in filtered.json()["items"])

    searched = client.get(f"/api/scans/{body['scan_id']}/issues", params={"search": "meta"})
    assert searched.status_code == 200

    sorted_issues = client.get(f"/api/scans/{body['scan_id']}/issues", params={"sort": "priority", "order": "desc"})
    assert sorted_issues.status_code == 200

    paged = client.get(f"/api/scans/{body['scan_id']}/issues", params={"page": 1, "page_size": 5})
    assert paged.status_code == 200
    assert paged.json()["pagination"]["page_size"] == 5
    assert len(paged.json()["items"]) <= 5

    oversized = client.get(f"/api/scans/{body['scan_id']}/issues", params={"page_size": 1000})
    assert oversized.json()["pagination"]["page_size"] == 100

    if issues_body["items"]:
        issue_id = issues_body["items"][0]["issue_id"]
        detail = client.get(f"/api/scans/{body['scan_id']}/issues/{issue_id}")
        assert detail.status_code == 200
        detail_body = detail.json()
        assert detail_body["issue"]["issue_id"] == issue_id
        assert detail_body["issue"]["source"]
        assert "evidence" in detail_body["issue"]
        assert "original_finding" in detail_body["issue"]
        assert "related_issues" in detail_body["issue"]

    missing_issue = client.get(f"/api/scans/{body['scan_id']}/issues/issue_does_not_exist")
    assert missing_issue.status_code == 404
    assert missing_issue.json()["error"]["code"] == "ISSUE_NOT_FOUND"

    recs = client.get(f"/api/scans/{body['scan_id']}/recommendations")
    assert recs.status_code == 200
    recs_body = recs.json()
    assert recs_body["scan_id"] == body["scan_id"]
    assert recs_body["pagination"]["page"] == 1
    assert recs_body["pagination"]["page_size"] == 25
    assert recs_body["pagination"]["total"] >= 0
    assert "summary" in recs_body
    assert "methodology" in recs_body
    assert "score" not in recs_body
    assert recs_body["analyzer_status"]["seo"] == "completed"
    oversized_recs = client.get(f"/api/scans/{body['scan_id']}/recommendations", params={"page_size": 1000})
    assert oversized_recs.json()["pagination"]["page_size"] == 100
    searched_recs = client.get(f"/api/scans/{body['scan_id']}/recommendations", params={"search": "title"})
    assert searched_recs.status_code == 200
    sorted_recs = client.get(f"/api/scans/{body['scan_id']}/recommendations", params={"sort": "priority", "order": "desc"})
    assert sorted_recs.status_code == 200
    if recs_body["items"]:
        rec_id = recs_body["items"][0]["id"]
        assert recs_body["items"][0]["action_steps"]
        assert "issue_ids" in recs_body["items"][0]
        rec_detail = client.get(f"/api/scans/{body['scan_id']}/recommendations/{rec_id}")
        assert rec_detail.status_code == 200
        detail_body = rec_detail.json()
        assert detail_body["recommendation"]["id"] == rec_id
        assert detail_body["recommendation"]["action_steps"]
        assert detail_body["recommendation"]["rationale"]
        assert "evidence" in detail_body["recommendation"]
        patched = client.patch(
            f"/api/scans/{body['scan_id']}/recommendations/{rec_id}",
            json={"status": "in_progress"},
        )
        assert patched.status_code == 200
        assert patched.json()["recommendation"]["status"] == "in_progress"
        again = client.get(f"/api/scans/{body['scan_id']}/recommendations/{rec_id}")
        assert again.json()["recommendation"]["status"] == "in_progress"
        invalid_patch = client.patch(
            f"/api/scans/{body['scan_id']}/recommendations/{rec_id}",
            json={"status": "done", "title": "nope"},
        )
        assert invalid_patch.status_code == 400
    missing_rec = client.get(f"/api/scans/{body['scan_id']}/recommendations/rec_does_not_exist")
    assert missing_rec.status_code == 404
    assert missing_rec.json()["error"]["code"] == "RECOMMENDATION_NOT_FOUND"

    pages = client.get(f"/api/scans/{body['scan_id']}/pages")
    assert pages.status_code == 200
    pages_body = pages.json()
    assert pages_body["scan_id"] == body["scan_id"]
    assert "items" in pages_body
    assert pages_body["pagination"]["page"] == 1
    assert pages_body["pagination"]["page_size"] == 25
    assert pages_body["pagination"]["total"] >= 1
    assert pages_body["summary"]["discovered"] >= 1
    assert pages_body["summary"]["crawled"] >= 1
    assert pages_body["limits"]["max_pages"] == 50
    assert pages_body["limits"]["max_depth"] == 3
    assert "score" not in pages_body
    page_ids = {item["id"] for item in pages_body["items"]}
    urls = {item["normalized_url"] for item in pages_body["items"]}
    assert any(url.rstrip("/").endswith("example.com") or url.endswith("example.com/") for url in urls)
    seed = next(item for item in pages_body["items"] if item.get("is_seed"))
    assert seed["title"] == "Example"
    if seed["seo"] is not None:
        assert isinstance(seed["seo"], int)
    assert "seo" in seed["available_analyzers"]

    searched = client.get(f"/api/scans/{body['scan_id']}/pages", params={"search": "Example"})
    assert searched.status_code == 200
    assert searched.json()["pagination"]["total"] >= 1

    typed = client.get(f"/api/scans/{body['scan_id']}/pages", params={"page_type": "homepage"})
    assert typed.status_code == 200

    status_filter = client.get(f"/api/scans/{body['scan_id']}/pages", params={"crawl_status": "crawled"})
    assert status_filter.status_code == 200
    assert all(item["crawl_status"] == "crawled" for item in status_filter.json()["items"])

    http_filter = client.get(f"/api/scans/{body['scan_id']}/pages", params={"http_status": "2xx"})
    assert http_filter.status_code == 200

    issues_filter = client.get(f"/api/scans/{body['scan_id']}/pages", params={"has_issues": "true"})
    assert issues_filter.status_code == 200

    sorted_pages = client.get(f"/api/scans/{body['scan_id']}/pages", params={"sort": "issue_count", "order": "desc"})
    assert sorted_pages.status_code == 200
    counts = [item["issue_count"] for item in sorted_pages.json()["items"]]
    assert counts == sorted(counts, reverse=True)

    paged = client.get(f"/api/scans/{body['scan_id']}/pages", params={"page": 1, "page_size": 1})
    assert paged.status_code == 200
    assert paged.json()["pagination"]["page_size"] == 1
    assert len(paged.json()["items"]) <= 1

    oversized = client.get(f"/api/scans/{body['scan_id']}/pages", params={"page_size": 1000})
    assert oversized.json()["pagination"]["page_size"] == 100

    architecture = client.get(f"/api/scans/{body['scan_id']}/architecture")
    assert architecture.status_code == 200
    arch_body = architecture.json()
    assert arch_body["scan_id"] == body["scan_id"]
    assert arch_body["summary"]["page_count"] >= 1
    assert "architecture_score" not in arch_body
    assert "score" not in arch_body["summary"]
    assert isinstance(arch_body["nodes"], list)
    assert isinstance(arch_body["edges"], list)
    assert arch_body["summary"]["internal_link_count"] >= 1
    home_node = next(item for item in arch_body["nodes"] if item.get("is_seed"))
    assert home_node["inbound_link_count"] >= 0
    assert home_node["outbound_link_count"] >= 1
    assert home_node["depth"] == 0
    assert "url_path_depth" in home_node
    arch_page = client.get(f"/api/scans/{body['scan_id']}/architecture/pages/{home_node['id']}")
    assert arch_page.status_code == 200
    assert arch_page.json()["page"]["id"] == home_node["id"]
    assert "inbound_links" in arch_page.json()
    links = client.get(f"/api/scans/{body['scan_id']}/architecture/links", params={"page_size": 1000})
    assert links.status_code == 200
    assert links.json()["pagination"]["page_size"] == 100
    missing_arch_page = client.get(f"/api/scans/{body['scan_id']}/architecture/pages/page_does_not_exist")
    assert missing_arch_page.status_code == 404

    detail = client.get(f"/api/scans/{body['scan_id']}/pages/{seed['id']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["page"]["id"] == seed["id"]
    assert detail_body["page"]["url"]
    assert "analyzers" in detail_body["page"]
    assert "issues" in detail_body["page"]
    assert "traceback" not in str(detail_body).lower()

    missing_page = client.get(f"/api/scans/{body['scan_id']}/pages/page_does_not_exist")
    assert missing_page.status_code == 404
    assert missing_page.json()["error"]["code"] == "PAGE_NOT_FOUND"


def test_seo_not_ready_and_missing(client: TestClient) -> None:
    from datetime import datetime, timezone

    from backend.api import scans as scans_api
    from backend.schemas.scan import ScanRecord

    running = ScanRecord(
        id="scan_runningseo",
        url="https://example.com",
        normalized_url="https://example.com/",
        status="running",
        progress=30,
        current_step="Fetching homepage",
        created_at=datetime.now(timezone.utc),
    )
    scans_api.service._store.create(running)
    response = client.get("/api/scans/scan_runningseo/seo")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SCAN_NOT_READY"

    missing = client.get("/api/scans/scan_does_not_exist/seo")
    assert missing.status_code == 404

    aeo_running = client.get("/api/scans/scan_runningseo/aeo")
    assert aeo_running.status_code == 409
    assert aeo_running.json()["error"]["code"] == "SCAN_NOT_READY"

    uiux_running = client.get("/api/scans/scan_runningseo/uiux")
    assert uiux_running.status_code == 409
    assert uiux_running.json()["error"]["code"] == "SCAN_NOT_READY"

    a11y_running = client.get("/api/scans/scan_runningseo/accessibility")
    assert a11y_running.status_code == 409
    assert a11y_running.json()["error"]["code"] == "SCAN_NOT_READY"

    perf_running = client.get("/api/scans/scan_runningseo/performance")
    assert perf_running.status_code == 409
    assert perf_running.json()["error"]["code"] == "SCAN_NOT_READY"

    content_running = client.get("/api/scans/scan_runningseo/content")
    assert content_running.status_code == 409
    assert content_running.json()["error"]["code"] == "SCAN_NOT_READY"

    schema_running = client.get("/api/scans/scan_runningseo/structured-data")
    assert schema_running.status_code == 409
    assert schema_running.json()["error"]["code"] == "SCAN_NOT_READY"

    mobile_running = client.get("/api/scans/scan_runningseo/mobile")
    assert mobile_running.status_code == 409
    assert mobile_running.json()["error"]["code"] == "SCAN_NOT_READY"

    issues_running = client.get("/api/scans/scan_runningseo/issues")
    assert issues_running.status_code == 409
    assert issues_running.json()["error"]["code"] == "SCAN_NOT_READY"
    recs_running = client.get("/api/scans/scan_runningseo/recommendations")
    assert recs_running.status_code == 409
    assert recs_running.json()["error"]["code"] == "SCAN_NOT_READY"
    score_running = client.get("/api/scans/scan_runningseo/score")
    assert score_running.status_code == 409
    assert score_running.json()["error"]["code"] == "SCAN_NOT_READY"

    pages_running = client.get("/api/scans/scan_runningseo/pages")
    assert pages_running.status_code == 200
    assert pages_running.json()["items"] == []
    assert pages_running.json()["in_progress"] is True
    architecture_running = client.get("/api/scans/scan_runningseo/architecture")
    assert architecture_running.status_code == 200
    assert architecture_running.json()["nodes"] == []


def test_create_scan_rejects_localhost(client: TestClient) -> None:
    response = client.post("/api/scans", json={"url": "http://127.0.0.1"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] in {"BLOCKED_URL", "INVALID_URL"}


def test_create_scan_concurrency_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import datetime, timezone

    from backend.api import scans as scans_api
    from backend.schemas.scan import ScanRecord

    monkeypatch.setattr("backend.services.scan_service.MAX_CONCURRENT_SCANS", 1)
    scans_api.service._store.create(
        ScanRecord(
            id="scan_busy_limit",
            url="https://busy.example.com",
            normalized_url="https://busy.example.com/",
            status="running",
            created_at=datetime.now(timezone.utc),
        )
    )
    response = client.post("/api/scans", json={"url": "https://example.com"})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "SCAN_LIMIT"


def test_patch_malformed_json_is_validation_error(client: TestClient) -> None:
    response = client.patch(
        "/api/scans/scan_missing/recommendations/rec_missing",
        content=b"{",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_missing_scan(client: TestClient) -> None:
    response = client.get("/api/scans/scan_does_not_exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCAN_NOT_FOUND"
    pages = client.get("/api/scans/scan_does_not_exist/pages")
    assert pages.status_code == 404
    assert pages.json()["error"]["code"] == "SCAN_NOT_FOUND"
    architecture = client.get("/api/scans/scan_does_not_exist/architecture")
    assert architecture.status_code == 404
    assert architecture.json()["error"]["code"] == "SCAN_NOT_FOUND"
    recs = client.get("/api/scans/scan_does_not_exist/recommendations")
    assert recs.status_code == 404
    assert recs.json()["error"]["code"] == "SCAN_NOT_FOUND"
    score = client.get("/api/scans/scan_does_not_exist/score")
    assert score.status_code == 404
    assert score.json()["error"]["code"] == "SCAN_NOT_FOUND"


def test_pages_scan_isolation(client: TestClient) -> None:
    from datetime import datetime, timezone

    from backend.api import scans as scans_api
    from backend.pages.ids import make_page_id
    from backend.schemas.scan import ScanRecord

    page_id = make_page_id("scan_owner", "https://example.com/")
    owner = ScanRecord(
        id="scan_owner",
        url="https://example.com",
        normalized_url="https://example.com/",
        status="completed",
        progress=100,
        current_step="Analysis complete",
        created_at=datetime.now(timezone.utc),
        result={
            "pages": {
                "version": 1,
                "summary": {"discovered": 1, "crawled": 1, "failed": 0, "skipped": 0, "max_pages": 50, "max_depth": 3},
                "limits": {"max_pages": 50, "max_depth": 3},
                "items": [
                    {
                        "id": page_id,
                        "scan_id": "scan_owner",
                        "url": "https://example.com/",
                        "normalized_url": "https://example.com/",
                        "crawl_status": "crawled",
                        "title": "Owner",
                    }
                ],
            }
        },
    )
    other = ScanRecord(
        id="scan_other",
        url="https://example.com",
        normalized_url="https://example.com/",
        status="completed",
        progress=100,
        current_step="Analysis complete",
        created_at=datetime.now(timezone.utc),
        result={"pages": {"items": [], "summary": {"discovered": 0, "crawled": 0, "failed": 0, "skipped": 0, "max_pages": 50, "max_depth": 3}, "limits": {"max_pages": 50, "max_depth": 3}}},
    )
    scans_api.service._store.create(owner)
    scans_api.service._store.create(other)
    stolen = client.get(f"/api/scans/scan_other/pages/{page_id}")
    assert stolen.status_code == 404
    assert stolen.json()["error"]["code"] == "PAGE_NOT_FOUND"
    owned = client.get(f"/api/scans/scan_owner/pages/{page_id}")
    assert owned.status_code == 200
    assert owned.json()["page"]["id"] == page_id
    stolen_arch = client.get(f"/api/scans/scan_other/architecture/pages/{page_id}")
    assert stolen_arch.status_code == 404
    owned_arch = client.get(f"/api/scans/scan_owner/architecture/pages/{page_id}")
    assert owned_arch.status_code == 200
    assert owned_arch.json()["page"]["id"] == page_id


def test_pages_failed_scan(client: TestClient) -> None:
    from datetime import datetime, timezone

    from backend.api import scans as scans_api
    from backend.schemas.scan import ScanRecord

    failed = ScanRecord(
        id="scan_failedpages",
        url="https://example.com",
        normalized_url="https://example.com/",
        status="failed",
        progress=30,
        current_step="Fetching homepage",
        created_at=datetime.now(timezone.utc),
        error={"code": "TIMEOUT", "message": "Connection timed out."},
    )
    scans_api.service._store.create(failed)
    response = client.get("/api/scans/scan_failedpages/pages")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SCAN_FAILED"
    assert "traceback" not in response.json()["error"]["message"].lower()


class _FailingA11yAnalyzer:
    async def analyze(self, **kwargs):
        raise ScanError("A11Y_FAILED", "Accessibility analysis could not be completed.")


def test_accessibility_failure_preserves_other_results(client: TestClient) -> None:
    scans_api.service._a11y = _FailingA11yAnalyzer()
    created = client.post("/api/scans", json={"url": "https://example.com"})
    scan_id = created.json()["scan_id"]
    payload = client.get(f"/api/scans/{scan_id}").json()
    assert payload["status"] == "completed"
    assert payload["result"]["seo"]["score"] is not None
    assert payload["result"]["aeo"]["score"] is not None
    assert payload["result"]["uiux"]["score"] is not None
    assert payload["result"]["accessibility"] is None
    assert payload["result"]["accessibility_error"]["code"] == "A11Y_FAILED"
    assert payload["result"]["performance"]["score"] is not None
    assert payload["result"]["content"]["score"] is not None
    health = client.get(f"/api/scans/{scan_id}/score")
    assert health.status_code == 200
    health_body = health.json()
    a11y_cat = next(item for item in health_body["categories"] if item["category"] == "accessibility")
    assert a11y_cat["available"] is False
    assert a11y_cat["status"] == "failed"
    assert a11y_cat["score"] is None
    assert health_body["overall"]["score"] is not None
    assert health_body["coverage"]["coverage_percent"] < 100
    a11y = client.get(f"/api/scans/{scan_id}/accessibility")
    assert a11y.status_code == 404
    body = a11y.json()
    assert body["error"]["code"] == "A11Y_FAILED"
    assert "traceback" not in body["error"]["message"].lower()
    assert "\\" not in body["error"]["message"]


class _FailingPerfAnalyzer:
    async def analyze(self, **kwargs):
        raise ScanError("PERF_FAILED", "Performance analysis could not be completed.")


def test_performance_failure_preserves_other_results(client: TestClient) -> None:
    scans_api.service._perf = _FailingPerfAnalyzer()
    created = client.post("/api/scans", json={"url": "https://example.com"})
    scan_id = created.json()["scan_id"]
    payload = client.get(f"/api/scans/{scan_id}").json()
    assert payload["status"] == "completed"
    assert payload["result"]["seo"]["score"] is not None
    assert payload["result"]["aeo"]["score"] is not None
    assert payload["result"]["uiux"]["score"] is not None
    assert payload["result"]["accessibility"]["score"] is not None
    assert payload["result"]["performance"] is None
    assert payload["result"]["performance_error"]["code"] == "PERF_FAILED"
    assert payload["result"]["content"]["score"] is not None
    perf = client.get(f"/api/scans/{scan_id}/performance")
    assert perf.status_code == 404
    body = perf.json()
    assert body["error"]["code"] == "PERF_FAILED"
    assert "traceback" not in body["error"]["message"].lower()
    issues = client.get(f"/api/scans/{scan_id}/issues")
    assert issues.status_code == 200
    issues_body = issues.json()
    assert issues_body["analyzer_status"]["performance"] == "failed"
    assert issues_body["analyzer_status"]["seo"] == "completed"
    assert all(item["source"] != "performance" for item in issues_body["items"])
    recs = client.get(f"/api/scans/{scan_id}/recommendations")
    assert recs.status_code == 200
    assert recs.json()["analyzer_status"]["performance"] == "failed"
    assert all(item["category"] != "Performance" for item in recs.json()["items"])
    health = client.get(f"/api/scans/{scan_id}/score")
    assert health.status_code == 200
    health_body = health.json()
    perf_cat = next(item for item in health_body["categories"] if item["category"] == "performance")
    assert perf_cat["available"] is False
    assert perf_cat["status"] == "failed"
    assert perf_cat["score"] is None
    assert health_body["overall"]["score"] is not None
    assert health_body["coverage"]["status"] in {"partial", "limited"}


class _FailingContentAnalyzer:
    def __call__(self, ctx):
        raise ScanError("CONTENT_FAILED", "Content analysis could not be completed.")


def test_content_failure_preserves_other_results(client: TestClient) -> None:
    scans_api.service._content = _FailingContentAnalyzer()
    created = client.post("/api/scans", json={"url": "https://example.com"})
    scan_id = created.json()["scan_id"]
    payload = client.get(f"/api/scans/{scan_id}").json()
    assert payload["status"] == "completed"
    assert payload["result"]["seo"]["score"] is not None
    assert payload["result"]["aeo"]["score"] is not None
    assert payload["result"]["uiux"]["score"] is not None
    assert payload["result"]["accessibility"]["score"] is not None
    assert payload["result"]["performance"]["score"] is not None
    assert payload["result"]["content"] is None
    assert payload["result"]["content_error"]["code"] == "CONTENT_FAILED"
    content = client.get(f"/api/scans/{scan_id}/content")
    assert content.status_code == 404
    body = content.json()
    assert body["error"]["code"] == "CONTENT_FAILED"
    assert "traceback" not in body["error"]["message"].lower()


class _FailingMobileAnalyzer:
    async def analyze(self, **kwargs):
        raise ScanError("MOBILE_FAILED", "Mobile analysis could not be completed.")


def test_mobile_failure_preserves_other_results(client: TestClient) -> None:
    scans_api.service._mobile = _FailingMobileAnalyzer()
    created = client.post("/api/scans", json={"url": "https://example.com"})
    scan_id = created.json()["scan_id"]
    payload = client.get(f"/api/scans/{scan_id}").json()
    assert payload["status"] == "completed"
    assert payload["result"]["seo"]["score"] is not None
    assert payload["result"]["aeo"]["score"] is not None
    assert payload["result"]["uiux"]["score"] is not None
    assert payload["result"]["accessibility"]["score"] is not None
    assert payload["result"]["performance"]["score"] is not None
    assert payload["result"]["content"]["score"] is not None
    assert payload["result"]["structured_data"]["score"] is not None
    assert payload["result"]["mobile"] is None
    assert payload["result"]["mobile_error"]["code"] == "MOBILE_FAILED"
    mobile = client.get(f"/api/scans/{scan_id}/mobile")
    assert mobile.status_code == 404
    body = mobile.json()
    assert body["error"]["code"] == "MOBILE_FAILED"
    assert "traceback" not in body["error"]["message"].lower()
    assert "\\" not in body["error"]["message"]


def test_recommendations_scan_isolation(client: TestClient) -> None:
    from datetime import datetime, timezone

    from backend.api import scans as scans_api
    from backend.schemas.scan import ScanRecord

    rec = {
        "id": "rec_owner_only",
        "scan_id": "scan_rec_owner",
        "recommendation_key": "seo.fix_missing_title",
        "grouping_key": "seo.fix_missing_title|site",
        "title": "Add unique page titles",
        "summary": "Add titles.",
        "category": "SEO",
        "priority": "high",
        "impact": "high",
        "effort": "small",
        "status": "open",
        "affected_page_count": 1,
        "issue_count": 1,
        "issue_ids": ["issue_1"],
        "issue_keys": ["seo.title.missing"],
        "page_ids": [],
        "page_urls": ["https://example.com/"],
        "rationale": "Titles identify pages.",
        "action_steps": ["Add a title element."],
        "evidence": {"issue_ids": ["issue_1"]},
    }
    owner = ScanRecord(
        id="scan_rec_owner",
        url="https://example.com",
        normalized_url="https://example.com/",
        status="completed",
        progress=100,
        current_step="Analysis complete",
        created_at=datetime.now(timezone.utc),
        result={
            "recommendations": {
                "version": 1,
                "summary": {"total": 1, "open": 1, "high_priority": 1},
                "recommendations": [rec],
                "user_status": {},
                "analyzer_status": {"seo": "completed"},
                "methodology": "deterministic",
            }
        },
    )
    other = ScanRecord(
        id="scan_rec_other",
        url="https://example.com",
        normalized_url="https://example.com/",
        status="completed",
        progress=100,
        current_step="Analysis complete",
        created_at=datetime.now(timezone.utc),
        result={
            "recommendations": {
                "version": 1,
                "recommendations": [],
                "summary": {"total": 0},
                "user_status": {},
                "analyzer_status": {},
            }
        },
    )
    scans_api.service._store.create(owner)
    scans_api.service._store.create(other)
    stolen = client.get("/api/scans/scan_rec_other/recommendations/rec_owner_only")
    assert stolen.status_code == 404
    assert stolen.json()["error"]["code"] == "RECOMMENDATION_NOT_FOUND"
    owned = client.get("/api/scans/scan_rec_owner/recommendations/rec_owner_only")
    assert owned.status_code == 200
    assert owned.json()["recommendation"]["id"] == "rec_owner_only"
    stolen_patch = client.patch(
        "/api/scans/scan_rec_other/recommendations/rec_owner_only",
        json={"status": "completed"},
    )
    assert stolen_patch.status_code == 404


def test_issues_include_screenshot_capture_and_skip_missing_images(client: TestClient) -> None:
    created = client.post("/api/scans", json={"url": "https://example.com"})
    assert created.status_code == 202
    scan_id = created.json()["scan_id"]
    issues = client.get(f"/api/scans/{scan_id}/issues")
    assert issues.status_code == 200
    body = issues.json()
    assert "screenshot_capture" in body
    assert body["screenshot_capture"]["status"] in {"pending", "running", "completed", "skipped"}
    for item in body["items"]:
        assert item.get("screenshot_url") in {None, ""} or str(item["screenshot_url"]).startswith("/api/")
        if item.get("screenshot_url"):
            shot = client.get(item["screenshot_url"])
            assert shot.status_code == 200
            assert shot.headers["content-type"] in {"image/webp", "image/png"}
    missing = client.get(f"/api/scans/{scan_id}/issues/not-a-real-issue/screenshot")
    assert missing.status_code == 404
    report = client.get(f"/api/scans/{scan_id}/report")
    assert report.status_code == 200
    assert "screenshot_capture" in report.json()["issues"]


def test_issue_capture_exception_does_not_fail_scan(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("capture exploded")

    monkeypatch.setattr("backend.issues.capture.IssueCaptureEngine.attach", boom)
    created = client.post("/api/scans", json={"url": "https://example.com"})
    assert created.status_code == 202
    scan_id = created.json()["scan_id"]
    status = client.get(f"/api/scans/{scan_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"
    issues = client.get(f"/api/scans/{scan_id}/issues")
    assert issues.status_code == 200
    assert isinstance(issues.json()["items"], list)

