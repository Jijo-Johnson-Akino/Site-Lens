from __future__ import annotations

import httpx
import pytest

from backend.errors import ScanError
from backend.services.url_validator import UrlValidator
from backend.services.website_fetcher import WebsiteFetcher

PUBLIC_HTML = """<!doctype html><html lang="en"><head><title>Ok</title></head><body><h1>Hi</h1></body></html>"""


def public_dns(_host: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


def handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if request.url.host == "127.0.0.1":
        return httpx.Response(200, text="internal")
    if request.url.path == "/redirect-private":
        return httpx.Response(302, headers={"location": "http://127.0.0.1/"})
    if request.url.path == "/redirect":
        return httpx.Response(302, headers={"location": "https://example.com/final"})
    if request.url.path == "/final":
        return httpx.Response(200, text=PUBLIC_HTML, headers={"content-type": "text/html"})
    if request.url.path == "/missing":
        return httpx.Response(404, text="<html><title>Nope</title></html>", headers={"content-type": "text/html"})
    if request.url.path == "/huge":
        return httpx.Response(200, content=b"x" * (11 * 1024 * 1024), headers={"content-type": "text/html"})
    if request.url.path == "/pdf":
        return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})
    if request.url.path == "/slow":
        raise httpx.ReadTimeout("slow")
    return httpx.Response(200, text=PUBLIC_HTML, headers={"content-type": "text/html; charset=utf-8"})


@pytest.fixture
def fetcher() -> WebsiteFetcher:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
        timeout=httpx.Timeout(2.0),
    )
    return WebsiteFetcher(validator=UrlValidator(resolver=public_dns), client=client)


@pytest.mark.asyncio
async def test_fetch_200(fetcher: WebsiteFetcher) -> None:
    result = await fetcher.fetch_homepage("https://example.com/")
    assert result["status_code"] == 200
    assert "Ok" in result["html"]
    assert result["html_size_bytes"] > 0


@pytest.mark.asyncio
async def test_fetch_404_is_still_a_response(fetcher: WebsiteFetcher) -> None:
    result = await fetcher.fetch_homepage("https://example.com/missing")
    assert result["status_code"] == 404


@pytest.mark.asyncio
async def test_follows_safe_redirect(fetcher: WebsiteFetcher) -> None:
    result = await fetcher.fetch_homepage("https://example.com/redirect")
    assert result["status_code"] == 200
    assert result["final_url"].endswith("/final")


@pytest.mark.asyncio
async def test_rejects_redirect_to_private_ip(fetcher: WebsiteFetcher) -> None:
    with pytest.raises(ScanError) as exc:
        await fetcher.fetch_homepage("https://example.com/redirect-private")
    assert exc.value.code == "BLOCKED_URL"


@pytest.mark.asyncio
async def test_timeout(fetcher: WebsiteFetcher) -> None:
    with pytest.raises(ScanError) as exc:
        await fetcher.fetch_homepage("https://example.com/slow")
    assert exc.value.code == "TIMEOUT"


@pytest.mark.asyncio
async def test_rejects_large_body(fetcher: WebsiteFetcher) -> None:
    with pytest.raises(ScanError) as exc:
        await fetcher.fetch_homepage("https://example.com/huge")
    assert exc.value.code == "RESPONSE_TOO_LARGE"


@pytest.mark.asyncio
async def test_rejects_pdf(fetcher: WebsiteFetcher) -> None:
    with pytest.raises(ScanError) as exc:
        await fetcher.fetch_homepage("https://example.com/pdf")
    assert exc.value.code == "UNSUPPORTED_CONTENT"


@pytest.mark.asyncio
async def test_fetch_document_rejects_off_host_redirect(fetcher: WebsiteFetcher) -> None:
    async def extra(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/leave":
            return httpx.Response(302, headers={"location": "https://other.example/"})
        return handler(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(extra), follow_redirects=False)
    local = WebsiteFetcher(validator=UrlValidator(resolver=public_dns), client=client)
    with pytest.raises(ScanError) as exc:
        await local.fetch_document("https://example.com/leave", allowed_host="example.com")
    assert exc.value.code == "EXTERNAL_REDIRECT"
