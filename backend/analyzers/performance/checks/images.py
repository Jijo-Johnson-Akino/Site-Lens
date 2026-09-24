from __future__ import annotations

from urllib.parse import urlsplit

from backend.analyzers.performance.checks._util import format_bytes, perf_check
from backend.analyzers.performance.config import DEFAULT_SCORING, PerfScoringConfig
from backend.analyzers.performance.models import CheckResult, PerformanceSnapshot


def _resource_key(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlsplit(str(url))
    return f"{(parsed.netloc or '').lower()}{(parsed.path or '').rstrip('/')}".lower()


def run(snapshot: PerformanceSnapshot, config: PerfScoringConfig = DEFAULT_SCORING) -> list[CheckResult]:
    image_bytes = int((snapshot.totals or {}).get("image_bytes") or 0)
    images = snapshot.images or []
    lcp = snapshot.vitals.get("lcp") if isinstance(snapshot.vitals, dict) else None
    lcp_url = (lcp or {}).get("url") if isinstance(lcp, dict) else None
    checks: list[CheckResult] = []

    large = [item for item in snapshot.resources if item.get("type") == "image" and int(item.get("transfer_bytes") or item.get("encoded_bytes") or 0) >= config.img_warn_bytes]
    high = [item for item in large if int(item.get("transfer_bytes") or item.get("encoded_bytes") or 0) >= config.img_high_bytes]
    if high:
        checks.append(perf_check(snapshot, check_id="PERF-IMG-001", name="Large image resources", group="images", status="warning", severity="high", message=f"{len(high)} image(s) exceed {format_bytes(config.img_high_bytes)}.", recommendation="Compress images and serve appropriately sized variants. File size alone is not an automatic failure.", affected_element_count=len(high), resource_url=high[0].get("url"), detected=format_bytes(image_bytes)))
    elif large:
        checks.append(perf_check(snapshot, check_id="PERF-IMG-001", name="Large image resources", group="images", status="warning", severity="medium", message=f"{len(large)} image(s) exceed {format_bytes(config.img_warn_bytes)}.", affected_element_count=len(large), resource_url=large[0].get("url"), detected=format_bytes(image_bytes)))
    else:
        checks.append(perf_check(snapshot, check_id="PERF-IMG-001", name="Large image resources", group="images", status="pass", severity="medium", message=f"Image transfer is {format_bytes(image_bytes)}.", detected=format_bytes(image_bytes)))

    oversized = []
    for item in images:
        natural_w = int(item.get("natural_width") or 0)
        rendered_w = int(item.get("rendered_width") or 0)
        if item.get("srcset"):
            continue
        if natural_w >= 400 and rendered_w >= 40 and natural_w >= rendered_w * config.oversize_ratio:
            oversized.append(item)
    if oversized:
        checks.append(perf_check(snapshot, check_id="PERF-IMG-002", name="Oversized images", group="images", status="warning", severity="medium", message=f"{len(oversized)} image(s) may be larger than their rendered size.", recommendation="Serve images closer to displayed dimensions. Responsive srcset selections are not flagged.", affected_element_count=len(oversized), resource_url=oversized[0].get("src"), selector="img"))
    elif images:
        checks.append(perf_check(snapshot, check_id="PERF-IMG-002", name="Oversized images", group="images", status="pass", severity="low", message="No clearly oversized images were detected (srcset images were skipped)."))
    else:
        checks.append(perf_check(snapshot, check_id="PERF-IMG-002", name="Oversized images", group="images", status="not_applicable", severity="low", message="No images were present to compare natural vs rendered size."))

    lcp_key = _resource_key(lcp_url)
    below = [
        item for item in images
        if item.get("below_fold")
        and str(item.get("loading") or "").lower() != "lazy"
        and (not lcp_key or _resource_key(item.get("src")) != lcp_key)
    ]
    if below:
        checks.append(perf_check(snapshot, check_id="PERF-IMG-003", name="Below-the-fold lazy loading", group="images", status="warning", severity="low", message=f"{len(below)} below-the-fold image(s) do not use loading=\"lazy\".", recommendation="Lazy-load offscreen images. Do not lazy-load the LCP/hero image.", affected_element_count=len(below), resource_url=below[0].get("src")))
    elif images:
        checks.append(perf_check(snapshot, check_id="PERF-IMG-003", name="Below-the-fold lazy loading", group="images", status="pass", severity="low", message="Below-the-fold images use lazy loading or none were offscreen."))
    else:
        checks.append(perf_check(snapshot, check_id="PERF-IMG-003", name="Below-the-fold lazy loading", group="images", status="not_applicable", severity="low", message="No images were present."))
    return checks
