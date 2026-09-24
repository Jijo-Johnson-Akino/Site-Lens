from __future__ import annotations

from backend.issues.engine import aggregate
from backend.issues.keys import issue_key_for
from backend.recommendations.engine import grouping_key, generate, payload_from_result
from backend.recommendations.query import parse_page_size, query_recommendations
from backend.recommendations.registry import all_rules, mapped_issue_keys, rules_for_issue_key
from backend.recommendations.scoring import calculate_effort, calculate_impact, calculate_priority, highest_priority


def _check(check_id: str, *, page_url: str = "https://example.com/", status: str = "fail", severity: str = "high", **extra):
    data = {
        "check_id": check_id,
        "name": check_id,
        "status": status,
        "severity": severity,
        "message": f"{check_id} failed",
        "page_url": page_url,
    }
    data.update(extra)
    return data


def _result_with_issues(**analyzers):
    body = {
        "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
        "url": "https://example.com/",
    }
    body.update(analyzers)
    issues = aggregate("scan_rec", body, "2026-01-01T00:00:00+00:00")
    body["issues"] = issues.model_dump(mode="json")
    return body


def test_rule_registration_and_issue_mapping():
    keys = {rule.recommendation_key for rule in all_rules()}
    assert "seo.fix_missing_title" in keys
    assert "performance.optimize_images" in keys
    assert "accessibility.add_form_labels" in keys
    assert "cro.improve_primary_cta_visibility" in keys
    mapped = mapped_issue_keys()
    assert "seo.title.missing" in mapped
    assert "seo.meta_description.missing" in mapped
    assert "performance.image.large" in mapped
    assert "accessibility.form.label.missing" in mapped
    assert "mobile.touch_target.small" in mapped
    assert "structured_data.invalid_jsonld" in mapped
    assert "cro.cta.primary.not_visible" in mapped
    assert issue_key_for("seo", "SEO-TITLE-001") == "seo.title.missing"
    recs = rules_for_issue_key("seo.title.missing")
    assert recs[0].recommendation_key == "seo.fix_missing_title"


def test_priority_impact_effort_are_deterministic():
    assert highest_priority(["medium", "high", "low"]) == "high"
    assert calculate_priority([], fallback="info") == "info"
    assert calculate_effort("small") == "small"
    assert calculate_impact(base="low", priority="critical", page_count=1, element_count=0) == "high"
    assert calculate_impact(base="low", priority="low", page_count=6, element_count=0) == "high"
    assert calculate_impact(base="medium", priority="medium", page_count=1, element_count=0) == "medium"


def test_fixture_consolidates_missing_titles_and_maps_expected_keys():
    pages = [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/contact",
    ]
    result = _result_with_issues(
        seo={
            "checks": [
                _check("SEO-TITLE-001", page_url=url, severity="critical")
                for url in pages
            ]
            + [_check("SEO-META-001", page_url="https://example.com/about")]
        },
        performance={"checks": [_check("PERF-IMG-001", status="warning", resource_url="/images/hero.jpg")]},
        accessibility={"checks": [_check("A11Y-FORM-001", selector="input#email")]},
        mobile={"checks": [_check("MOBILE-TOUCH-001", selector="button.icon")]},
        structured_data={"checks": [_check("SCHEMA-SYNTAX-001")]},
    )
    payload = generate("scan_rec", result, "2026-01-01T00:00:00+00:00")
    by_key = {item.recommendation_key: item for item in payload.recommendations}
    title = by_key["seo.fix_missing_title"]
    assert title.affected_page_count == 3
    assert title.issue_count == 3
    assert len(title.issue_ids) == 1
    assert title.issue_keys == ["seo.title.missing"]
    assert title.status == "open"
    assert title.priority in {"critical", "high"}
    assert "seo.add_meta_description" in by_key
    assert "performance.optimize_images" in by_key
    assert "accessibility.add_form_labels" in by_key
    assert "mobile.increase_touch_target_size" in by_key
    assert "structured_data.fix_invalid_jsonld" in by_key
    assert payload.summary.total == len(payload.recommendations)
    assert all(item.evidence for item in payload.recommendations if item.source_kind == "issues")


def test_generation_is_idempotent_and_preserves_status():
    result = _result_with_issues(seo={"checks": [_check("SEO-TITLE-001"), _check("SEO-TITLE-001", page_url="https://example.com/a")]})
    first = generate("scan_dup", result, "2026-01-01T00:00:00+00:00")
    title = next(item for item in first.recommendations if item.recommendation_key == "seo.fix_missing_title")
    first.user_status[title.grouping_key] = "completed"
    title.status = "completed"
    result["recommendations"] = first.model_dump(mode="json")
    second = generate("scan_dup", result, "2026-01-02T00:00:00+00:00")
    titles = [item for item in second.recommendations if item.recommendation_key == "seo.fix_missing_title"]
    assert len(titles) == 1
    assert titles[0].id == title.id
    assert titles[0].status == "completed"
    assert titles[0].grouping_key == grouping_key("seo.fix_missing_title")


