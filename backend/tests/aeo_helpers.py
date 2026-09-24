from __future__ import annotations

from pathlib import Path

from backend.analyzers.aeo.analyzer import analyze_aeo
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, AeoResult
from backend.parser.html_parser import parse_html

FIXTURES = Path(__file__).parent / "fixtures" / "aeo"

DEFAULT_ROBOTS = {
    "exists": True,
    "status_code": 200,
    "content_type": "text/plain",
    "body": "User-agent: *\nDisallow:",
}
DEFAULT_LLMS = {"exists": False, "status_code": 404, "body": None}


def load_aeo_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def analyze_aeo_html(html: str, **overrides) -> AeoResult:
    ctx = AeoContext(
        page_url=overrides.get("page_url", "https://example.com/"),
        final_url=overrides.get("final_url", overrides.get("page_url", "https://example.com/")),
        status_code=overrides.get("status_code", 200),
        html=parse_html(html),
        robots_txt=overrides.get("robots_txt", DEFAULT_ROBOTS),
        llms_txt=overrides.get("llms_txt", DEFAULT_LLMS),
    )
    return analyze_aeo(ctx)


def aeo_by_id(result: AeoResult, check_id: str) -> CheckResult:
    return next(check for check in result.checks if check.check_id == check_id)
