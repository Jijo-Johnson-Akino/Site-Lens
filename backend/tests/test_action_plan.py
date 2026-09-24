from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.errors import ScanError
from backend.recommendations.serialize import recommendation_to_list_item
from backend.recommendations.engine import generate
from backend.schemas.scan import ScanRecord
from backend.services.scan_service import ScanService
from backend.services.url_validator import UrlValidator
from backend.store.scans import InMemoryScanStore


def public_dns(_host: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


def _check(check_id: str, *, page_url: str = "https://example.com/", status: str = "fail", severity: str = "high"):
    return {
        "check_id": check_id,
        "name": check_id,
        "status": status,
        "severity": severity,
        "message": f"{check_id} failed",
        "page_url": page_url,
    }


def test_list_item_includes_action_evidence():
    from backend.issues.engine import aggregate

    result = {
        "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
        "url": "https://example.com/",
        "seo": {"checks": [_check("SEO-TITLE-001")]},
    }
    issues = aggregate("scan_action", result, "2026-01-01T00:00:00+00:00")
    result["issues"] = issues.model_dump(mode="json")
    payload = generate("scan_action", result, "2026-01-01T00:00:00+00:00")
    assert payload.recommendations
    row = recommendation_to_list_item(payload.recommendations[0])
    assert row["action_steps"]
    assert "issue_ids" in row
    assert "page_ids" in row
    groups = {}
    for item in payload.recommendations:
        groups.setdefault(item.priority, 0)
        groups[item.priority] += 1
    assert sum(groups.values()) == payload.summary.total


def test_create_respects_concurrency_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.services.scan_service.MAX_CONCURRENT_SCANS", 1)
    store = InMemoryScanStore()
    store.create(
        ScanRecord(
            id="scan_busy",
            url="https://busy.example.com",
            normalized_url="https://busy.example.com/",
            status="running",
            created_at=datetime.now(timezone.utc),
        )
    )
    service = ScanService(store=store, validator=UrlValidator(resolver=public_dns))
    with pytest.raises(ScanError) as exc:
        service.create("https://example.com")
    assert exc.value.code == "SCAN_LIMIT"

