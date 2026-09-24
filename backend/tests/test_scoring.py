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
from backend.schemas.scan import ScanRecord
from backend.scoring.coverage import build_coverage
from backend.scoring.engine import calculate_health
from backend.scoring.methodology import band_for
from backend.scoring.normalization import InvalidScoreError, infer_source_scale, normalize_score
from backend.scoring.repository import attach_health
from backend.scoring.weights import (
    CALCULATION_VERSION,
    CATEGORY_WEIGHTS,
    WeightConfigurationError,
    validate_weights,
)
from backend.services.scan_service import ScanService
from backend.services.url_validator import UrlValidator
from backend.services.website_fetcher import WebsiteFetcher
from backend.store.scans import InMemoryScanStore
from backend.store.screenshots import InMemoryScreenshotStore

KEYS = tuple(CATEGORY_WEIGHTS.keys())


def _all_scores(**overrides: object) -> dict:
    result = {key: {"score": 80} for key in KEYS}
    result.update(overrides)
    return result


def _by_category(health, category: str):
    return next(item for item in health.categories if item.category == category)


def test_default_weights_total_100() -> None:
    assert abs(sum(CATEGORY_WEIGHTS.values()) - 100) < 1e-9
    assert CATEGORY_WEIGHTS["seo"] == 15
    assert CATEGORY_WEIGHTS["aeo"] == 10
    assert CATEGORY_WEIGHTS["uiux"] == 10
    assert CATEGORY_WEIGHTS["accessibility"] == 10
    assert CATEGORY_WEIGHTS["performance"] == 15
    assert CATEGORY_WEIGHTS["content"] == 10
    assert CATEGORY_WEIGHTS["structured_data"] == 5
    assert CATEGORY_WEIGHTS["mobile"] == 10
    assert CATEGORY_WEIGHTS["cro"] == 7.5
    assert CATEGORY_WEIGHTS["trust"] == 7.5
    assert validate_weights() == CATEGORY_WEIGHTS
    assert CALCULATION_VERSION == "1.0"


def test_invalid_weight_configuration() -> None:
    with pytest.raises(WeightConfigurationError, match="total 100"):
        validate_weights({"seo": 50})
    with pytest.raises(WeightConfigurationError, match="non-negative"):
        validate_weights({**CATEGORY_WEIGHTS, "seo": -1})
    with pytest.raises(WeightConfigurationError, match="empty"):
        validate_weights({})


def test_score_normalization() -> None:
    assert normalize_score(82)["score"] == 82
    assert normalize_score(0.8, 1)["score"] == 80
    assert normalize_score(8, 10)["score"] == 80
    assert normalize_score(0)["score"] == 0
    assert normalize_score(100)["score"] == 100
    assert normalize_score(None) == {"score": None, "available": False, "raw": None}
    assert infer_source_scale({"score": 0.8, "score_scale": 1}) == 1
    with pytest.raises(InvalidScoreError):
        normalize_score(101)
    with pytest.raises(InvalidScoreError):
        normalize_score(-1)
    with pytest.raises(InvalidScoreError):
        normalize_score("not-a-score")


def test_all_categories_available() -> None:
    health = calculate_health(_all_scores(), calculated_at="2026-01-01T00:00:00+00:00")
    assert health.overall.score == 80
    assert health.overall.status == "Good"
    assert health.coverage.status == "complete"
    assert health.coverage.coverage_percent == 100
    assert health.coverage.available_weight == 100
    assert health.overall.available_categories == 10
    assert health.architecture.included_in_score is False
    assert health.calculation_version == "1.0"
    seo = _by_category(health, "seo")
    assert seo.weighted_contribution == 12
    assert seo.weight == 15
    assert seo.status == "available"


def test_one_category_unavailable_is_not_zero() -> None:
    health = calculate_health(_all_scores(performance=None))
    perf = _by_category(health, "performance")
    assert perf.available is False
    assert perf.score is None
    assert perf.status == "unavailable"
    assert health.coverage.available_weight == 85
    assert health.coverage.coverage_percent == 85
    assert health.coverage.status == "partial"
    assert health.overall.score == 80
    assert health.partial_notice


