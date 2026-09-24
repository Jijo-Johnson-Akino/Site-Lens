from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.analyzers.accessibility.stub import StubA11yAnalyzer
from backend.analyzers.mobile.stub import StubMobileAnalyzer
from backend.analyzers.performance.stub import StubPerfAnalyzer
from backend.analyzers.trust import analyze_trust
from backend.analyzers.trust.extraction import extract_signals, mask_email, same_site_email
from backend.analyzers.trust.scoring import overall_score
from backend.analyzers.uiux.stub import StubUiuxAnalyzer
from backend.api import scans as scans_api
from backend.errors import ScanError
from backend.issues.engine import aggregate
from backend.issues.keys import issue_key_for
from backend.main import app
from backend.pages.ids import make_link_id, make_page_id
from backend.pages.models import InternalLink, PageRecord, PagesPayload
from backend.recommendations.engine import generate
from backend.recommendations.registry import mapped_issue_keys
from backend.services.scan_service import ScanService
from backend.services.url_identity import normalize_page_url
from backend.services.url_validator import UrlValidator
from backend.services.website_fetcher import WebsiteFetcher
from backend.store.scans import InMemoryScanStore
from backend.store.screenshots import InMemoryScreenshotStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "trust"
FORBIDDEN = (
    "this company is trustworthy",
    "this company is legitimate",
    "this company is safe",
    "this company is fraudulent",
    "gdpr compliant",
    "ccpa compliant",
    "website is secure",
    "ssl certified",
    "legally compliant",
)


