"""SSRF-aware URL validation. Checks protocols, ports, hostnames, and resolved DNS."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

from backend.errors import ScanError

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443}
BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
}
BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".home",
    ".corp",
    ".private",
)
EXTRA_BLOCKED_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("198.18.0.0/15"),
)


def safe_display_url(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.hostname or parsed.netloc
    return f"{parsed.scheme}://{host}{parsed.path}"


def normalize_submitted_url(raw: str) -> str:
    trimmed = raw.strip()
    if not trimmed:
        raise ScanError("INVALID_URL", "Please enter a valid website URL.")
    if "://" not in trimmed:
        trimmed = f"https://{trimmed}"
    return trimmed


def _blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return _blocked_ip(ip.ipv4_mapped)
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True
    return any(ip in network for network in EXTRA_BLOCKED_NETWORKS)


def _blocked_hostname(host: str) -> bool:
    lowered = host.rstrip(".").lower()
    if lowered in BLOCKED_HOSTS:
        return True
    return any(lowered.endswith(suffix) for suffix in BLOCKED_HOST_SUFFIXES)


def resolve_host(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ScanError("WEBSITE_UNREACHABLE", "The website could not be reached.") from exc
    addresses: list[str] = []
    for info in infos:
        addr = info[4][0]
        if addr not in addresses:
            addresses.append(addr)
    if not addresses:
        raise ScanError("WEBSITE_UNREACHABLE", "The website could not be reached.")
    return addresses


class UrlValidator:
    def __init__(self, resolver=resolve_host) -> None:
        self._resolver = resolver

    def parse(self, raw: str) -> str:
        normalized = normalize_submitted_url(raw)
        parsed = urlsplit(normalized)
        if parsed.scheme not in ALLOWED_SCHEMES:
            raise ScanError("INVALID_URL", "Please enter a valid website URL.")
        if parsed.username or parsed.password:
            raise ScanError("INVALID_URL", "Please enter a valid website URL.")
        host = parsed.hostname
        if not host:
            raise ScanError("INVALID_URL", "Please enter a valid website URL.")
        try:
            port = parsed.port
        except ValueError as exc:
            raise ScanError("INVALID_URL", "Please enter a valid website URL.") from exc
        port = port or (443 if parsed.scheme == "https" else 80)
        if port not in ALLOWED_PORTS:
            raise ScanError("BLOCKED_URL", "This website cannot be scanned.")
        if _blocked_hostname(host):
            raise ScanError("BLOCKED_URL", "This website cannot be scanned.")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if "." not in host and ":" not in host:
                raise ScanError("INVALID_URL", "Please enter a valid website URL.") from None
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))

    def validate(self, raw: str) -> str:
        """Return a normalized URL after DNS and IP checks."""
        url = self.parse(raw)
        parsed = urlsplit(url)
        host = parsed.hostname
        if host is None:
            raise ScanError("INVALID_URL", "Please enter a valid website URL.")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            literal_ip = ipaddress.ip_address(host)
        except ValueError:
            literal_ip = None
        if literal_ip is not None and _blocked_ip(literal_ip):
            raise ScanError("BLOCKED_URL", "This website cannot be scanned.")
        for address in self._resolver(host, port):
            try:
                ip = ipaddress.ip_address(address)
            except ValueError as exc:
                raise ScanError("BLOCKED_URL", "This website cannot be scanned.") from exc
            if _blocked_ip(ip):
                raise ScanError("BLOCKED_URL", "This website cannot be scanned.")
        return url