def test_multiple_categories_unavailable_renormalizes() -> None:
    result = {
        "seo": {"score": 80},
        "performance": {"score": 60},
    }
    health = calculate_health(result)
    seo = _by_category(health, "seo")
    perf = _by_category(health, "performance")
    assert seo.score == 80
    assert perf.score == 60
    assert 80 * 15 / 100 == 12
    assert 60 * 15 / 100 == 9
    assert health.coverage.available_weight == 30
    assert seo.weighted_contribution == 40
    assert perf.weighted_contribution == 30
    assert health.overall.score == 70
    assert health.coverage.coverage_percent == 30
    assert health.coverage.status == "unavailable"
    assert _by_category(health, "aeo").score is None
    assert _by_category(health, "aeo").available is False


def test_zero_and_perfect_scores_are_valid() -> None:
    zero = calculate_health(_all_scores(**{key: {"score": 0} for key in KEYS}))
    assert zero.overall.score == 0
    assert zero.overall.band == "Critical"
    perfect = calculate_health(_all_scores(**{key: {"score": 100} for key in KEYS}))
    assert perfect.overall.score == 100
    assert perfect.overall.band == "Excellent"


def test_null_score_is_unavailable_not_zero() -> None:
    health = calculate_health(_all_scores(cro={"score": None}, trust={"score": None}))
    assert _by_category(health, "cro").available is False
    assert _by_category(health, "cro").score is None
    assert _by_category(health, "trust").score is None
    assert health.overall.score == 80
    assert health.coverage.available_weight == 85


def test_invalid_analyzer_score_is_failed() -> None:
    health = calculate_health(_all_scores(seo={"score": 150}))
    seo = _by_category(health, "seo")
    assert seo.status == "failed"
    assert seo.available is False
    assert seo.score is None
    assert health.overall.score == 80
    assert health.coverage.available_weight == 85


def test_failed_analyzer_reason_is_exposed() -> None:
    health = calculate_health(
        _all_scores(
            performance=None,
            performance_error={"code": "PERF_FAILED", "message": "Browser measurement failed."},
        )
    )
    perf = _by_category(health, "performance")
    assert perf.status == "failed"
    assert perf.reason == "Browser measurement failed."
    assert health.coverage.status == "partial"


def test_partial_scan_marks_available_categories() -> None:
    health = calculate_health(
        {
            **_all_scores(),
            "pages": {"summary": {"crawled": 12, "failed": 2, "page_limit_reached": True}},
        }
    )
    assert all(item.status == "partial" for item in health.categories if item.available)
    assert health.page_summary.pages_analyzed == 12


def test_issue_counts_do_not_change_scores() -> None:
    baseline = calculate_health(_all_scores(seo={"score": 80}))
    with_issues = calculate_health(
        {
            **_all_scores(seo={"score": 80}),
            "issues": {
                "issues": [
                    {"source": "seo", "severity": "critical"},
                    {"source": "seo", "severity": "high"},
                    {"source": "performance", "severity": "medium"},
                    {"source": "aeo", "severity": "low"},
                    {"source": "content", "severity": "info"},
                ]
            },
        }
    )
    assert with_issues.overall.score == baseline.overall.score
    assert _by_category(with_issues, "seo").score == 80
    assert with_issues.issue_summary.total == 5
    assert with_issues.issue_summary.critical == 1
    assert with_issues.issue_summary.high == 1
    assert with_issues.issue_summary.medium == 1
    assert with_issues.issue_summary.low == 1
    assert with_issues.issue_summary.info == 1
    assert _by_category(with_issues, "seo").issue_summary.critical == 1
    assert _by_category(with_issues, "seo").issue_count == 2


def test_passed_checks_are_not_counted_as_issues() -> None:
    health = calculate_health(
        {
            **_all_scores(),
            "issues": {
                "issues": [
                    {"source": "seo", "severity": "critical", "check_status": "pass"},
                    {"source": "seo", "severity": "high", "check_status": "not_applicable"},
                    {"source": "seo", "severity": "medium", "check_status": "fail"},
                    {"source": "aeo", "severity": "low", "check_status": "warning"},
                ]
            },
        }
    )
    assert health.issue_summary.total == 2
    assert health.issue_summary.medium == 1
    assert health.issue_summary.low == 1
    assert health.issue_summary.critical == 0
    assert _by_category(health, "seo").issue_count == 1