def load(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _page(scan_id: str, url: str, html: str, *, page_type: str, is_seed: bool = False) -> PageRecord:
    normalized = normalize_page_url(url)
    signals = extract_signals(html, url)
    return PageRecord(
        id=make_page_id(scan_id, normalized),
        scan_id=scan_id,
        url=url,
        normalized_url=normalized,
        final_url=url,
        crawl_status="crawled",
        page_type=page_type,
        title=signals.get("identity", {}).get("h1") if isinstance(signals.get("identity"), dict) else None,
        h1=signals.get("identity", {}).get("h1") if isinstance(signals.get("identity"), dict) else None,
        trust_signals=signals,
        schema_types=list((signals.get("identity") or {}).get("schema_types") or []),
        is_seed=is_seed,
        http_status=200,
        discovery_method="seed" if is_seed else "internal_link",
    )


def _link(scan_id: str, source: PageRecord, dest: PageRecord, anchor: str = "") -> InternalLink:
    return InternalLink(
        id=make_link_id(scan_id, source.id, dest.id, anchor),
        scan_id=scan_id,
        source_page_id=source.id,
        destination_page_id=dest.id,
        source_url=source.normalized_url,
        destination_url=dest.normalized_url,
        anchor_text=anchor,
    )


def site_pages(scan_id: str = "scan_trust") -> PagesPayload:
    home = _page(scan_id, "https://example.com/", load("home.html"), page_type="homepage", is_seed=True)
    about = _page(scan_id, "https://example.com/about", load("about.html"), page_type="about")
    contact = _page(scan_id, "https://example.com/contact", load("contact.html"), page_type="contact")
    author = _page(scan_id, "https://example.com/blog/author", load("article_author.html"), page_type="article")
    no_author = _page(scan_id, "https://example.com/blog/note", load("article_no_author.html"), page_type="article")
    privacy = _page(scan_id, "https://example.com/privacy", load("privacy.html"), page_type="unknown")
    terms = _page(scan_id, "https://example.com/terms", load("terms.html"), page_type="unknown")
    items = [home, about, contact, author, no_author, privacy, terms]
    links = [
        _link(scan_id, home, about, "About"),
        _link(scan_id, home, contact, "Contact"),
        _link(scan_id, home, author, "Blog"),
        _link(scan_id, home, privacy, "Privacy Policy"),
        _link(scan_id, home, terms, "Terms of Service"),
    ]
    return PagesPayload(items=items, internal_links=links, internal_links_recorded=True)


def analyze(pages: PagesPayload, *, schema: dict | None = None, content: dict | None = None, current_year: int = 2026):
    seed = next(page for page in pages.items if page.is_seed)
    payload: dict = {
        "website": {"url": seed.url, "final_url": seed.url},
        "html": {"title": seed.title, "h1": seed.h1},
    }
    if schema is not None:
        payload["structured_data"] = schema
    if content is not None:
        payload["content"] = content
    return analyze_trust(payload, pages=pages, current_year=current_year)


def by_id(result, check_id: str, page_url: str | None = None):
    matches = [item for item in result.checks if item.check_id == check_id]
    if page_url:
        matches = [item for item in matches if item.page_url.rstrip("/") == page_url.rstrip("/")]
    assert matches, f"expected {check_id} on {page_url or 'any page'}"
    return matches[0]


def claim_blob(result) -> str:
    parts = [result.narrative, result.methodology, result.score_note, result.crawl_note]
    parts.extend(item.message for item in result.checks)
    parts.extend(item.recommendation or "" for item in result.checks)
    return " ".join(parts).lower()


def test_organization_brand_and_schema_reuse():
    signals = extract_signals(load("home.html"), "https://example.com/")
    identity = signals["identity"]
    assert identity["visible_name"]
    assert "Acme" in (identity["og_site_name"] or identity["visible_name"] or "")
    types = set(identity["schema_types"])
    assert "Organization" in types
    assert "WebSite" in types
    result = analyze(site_pages())
    check = by_id(result, "trust.identity.organization.missing")
    assert check.status == "pass"
    assert "organization identity signals detected" in check.message.lower()
    schema = {
        "entities": [
            {"types": ["Organization"], "name": "Acme Technologies", "properties": {"email": "support@example.com"}}
        ]
    }
    reused = analyze(site_pages("scan_schema"), schema=schema)
    assert by_id(reused, "trust.identity.organization.missing").status == "pass"


def test_contact_about_and_policy_detection():
    home = extract_signals(load("home.html"), "https://example.com/")
    assert home["contact"]["emails"]
    assert any("example.com" in email for email in home["contact"]["emails"])
    contact = extract_signals(load("contact.html"), "https://example.com/contact")
    assert contact["contact"]["emails"]
    assert contact["contact"]["phones"]
    assert contact["contact"]["form"] is True
    assert contact["contact"]["has_address"] or contact["business"]["address"]
    about = extract_signals(load("about.html"), "https://example.com/about")
    assert about["business"]["address"]
    result = analyze(site_pages())
    assert by_id(result, "trust.contact.page.missing").status == "pass"
    assert by_id(result, "trust.contact.email.present").status == "pass"
    assert by_id(result, "trust.contact.phone.present").status == "pass"
    assert by_id(result, "trust.contact.address.present").status == "pass"
    assert by_id(result, "trust.contact.form.present").status == "pass"
    assert by_id(result, "trust.about.page.missing").status == "pass"
    assert "within the crawled pages" in by_id(result, "trust.about.page.missing").message.lower() or by_id(result, "trust.about.page.missing").status == "pass"
    assert by_id(result, "trust.policy.privacy.missing").status == "pass"
    assert by_id(result, "trust.policy.terms.missing").status == "pass"
    missing = analyze(PagesPayload(items=[_page("scan_gap", "https://example.com/", load("missing_about.html"), page_type="homepage", is_seed=True)]))
    about_gap = by_id(missing, "trust.about.page.missing")
    assert about_gap.status == "warning"
    assert "no dedicated about page was detected within the crawled pages" in about_gap.message.lower()
    assert "has no about information" not in about_gap.message.lower()
    privacy_gap = by_id(missing, "trust.policy.privacy.missing")
    assert privacy_gap.status == "warning"
    assert "within the crawled pages" in privacy_gap.message.lower()


def test_authorship_and_author_schema_consistency():
    author_signals = extract_signals(load("article_author.html"), "https://example.com/blog/author")
    assert "John Smith" in author_signals["authorship"]["authors"]
    assert author_signals["authorship"]["dates"]
    result = analyze(site_pages())
    authored = by_id(result, "trust.authorship.author.missing", "https://example.com/blog/author")
    assert authored.status == "pass"
    dated = by_id(result, "trust.authorship.date.missing", "https://example.com/blog/author")
    assert dated.status == "pass"
    missing_author = by_id(result, "trust.authorship.author.missing", "https://example.com/blog/note")
    assert missing_author.status == "warning"
    mismatch_page = _page("scan_auth", "https://example.com/blog/mismatch", load("author_mismatch.html"), page_type="article", is_seed=True)
    mismatch = analyze(PagesPayload(items=[mismatch_page]))
    inconsistent = by_id(mismatch, "trust.authorship.inconsistent")
    assert inconsistent.status == "warning"
    assert "potential author information inconsistency" in inconsistent.message.lower()
    assert "fraud" not in inconsistent.message.lower()


def test_social_proof_credentials_business_and_security():
    home = extract_signals(load("home.html"), "https://example.com/")
    assert home["social_proof"]["testimonials"]["detected"] is True
    assert home["social_proof"]["client_logos"]["detected"] is True
    assert home["social_proof"]["case_studies"]["detected"] is True
    assert home["social_proof"]["user_claims"]
    result = analyze(site_pages())
    assert by_id(result, "trust.social_proof.testimonial.detected").status == "pass"
    assert by_id(result, "trust.social_proof.client_logos.detected").status == "pass"
    assert by_id(result, "trust.social_proof.case_study.detected").status == "pass"
    reviews = analyze(PagesPayload(items=[_page("scan_rev", "https://example.com/", load("reviews.html"), page_type="homepage", is_seed=True)]))
    assert by_id(reviews, "trust.social_proof.reviews.detected").status == "pass"
    cert = analyze(PagesPayload(items=[_page("scan_cert", "https://example.com/", load("certification.html"), page_type="homepage", is_seed=True)]))
    assert by_id(cert, "trust.credentials.certification.detected").status == "pass"
    assert "certification badge" in by_id(cert, "trust.credentials.certification.detected").message.lower()
    assert by_id(cert, "trust.credentials.award.detected").status == "pass"
    assert by_id(result, "trust.business.address.detected").status == "pass"
    assert by_id(result, "trust.business.hours.detected").status == "pass"
    assert by_id(result, "trust.business.identifier.detected").status == "pass"
    assert by_id(result, "trust.security.https.enabled").status == "pass"
    assert by_id(result, "trust.security.https.enabled").message.lower() == "https enabled."
    payment = analyze(PagesPayload(items=[_page("scan_pay", "https://example.com/", load("payment.html"), page_type="product", is_seed=True)]))
    assert by_id(payment, "trust.security.payment_method.detected").status == "pass"
    assert by_id(payment, "trust.security.badge.detected").status == "pass"
    http_page = _page("scan_http", "http://example.com/", load("missing_about.html"), page_type="homepage", is_seed=True)
    http_result = analyze(PagesPayload(items=[http_page]))
    https_check = by_id(http_result, "trust.security.https.enabled")
    assert https_check.status == "warning"
    assert "website is secure" not in https_check.message.lower()


def test_social_profiles_entity_consistency_copyright_and_external_email():
    home = extract_signals(load("home.html"), "https://example.com/")
    platforms = {item["platform"] for item in home["social"]["profiles"]}
    assert "LinkedIn" in platforms
    result = analyze(site_pages())
    social = by_id(result, "trust.contact.social.detected")
    assert social.status == "pass"
    assert by_id(result, "trust.consistency.organization_name").status == "pass"
    copyright_check = by_id(result, "trust.transparency.copyright.detected")
    assert copyright_check.status == "pass"
    assert "2026" in (copyright_check.detected or "")
    inconsistent = analyze(PagesPayload(items=[_page("scan_inc", "https://example.com/", load("inconsistent_name.html"), page_type="homepage", is_seed=True)]))
    name_check = by_id(inconsistent, "trust.consistency.organization_name")
    assert name_check.status == "warning"
    assert "potential entity-name inconsistency" in name_check.message.lower()
    external = analyze(PagesPayload(items=[_page("scan_ext", "https://example.com/", load("external_email.html"), page_type="homepage", is_seed=True)]))
    email_check = by_id(external, "trust.contact.email.present")
    assert email_check.status == "pass"
    assert "external domain" in email_check.message.lower()
    assert "suspicious" not in email_check.message.lower()
    assert same_site_email("example.com", "hello@gmail.com") is False
    assert mask_email("support@example.com") == "su***@example.com"
    authored = extract_signals(load("article_author.html"), "https://example.com/blog/author")
    assert authored["transparency"]["citations"] is True or authored["transparency"]["methodology"] is True
    assert by_id(result, "trust.authorship.citation.detected", "https://example.com/blog/author").status == "pass"
    assert by_id(result, "trust.transparency.credibility.detected").status == "pass"
    assert by_id(result, "trust.transparency.footer.detected").status == "pass"
    login_page = _page("scan_login", "https://example.com/login", load("login.html"), page_type="login", is_seed=True)
    login_result = analyze(PagesPayload(items=[login_page]))
    login_check = by_id(login_result, "trust.security.login.messaging")
    assert login_check.status == "pass"
    assert "login or signup" in login_check.message.lower()


def test_scoring_na_handling_and_no_legitimacy_claims():
    first = analyze(site_pages())
    second = analyze(site_pages())
    assert first.score == second.score
    assert first.score is not None
    assert 0 <= first.score <= 100
    blob = claim_blob(first)
    for phrase in FORBIDDEN:
        assert phrase not in blob
    assert "does not verify the truth" in first.methodology.lower()
    article_only = PagesPayload(items=[_page("scan_na", "https://example.com/blog", load("article_no_author.html"), page_type="article", is_seed=True)])
    article_result = analyze(article_only)
    na_checks = [item for item in article_result.checks if item.status == "not_applicable"]
    assert na_checks
    assert overall_score(article_result.checks) == article_result.score
    missing_social = [item for item in article_result.checks if item.check_id == "trust.social_proof.testimonial.detected"][0]
    assert missing_social.status == "not_applicable"


def test_issues_recommendations_and_partial_analyzer():
    missing = analyze(PagesPayload(items=[_page("scan_issues", "https://example.com/", load("missing_about.html"), page_type="homepage", is_seed=True)]))
    result = {
        "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
        "trust": missing.model_dump(mode="json"),
    }
    issues = aggregate("scan_issues", result, "2026-01-01T00:00:00+00:00")
    keys = {item.issue_key for item in issues.issues}
    assert "trust.about.page.missing" in keys
    assert issue_key_for("trust", "trust.identity.organization.missing") == "trust.identity.organization.missing"
    assert "trust.identity.organization.missing" in mapped_issue_keys()
    result["issues"] = issues.model_dump(mode="json")
    recs = generate("scan_issues", result, "2026-01-01T00:00:00+00:00")
    rec_keys = {item.recommendation_key for item in recs.recommendations}
    assert "trust.add_about_page" in rec_keys or "trust.add_privacy_policy_link" in rec_keys
    assert all(item.category == "Trust" for item in recs.recommendations if item.recommendation_key.startswith("trust."))
    a = site_pages("scan_a")
    b = PagesPayload(items=[_page("scan_b", "https://other.example/", load("missing_about.html"), page_type="homepage", is_seed=True)])
    left = analyze(a)
    right = analyze(b)
    assert all("other.example" not in item.page_url for item in left.checks)
    assert all(item.page_url.startswith("https://other.example") for item in right.checks)
    with pytest.raises(ScanError) as exc:
        analyze_trust({}, pages=PagesPayload())
    assert exc.value.code == "TRUST_FAILED"


def public_dns(_host: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


PAGES = {
    "/": load("home.html"),
    "/about": load("about.html"),
    "/contact": load("contact.html"),
    "/blog/author": load("article_author.html"),
    "/blog/note": load("article_no_author.html"),
    "/privacy": load("privacy.html"),
    "/terms": load("terms.html"),
}


def trust_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path in {"/robots.txt", "/sitemap.xml", "/llms.txt"}:
        return httpx.Response(404, text="missing")
    html = PAGES.get(path)
    if html is None:
        return httpx.Response(404, text="missing")
    return httpx.Response(200, text=html, headers={"content-type": "text/html"})


@pytest.fixture
def trust_client() -> TestClient:
    store = InMemoryScanStore()
    shots = InMemoryScreenshotStore()
    validator = UrlValidator(resolver=public_dns)
    fetcher = WebsiteFetcher(
        validator=validator,
        client=httpx.AsyncClient(transport=httpx.MockTransport(trust_handler), follow_redirects=False),
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


def test_trust_api_fixture_scan(trust_client: TestClient) -> None:
    created = trust_client.post("/api/scans", json={"url": "https://example.com"})
    assert created.status_code == 202
    scan_id = created.json()["scan_id"]
    payload = trust_client.get(f"/api/scans/{scan_id}").json()
    assert payload["status"] == "completed"
    trust_payload = payload["result"]["trust"]
    assert trust_payload is not None
    assert isinstance(trust_payload["score"], int)
    assert 0 <= trust_payload["score"] <= 100
    joined = str(trust_payload).lower()
    for phrase in FORBIDDEN:
        assert phrase not in joined
    api = trust_client.get(f"/api/scans/{scan_id}/trust")
    assert api.status_code == 200
    body = api.json()
    assert body["scan_id"] == scan_id
    assert body["score"] == trust_payload["score"]
    assert body["summary"]["pages_analyzed"] >= 1
    assert body["pages"]
    assert body["methodology"]
    assert "does not verify the truth" in body["methodology"]
    ids = {item["check_id"] for item in body["checks"]}
    assert "trust.identity.organization.missing" in ids
    assert "trust.security.https.enabled" in ids
    page_id = body["pages"][0]["page_id"]
    detail = trust_client.get(f"/api/scans/{scan_id}/trust/pages/{page_id}")
    assert detail.status_code == 200
    assert detail.json()["page"]["page_id"] == page_id
    missing = trust_client.get(f"/api/scans/{scan_id}/trust/pages/page_does_not_exist")
    assert missing.status_code == 404
    issues = trust_client.get(f"/api/scans/{scan_id}/issues", params={"category": "Trust"})
    assert issues.status_code == 200
    assert all(item["category"] == "Trust" for item in issues.json()["items"])
    recs = trust_client.get(f"/api/scans/{scan_id}/recommendations", params={"category": "Trust"})
    assert recs.status_code == 200
    pages = trust_client.get(f"/api/scans/{scan_id}/pages")
    assert pages.status_code == 200
    architecture = trust_client.get(f"/api/scans/{scan_id}/architecture")
    assert architecture.status_code == 200
    cro = trust_client.get(f"/api/scans/{scan_id}/cro")
    assert cro.status_code == 200
    other = trust_client.post("/api/scans", json={"url": "https://example.com"})
    other_id = other.json()["scan_id"]
    isolated = trust_client.get(f"/api/scans/{other_id}/trust")
    assert isolated.status_code == 200
    leak = trust_client.get(f"/api/scans/{other_id}/trust/pages/{page_id}")
    assert leak.status_code == 404


def test_trust_failure_preserves_other_results(trust_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args, **_kwargs):
        raise ScanError("TRUST_FAILED", "Trust & Credibility analysis unavailable.")

    monkeypatch.setattr("backend.services.scan_service.analyze_trust", _fail)
    created = trust_client.post("/api/scans", json={"url": "https://example.com"})
    scan_id = created.json()["scan_id"]
    payload = trust_client.get(f"/api/scans/{scan_id}").json()
    assert payload["status"] == "completed"
    assert payload["result"]["seo"]["score"] is not None
    assert payload["result"]["cro"] is not None
    assert payload["result"]["trust"] is None
    assert payload["result"]["trust_error"]["code"] == "TRUST_FAILED"
    trust = trust_client.get(f"/api/scans/{scan_id}/trust")
    assert trust.status_code == 404
    assert trust.json()["error"]["code"] == "TRUST_FAILED"
    issues = trust_client.get(f"/api/scans/{scan_id}/issues")
    assert issues.status_code == 200
    recs = trust_client.get(f"/api/scans/{scan_id}/recommendations")
    assert recs.status_code == 200
    pages = trust_client.get(f"/api/scans/{scan_id}/pages")
    assert pages.status_code == 200
    architecture = trust_client.get(f"/api/scans/{scan_id}/architecture")
    assert architecture.status_code == 200
    cro = trust_client.get(f"/api/scans/{scan_id}/cro")
    assert cro.status_code == 200
