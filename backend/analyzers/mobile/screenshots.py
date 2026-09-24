from backend.analyzers.mobile.config import COMPACT_VIEWPORT, PRIMARY_VIEWPORT, SCREENSHOT_KEYS

PRIMARY_KEY = SCREENSHOT_KEYS[0]
PRIMARY_FULL_KEY = SCREENSHOT_KEYS[1]
COMPACT_KEY = SCREENSHOT_KEYS[2]
COMPACT_FULL_KEY = SCREENSHOT_KEYS[3]


def screenshot_url(scan_id: str, key: str) -> str:
    return f"/api/scans/{scan_id}/mobile/screenshots/{key}"


def allowed_screenshot_key(key: str) -> bool:
    return key in SCREENSHOT_KEYS


def viewport_for_key(key: str) -> dict[str, int]:
    if key.startswith("mobile_375"):
        return dict(COMPACT_VIEWPORT)
    return dict(PRIMARY_VIEWPORT)
