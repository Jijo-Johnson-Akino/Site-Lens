from __future__ import annotations

import pytest

from backend.errors import ScanError
from backend.services.url_validator import UrlValidator

PUBLIC_IP = "93.184.216.34"


def public_dns(_host: str, _port: int) -> list[str]:
    return [PUBLIC_IP]


def private_dns(_host: str, _port: int) -> list[str]:
    return ["10.0.0.8"]


@pytest.fixture
def validator() -> UrlValidator:
    return UrlValidator(resolver=public_dns)


@pytest.mark.parametrize(
    "raw",
    [
        "https://example.com",
        "http://example.com",
        "example.com",
        "https://example.com/path?q=1",
    ],
)
def test_allows_public_http_urls(validator: UrlValidator, raw: str) -> None:
    url = validator.validate(raw)
    assert url.startswith("http")
    assert "example.com" in url


@pytest.mark.parametrize(
    "raw",
    [
        "localhost",
        "http://localhost",
        "https://localhost",
        "http://foo.localhost",
        "127.0.0.1",
        "http://127.0.0.1",
        "http://192.168.1.1",
        "http://10.0.0.1",
        "http://172.16.0.4",
        "http://169.254.169.254",
        "http://[::1]",
        "file:///etc/passwd",
        "ftp://example.com",
        "javascript:alert(1)",
        "http://example.com:8080",
        "http://example.com:22",
    ],
)
def test_rejects_unsafe_urls(raw: str) -> None:
    validator = UrlValidator(resolver=public_dns)
    with pytest.raises(ScanError) as exc:
        validator.validate(raw)
    assert exc.value.code in {"INVALID_URL", "BLOCKED_URL", "WEBSITE_UNREACHABLE"}


def test_rejects_dns_to_private_network() -> None:
    validator = UrlValidator(resolver=private_dns)
    with pytest.raises(ScanError) as exc:
        validator.validate("https://evil.example")
    assert exc.value.code == "BLOCKED_URL"


def test_rejects_userinfo(validator: UrlValidator) -> None:
    with pytest.raises(ScanError):
        validator.validate("https://user:pass@example.com")
