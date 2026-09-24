"""Homepage fetch with redirect re-validation, timeouts, and size limits."""

from __future__ import annotations

import logging
import time
from urllib.parse import urljoin

import httpx

from backend import config
from backend.errors import ScanError
from backend.services.url_identity import hostname_of
from backend.services.url_validator import UrlValidator, safe_display_url

logger = logging.getLogger("sitebench.fetcher")

HTML_TYPES = ("text/html", "application/xhtml+xml", "text/plain")


def _content_type(value: str | None) -> str:
    if not value:
        return "application/octet-stream"
    return value.split(";", 1)[0].strip().lower()


def _charset(content_type: str | None) -> str:
    if not content_type:
        return "utf-8"
    parts = [part.strip() for part in content_type.split(";")]
    for part in parts[1:]:
        if part.lower().startswith("charset="):
            return part.split("=", 1)[1].strip().strip('"') or "utf-8"
    return "utf-8"


def _decode(body: bytes, content_type: str | None) -> str:
    return body.decode(_charset(content_type), errors="replace")


class WebsiteFetcher:
    def __init__(self, validator: UrlValidator | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._validator = validator or UrlValidator()
        self._client = client

    async def _request(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        self._validator.validate(url)
        logger.info("connection_attempt host=%s", safe_display_url(url))
        try:
            request = client.build_request("GET", url)
            response = await client.send(request, stream=True, follow_redirects=False)
        except httpx.TimeoutException as exc:
            raise ScanError("TIMEOUT", "Connection timed out.") from exc
        except httpx.ConnectError as exc:
            raise ScanError("WEBSITE_UNREACHABLE", "The website could not be reached.") from exc
        except httpx.HTTPError as exc:
            message = str(exc).lower()
            if "ssl" in message or "certificate" in message or "tls" in message:
                raise ScanError("TLS_ERROR", "The website could not be reached.") from exc
            raise ScanError("WEBSITE_UNREACHABLE", "The website could not be reached.") from exc
        return response

    async def _read_limited(self, response: httpx.Response) -> bytes:
        chunks = bytearray()
        try:
            async for chunk in response.aiter_bytes():
                if len(chunks) + len(chunk) > config.MAX_RESPONSE_SIZE:
                    raise ScanError("RESPONSE_TOO_LARGE", "Response exceeds allowed size.")
                chunks.extend(chunk)
        finally:
            await response.aclose()
        return bytes(chunks)

    async def fetch_probe(self, url: str) -> dict:
        """Small GET used for robots.txt / sitemap existence. Never throws for HTTP errors."""
        try:
            safe_url = self._validator.validate(url)
        except ScanError:
            return {"exists": False, "status_code": None}
        client = self._client
        owns_client = client is None
        if client is None:
            client = self._build_client()
        try:
            response = await client.get(safe_url, follow_redirects=False)
            exists = response.status_code == 200
            content_type = response.headers.get("content-type")
            body = None
            if exists:
                body = response.text[:65536]
            return {
                "exists": exists,
                "status_code": response.status_code,
                "content_type": content_type,
                "body": body,
            }
        except httpx.HTTPError:
            return {"exists": False, "status_code": None}
        finally:
            if owns_client:
                await client.aclose()

    def _build_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(
            connect=config.CONNECT_TIMEOUT,
            read=config.READ_TIMEOUT,
            write=config.CONNECT_TIMEOUT,
            pool=config.CONNECT_TIMEOUT,
        )
        headers = {"User-Agent": config.USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"}
        return httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=False, verify=True)

    async def fetch_homepage(self, url: str) -> dict:
        return await self.fetch_document(url)

    async def fetch_document(self, url: str, *, allowed_host: str | None = None) -> dict:
        current = self._validator.validate(url)
        if allowed_host and hostname_of(current) != allowed_host.lower():
            raise ScanError("EXTERNAL_REDIRECT", "The URL is outside the scanned website.")
        client = self._client
        owns_client = client is None
        if client is None:
            client = self._build_client()

        redirects = 0
        started = time.perf_counter()
        try:
            while True:
                response = await self._request(client, current)
                if response.is_redirect:
                    await response.aclose()
                    redirects += 1
                    if redirects > config.MAX_REDIRECTS:
                        raise ScanError("REDIRECT_ERROR", "The website could not be reached.")
                    location = response.headers.get("location")
                    if not location:
                        raise ScanError("REDIRECT_ERROR", "The website could not be reached.")
                    nxt = self._validator.validate(urljoin(current, location))
                    if allowed_host and hostname_of(nxt) != allowed_host.lower():
                        raise ScanError("EXTERNAL_REDIRECT", "The redirect left the scanned website.")
                    current = nxt
                    continue

                body = await self._read_limited(response)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                content_type = _content_type(response.headers.get("content-type"))
                logger.info(
                    "http_response status=%s bytes=%s url=%s",
                    response.status_code,
                    len(body),
                    safe_display_url(str(response.url)),
                )
                if content_type and not any(content_type.startswith(prefix) for prefix in HTML_TYPES):
                    raise ScanError("UNSUPPORTED_CONTENT", "This website could not be analyzed.")
                return {
                    "status_code": response.status_code,
                    "final_url": str(response.url),
                    "response_time_ms": elapsed_ms,
                    "content_type": response.headers.get("content-type", content_type),
                    "html": _decode(body, response.headers.get("content-type")),
                    "html_size_bytes": len(body),
                    "x_robots_tag": response.headers.get("x-robots-tag"),
                }
        finally:
            if owns_client:
                await client.aclose()