def test_empty_and_large_issue_sets() -> None:
    empty = calculate_health(_all_scores())
    assert empty.issue_summary.total == 0
    huge = calculate_health(
        {
            **_all_scores(),
            "issues": {"issues": [{"source": "seo", "severity": "medium"} for _ in range(500)]},
        }
    )
    assert huge.issue_summary.total == 500
    assert huge.overall.score == empty.overall.score


def test_duplicate_payload_and_malformed_output() -> None:
    health = calculate_health(_all_scores(seo=["not", "an", "object"], uiux={"summary": {"score": 90}}))
    assert _by_category(health, "seo").available is False
    assert _by_category(health, "uiux").score == 90
    nested = calculate_health(_all_scores(aeo={"weighted_score": 70}))
    assert _by_category(nested, "aeo").score == 70


def test_architecture_is_informational() -> None:
    health = calculate_health({**_all_scores(), "architecture": {"summary": {"nodes": 4}}})
    assert all(item.category != "architecture" for item in health.categories)
    assert health.architecture.status == "informational"
    assert health.architecture.included_in_score is False


def test_idempotent_recalculation() -> None:
    result = _all_scores(seo={"score": 82}, performance={"score": 68})
    first = attach_health(result)
    snapshot = result["health"]["overall"]["score"]
    second = attach_health(result)
    assert first.overall.score == second.overall.score == snapshot
    assert first.calculation_version == second.calculation_version == "1.0"
    assert result["health"]["overall"]["score"] == snapshot


def test_score_bands_and_coverage_thresholds() -> None:
    assert band_for(90) == "Excellent"
    assert band_for(82) == "Good"
    assert band_for(60) == "Needs Improvement"
    assert band_for(40) == "Poor"
    assert band_for(0) == "Critical"
    assert band_for(None) is None
    complete = build_coverage(configured_weight=100, available_weight=100, configured_categories=10, available_categories=10)
    assert complete.status == "complete"
    partial = build_coverage(configured_weight=100, available_weight=92.5, configured_categories=10, available_categories=9)
    assert partial.status == "partial"
    assert partial.coverage_percent == 92.5
    limited = build_coverage(configured_weight=100, available_weight=50, configured_categories=10, available_categories=5)
    assert limited.status == "limited"
    unavailable = build_coverage(configured_weight=100, available_weight=30, configured_categories=10, available_categories=2)
    assert unavailable.status == "unavailable"


def test_no_usable_scores_does_not_fabricate_zero() -> None:
    health = calculate_health({})
    assert health.overall.score is None
    assert health.overall.status == "Health score unavailable"
    assert health.coverage.status == "unavailable"
    assert health.coverage.available_weight == 0
    dumped = health.model_dump(mode="json")
    assert "normalized_score" not in dumped["categories"][0]


def test_methodology_copy_has_no_business_predictions() -> None:
    health = calculate_health(_all_scores())
    blob = str(health.model_dump(mode="json")).lower()
    assert "conversion probability" not in blob
    assert "revenue increase" not in blob
    assert "this company is trustworthy" not in blob
    assert "predicted traffic" not in blob
    assert "not a prediction of search rankings" in health.score_note.lower()
    assert "not a statistical confidence interval" in health.coverage_note.lower()


def test_explicit_zero_one_scale_without_guessing_small_percentages() -> None:
    health = calculate_health(_all_scores(seo={"score": 8}))
    assert _by_category(health, "seo").score == 8
    scaled = calculate_health(_all_scores(seo={"score": 0.8, "score_scale": 1}))
    assert _by_category(scaled, "seo").score == 80