def test_disappearing_issue_removes_active_recommendation():
    result = _result_with_issues(seo={"checks": [_check("SEO-TITLE-001"), _check("SEO-META-001")]})
    first = generate("scan_gone", result, "2026-01-01T00:00:00+00:00")
    assert {item.recommendation_key for item in first.recommendations} >= {"seo.fix_missing_title", "seo.add_meta_description"}
    result["seo"] = {"checks": [_check("SEO-META-001")]}
    result["issues"] = aggregate("scan_gone", result, "2026-01-01T00:00:00+00:00").model_dump(mode="json")
    result["recommendations"] = first.model_dump(mode="json")
    second = generate("scan_gone", result, "2026-01-01T00:00:00+00:00")
    keys = {item.recommendation_key for item in second.recommendations}
    assert "seo.fix_missing_title" not in keys
    assert "seo.add_meta_description" in keys


def test_partial_analyzer_does_not_invent_recommendations():
    result = _result_with_issues(
        seo={"checks": [_check("SEO-TITLE-001")]},
        performance_error={"code": "PERF_FAILED", "message": "failed"},
    )
    payload = generate("scan_partial", result, "2026-01-01T00:00:00+00:00")
    keys = {item.recommendation_key for item in payload.recommendations}
    assert "seo.fix_missing_title" in keys
    assert not any(item.category == "Performance" for item in payload.recommendations)
    assert payload.analyzer_status["performance"] == "failed"
    assert payload.analyzer_status["seo"] == "completed"


def test_pass_findings_do_not_create_recommendations():
    result = _result_with_issues(seo={"checks": [_check("SEO-TITLE-001", status="pass")]})
    payload = generate("scan_pass", result, "2026-01-01T00:00:00+00:00")
    assert "seo.fix_missing_title" not in {item.recommendation_key for item in payload.recommendations}


def test_architecture_orphans_create_recommendation_with_evidence():
    result = {
        "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
        "pages": {
            "version": 1,
            "internal_links_recorded": True,
            "internal_links": [],
            "summary": {"discovered": 2, "crawled": 2, "failed": 0, "skipped": 0, "max_pages": 50, "max_depth": 3},
            "limits": {"max_pages": 50, "max_depth": 3},
            "items": [
                {
                    "id": "page_seed",
                    "scan_id": "scan_arch",
                    "url": "https://example.com/",
                    "normalized_url": "https://example.com/",
                    "crawl_status": "crawled",
                    "is_seed": True,
                    "depth": 0,
                    "title": "Home",
                },
                {
                    "id": "page_orphan",
                    "scan_id": "scan_arch",
                    "url": "https://example.com/hidden",
                    "normalized_url": "https://example.com/hidden",
                    "crawl_status": "crawled",
                    "is_seed": False,
                    "depth": 1,
                    "title": "Hidden",
                },
            ],
        },
        "issues": {"version": 1, "issues": [], "summary": {}, "analyzer_status": {}, "groups": {}},
    }
    payload = generate("scan_arch", result, "2026-01-01T00:00:00+00:00")
    rec = next(item for item in payload.recommendations if item.recommendation_key == "architecture.improve_internal_linking")
    assert rec.affected_page_count == 1
    assert rec.page_ids == ["page_orphan"]
    assert rec.evidence["page_urls"]
    assert rec.source_kind == "architecture"


def test_query_pagination_filter_search_sort():
    result = _result_with_issues(
        seo={"checks": [_check("SEO-TITLE-001"), _check("SEO-META-001")]},
        performance={"checks": [_check("PERF-IMG-001", status="warning")]},
    )
    payload = generate("scan_query", result, "2026-01-01T00:00:00+00:00")
    assert parse_page_size("1000") == 100
    seo_only, meta = query_recommendations(payload.recommendations, {"category": "SEO"})
    assert meta["page_size"] == 25
    assert all(item.category == "SEO" for item in seo_only)
    searched, _ = query_recommendations(payload.recommendations, {"search": "title"})
    assert searched and all("title" in item.title.lower() or "title" in item.summary.lower() for item in searched)
    by_status, _ = query_recommendations(payload.recommendations, {"sort": "status", "order": "desc"})
    assert [item.status for item in by_status]
    paged, page_meta = query_recommendations(payload.recommendations, {"page": 1, "page_size": 1, "sort": "priority", "order": "desc"})
    assert len(paged) == 1
    assert page_meta["page_size"] == 1
    assert page_meta["total"] == len(payload.recommendations)


def test_payload_from_result_round_trip():
    result = _result_with_issues(seo={"checks": [_check("SEO-TITLE-001")]})
    generated = generate("scan_store", result, "2026-01-01T00:00:00+00:00")
    result["recommendations"] = generated.model_dump(mode="json")
    loaded = payload_from_result("scan_store", result, "2026-01-01T00:00:00+00:00")
    assert [item.id for item in loaded.recommendations] == [item.id for item in generated.recommendations]


def test_schema_property_depends_on_invalid_jsonld():
    result = _result_with_issues(
        structured_data={
            "checks": [
                _check("SCHEMA-SYNTAX-001"),
                _check("SCHEMA-CORE-001", status="warning", severity="medium"),
            ]
        }
    )
    payload = generate("scan_dep", result, "2026-01-01T00:00:00+00:00")
    by_key = {item.recommendation_key: item for item in payload.recommendations}
    complete = by_key["structured_data.complete_schema_properties"]
    invalid = by_key["structured_data.fix_invalid_jsonld"]
    assert invalid.id in complete.depends_on_recommendation_ids
