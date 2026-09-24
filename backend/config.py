"""Runtime configuration. Secrets belong in .env, never in code."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float, fallback_name: str | None = None) -> float:
    raw = os.getenv(name)
    if (raw is None or not raw.strip()) and fallback_name:
        raw = os.getenv(fallback_name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


USER_AGENT: str = os.getenv("SITEBENCH_USER_AGENT", "SiteLensBot/1.0")
CONNECT_TIMEOUT: float = _float_env("SITEBENCH_CONNECT_TIMEOUT", 10)
READ_TIMEOUT: float = _float_env("SITEBENCH_READ_TIMEOUT", 20, "SITEBENCH_REQUEST_TIMEOUT")
MAX_RESPONSE_SIZE: int = _int_env("SITEBENCH_MAX_RESPONSE_SIZE", 10 * 1024 * 1024)
MAX_REDIRECTS: int = _int_env("SITEBENCH_MAX_REDIRECTS", 5)
MAX_CONCURRENT_SCANS: int = max(1, _int_env("SITEBENCH_MAX_CONCURRENT_SCANS", 3))
ISSUE_SCREENSHOT_DIR: Path = Path(os.getenv("SITEBENCH_ISSUE_SCREENSHOT_DIR") or (ROOT / "storage" / "screenshots"))
ISSUE_SCREENSHOT_TTL_DAYS: int = max(1, _int_env("SITEBENCH_ISSUE_SCREENSHOT_TTL_DAYS", 30))
ISSUE_SCREENSHOT_MAX_PER_SCAN: int = max(1, _int_env("SITEBENCH_ISSUE_SCREENSHOT_MAX_PER_SCAN", 20))


def issue_screenshots_enabled() -> bool:
    raw = os.getenv("SITEBENCH_ISSUE_SCREENSHOTS")
    if raw is not None and raw.strip():
        return raw.strip().lower() not in {"0", "false", "no", "off"}
    return "PYTEST_CURRENT_TEST" not in os.environ
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv(
        "SITEBENCH_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