def public_dns(_host: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path in {"/robots.txt", "/sitemap.xml", "/llms.txt"}:
        return httpx.Response(404, text="missing")
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


def test_score_api_from_inserted_analyzer_results(client: TestClient) -> None:
    result = _all_scores(seo={"score": 82}, performance={"score": 68})
    attach_health(result)
    record = ScanRecord(
        id="scan_scoreowner",
        url="https://example.com",
        normalized_url="https://example.com/",
        status="completed",
        progress=100,
        current_step="Analysis complete",
        created_at=datetime.now(timezone.utc),
        result=result,
    )
    other_result = _all_scores(**{key: {"score": 10} for key in KEYS})
    attach_health(other_result)
    other = ScanRecord(
        id="scan_scoreother",
        url="https://example.com",
        normalized_url="https://example.com/",
        status="completed",
        progress=100,
        current_step="Analysis complete",
        created_at=datetime.now(timezone.utc),
        result=other_result,
    )
    scans_api.service._store.create(record)
    scans_api.service._store.create(other)

    response = client.get("/api/scans/scan_scoreowner/score")
    assert response.status_code == 200
    body = response.json()
    assert body["scan_id"] == "scan_scoreowner"
    assert body["overall"]["score"] == result["health"]["overall"]["score"]
    assert body["calculation_version"] == "1.0"
    assert {item["category"] for item in body["categories"]} == set(KEYS)
    assert all(item["category"] != "architecture" for item in body["categories"])
    assert body["architecture"]["included_in_score"] is False
    seo = next(item for item in body["categories"] if item["category"] == "seo")
    assert seo["score"] == 82
    assert seo["weight"] == 15
    stolen = client.get("/api/scans/scan_scoreother/score")
    assert stolen.status_code == 200
    assert stolen.json()["overall"]["score"] == 10
    assert stolen.json()["scan_id"] == "scan_scoreother"

    method = client.get("/api/scans/scan_scoreowner/score/methodology")
    assert method.status_code == 200
    assert method.json()["calculation_version"] == "1.0"
    assert abs(sum(method.json()["weights"].values()) - 100) < 1e-6
    assert "renormal" in method.json()["unavailable_behavior"].lower()


def test_score_api_missing_running_failed(client: TestClient) -> None:
    missing = client.get("/api/scans/scan_does_not_exist/score")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "SCAN_NOT_FOUND"

    scans_api.service._store.create(
        ScanRecord(
            id="scan_scorerunning",
            url="https://example.com",
            normalized_url="https://example.com/",
            status="running",
            progress=50,
            current_step="SEO analysis",
            created_at=datetime.now(timezone.utc),
        )
    )
    running = client.get("/api/scans/scan_scorerunning/score")
    assert running.status_code == 409
    assert running.json()["error"]["code"] == "SCAN_NOT_READY"

    scans_api.service._store.create(
        ScanRecord(
            id="scan_scorefailed",
            url="https://example.com",
            normalized_url="https://example.com/",
            status="failed",
            progress=30,
            current_step="Fetching homepage",
            created_at=datetime.now(timezone.utc),
            error={"code": "TIMEOUT", "message": "Connection timed out."},
        )
    )
    failed = client.get("/api/scans/scan_scorefailed/score")
    assert failed.status_code == 409
    assert failed.json()["error"]["code"] == "SCAN_FAILED"


def test_score_api_does_not_use_another_scan_analyzer_payload(client: TestClient) -> None:
    owner = _all_scores(seo={"score": 91})
    attach_health(owner)
    scans_api.service._store.create(
        ScanRecord(
            id="scan_scoreiso_a",
            url="https://example.com",
            normalized_url="https://example.com/",
            status="completed",
            progress=100,
            current_step="Analysis complete",
            created_at=datetime.now(timezone.utc),
            result=owner,
        )
    )
    scans_api.service._store.create(
        ScanRecord(
            id="scan_scoreiso_b",
            url="https://example.com",
            normalized_url="https://example.com/",
            status="completed",
            progress=100,
            current_step="Analysis complete",
            created_at=datetime.now(timezone.utc),
            result={"seo": {"score": 12}},
        )
    )
    isolated = client.get("/api/scans/scan_scoreiso_b/score")
    assert isolated.status_code == 404
    assert isolated.json()["error"]["code"] == "SCORE_NOT_AVAILABLE"
    owned = client.get("/api/scans/scan_scoreiso_a/score")
    assert owned.json()["categories"][0]["score"] == 91 or next(item["score"] for item in owned.json()["categories"] if item["category"] == "seo") == 91
