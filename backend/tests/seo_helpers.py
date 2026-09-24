from __future__ import annotations

from pathlib import Path

from backend.analyzers.seo.analyzer import analyze_seo
from backend.analyzers.seo.context import SeoContext
from backend.analyzers.seo.models import CheckResult, SeoResult
from backend.parser.html_parser import parse_html

FIXTURES = Path(__file__).parent / "fixtures"

DEFAULT_ROBOTS = {
    "exists": True,
    "status_code": 200,
    "content_type": "text/plain",
    "body": "User-agent: *\nDisallow:",
}
DEFAULT_SITEMAP = {
    "exists": True,
    "status_code": 200,
    "content_type": "application/xml",
    "body": '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
}


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def analyze_html(html: str, **overrides) -> SeoResult:
    ctx = SeoContext(
        page_url=overrides.get("page_url", "https://example.com/"),
        final_url=overrides.get("final_url", overrides.get("page_url", "https://example.com/")),
        status_code=overrides.get("status_code", 200),
        html=parse_html(html),
        x_robots_tag=overrides.get("x_robots_tag"),
        robots_txt=overrides.get("robots_txt", DEFAULT_ROBOTS),
        sitemap=overrides.get("sitemap", DEFAULT_SITEMAP),
    )
    return analyze_seo(ctx)


def by_id(result: SeoResult, check_id: str) -> CheckResult:
    return next(check for check in result.checks if check.check_id == check_id)
