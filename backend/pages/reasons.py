"""User-safe skip/failure copy. Never includes stack traces or internals."""

from __future__ import annotations

from backend.errors import ScanError

SKIP_CODES = {
    "BLOCKED_URL": "Disallowed destination.",
    "UNSUPPORTED_CONTENT": "Unsupported content type.",
    "RESPONSE_TOO_LARGE": "Response exceeds the allowed size.",
    "EXTERNAL_REDIRECT": "Redirect left the scanned website.",
    "INVALID_URL": "Unsupported URL.",
}

FAIL_CODES = {
    "TIMEOUT": "The request timed out.",
    "WEBSITE_UNREACHABLE": "The page could not be reached.",
    "TLS_ERROR": "The page could not be reached.",
    "REDIRECT_ERROR": "Too many redirects.",
}

SKIP_PAGE_LIMIT = "Maximum page limit reached."
SKIP_DEPTH_LIMIT = "Maximum crawl depth reached."
SKIP_DUPLICATE = "Duplicate URL."
SKIP_RESOURCE = "Unsupported resource."
SKIP_EXTERNAL = "External destination."


def classify_fetch_error(exc: ScanError) -> tuple[str, str]:
    if exc.code in SKIP_CODES:
        return "skipped", SKIP_CODES[exc.code]
    if exc.code in FAIL_CODES:
        return "failed", FAIL_CODES[exc.code]
    return "failed", "The page could not be retrieved."
