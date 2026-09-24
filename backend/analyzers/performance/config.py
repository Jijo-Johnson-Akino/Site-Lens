"""Configurable performance scoring and measurement thresholds."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


WAIT_AFTER_LOAD_MS = _int_env("SITEBENCH_PERF_WAIT_AFTER_LOAD_MS", 1500)
MAX_RESOURCES = _int_env("SITEBENCH_PERF_MAX_RESOURCES", 150)
MAX_LONG_TASKS = _int_env("SITEBENCH_PERF_MAX_LONG_TASKS", 40)

TTFB_GOOD_MS = _int_env("SITEBENCH_PERF_TTFB_GOOD_MS", 800)
TTFB_POOR_MS = _int_env("SITEBENCH_PERF_TTFB_POOR_MS", 1800)
LCP_GOOD_MS = _int_env("SITEBENCH_PERF_LCP_GOOD_MS", 2500)
LCP_POOR_MS = _int_env("SITEBENCH_PERF_LCP_POOR_MS", 4000)
CLS_GOOD = _float_env("SITEBENCH_PERF_CLS_GOOD", 0.10)
CLS_POOR = _float_env("SITEBENCH_PERF_CLS_POOR", 0.25)
INP_GOOD_MS = _int_env("SITEBENCH_PERF_INP_GOOD_MS", 200)
INP_POOR_MS = _int_env("SITEBENCH_PERF_INP_POOR_MS", 500)
DCL_GOOD_MS = _int_env("SITEBENCH_PERF_DCL_GOOD_MS", 1800)
DCL_POOR_MS = _int_env("SITEBENCH_PERF_DCL_POOR_MS", 3500)
LOAD_GOOD_MS = _int_env("SITEBENCH_PERF_LOAD_GOOD_MS", 2500)
LOAD_POOR_MS = _int_env("SITEBENCH_PERF_LOAD_POOR_MS", 5000)

JS_WARN_BYTES = _int_env("SITEBENCH_PERF_JS_WARN_BYTES", 500_000)
JS_HIGH_BYTES = _int_env("SITEBENCH_PERF_JS_HIGH_BYTES", 1_000_000)
CSS_WARN_BYTES = _int_env("SITEBENCH_PERF_CSS_WARN_BYTES", 150_000)
CSS_HIGH_BYTES = _int_env("SITEBENCH_PERF_CSS_HIGH_BYTES", 300_000)
IMG_WARN_BYTES = _int_env("SITEBENCH_PERF_IMG_WARN_BYTES", 500_000)
IMG_HIGH_BYTES = _int_env("SITEBENCH_PERF_IMG_HIGH_BYTES", 1_000_000)
HTML_WARN_BYTES = _int_env("SITEBENCH_PERF_HTML_WARN_BYTES", 200_000)
HTML_HIGH_BYTES = _int_env("SITEBENCH_PERF_HTML_HIGH_BYTES", 500_000)
FONT_WARN_BYTES = _int_env("SITEBENCH_PERF_FONT_WARN_BYTES", 200_000)
FONT_HIGH_BYTES = _int_env("SITEBENCH_PERF_FONT_HIGH_BYTES", 400_000)
DOM_WARN = _int_env("SITEBENCH_PERF_DOM_WARN", 1500)
DOM_HIGH = _int_env("SITEBENCH_PERF_DOM_HIGH", 3000)
REQ_WARN = _int_env("SITEBENCH_PERF_REQ_WARN", 75)
REQ_HIGH = _int_env("SITEBENCH_PERF_REQ_HIGH", 150)
TP_RATIO_WARN = _float_env("SITEBENCH_PERF_TP_RATIO_WARN", 0.30)
TP_REQ_WARN = _int_env("SITEBENCH_PERF_TP_REQ_WARN", 15)
REDIRECT_WARN = _int_env("SITEBENCH_PERF_REDIRECT_WARN", 2)
REDIRECT_FAIL = _int_env("SITEBENCH_PERF_REDIRECT_FAIL", 3)
OVERSIZE_RATIO = _float_env("SITEBENCH_PERF_OVERSIZE_RATIO", 2.5)
COMPRESS_MIN_BYTES = _int_env("SITEBENCH_PERF_COMPRESS_MIN_BYTES", 1500)
LONG_TASK_MS = _int_env("SITEBENCH_PERF_LONG_TASK_MS", 50)
LONG_TASK_TOTAL_WARN_MS = _int_env("SITEBENCH_PERF_LONG_TASK_TOTAL_WARN_MS", 300)

DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "vitals": 0.30,
    "loading": 0.13,
    "server": 0.10,
    "javascript": 0.10,
    "images": 0.10,
    "css": 0.04,
    "fonts": 0.02,
    "third_party": 0.05,
    "caching": 0.05,
    "compression": 0.03,
    "blocking": 0.04,
    "dom": 0.02,
    "network": 0.01,
    "redirects": 0.01,
}

DEFAULT_CHECK_WEIGHTS: dict[str, int] = {
    "PERF-VITAL-001": 14,
    "PERF-VITAL-002": 10,
    "PERF-VITAL-003": 6,
    "PERF-TTFB-001": 12,
    "PERF-LOAD-001": 8,
    "PERF-LOAD-002": 6,
    "PERF-REDIR-001": 6,
    "PERF-HTML-001": 3,
    "PERF-JS-001": 8,
    "PERF-JS-002": 8,
    "PERF-CSS-001": 6,
    "PERF-IMG-001": 7,
    "PERF-IMG-002": 6,
    "PERF-IMG-003": 4,
    "PERF-FONT-001": 3,
    "PERF-TP-001": 8,
    "PERF-CACHE-001": 6,
    "PERF-COMP-001": 6,
    "PERF-BLOCK-001": 8,
    "PERF-DOM-001": 4,
    "PERF-NET-001": 4,
    "PERF-LONG-001": 4,
}

LIMITATIONS = [
    "Performance results are based on this automated browser run and can vary with network, device, browser, server load, and third-party services.",
    "One automated run does not represent every real-world user.",
    "Some Core Web Vitals require real user interaction and may be unavailable.",
    "Automated analysis does not replace field data such as CrUX or RUM.",
    "Results may vary between scans.",
]


@dataclass(frozen=True)
class PerfScoringConfig:
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    check_weights: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CHECK_WEIGHTS))
    ttfb_good_ms: int = TTFB_GOOD_MS
    ttfb_poor_ms: int = TTFB_POOR_MS
    lcp_good_ms: int = LCP_GOOD_MS
    lcp_poor_ms: int = LCP_POOR_MS
    cls_good: float = CLS_GOOD
    cls_poor: float = CLS_POOR
    dcl_good_ms: int = DCL_GOOD_MS
    dcl_poor_ms: int = DCL_POOR_MS
    load_good_ms: int = LOAD_GOOD_MS
    load_poor_ms: int = LOAD_POOR_MS
    js_warn_bytes: int = JS_WARN_BYTES
    js_high_bytes: int = JS_HIGH_BYTES
    css_warn_bytes: int = CSS_WARN_BYTES
    css_high_bytes: int = CSS_HIGH_BYTES
    img_warn_bytes: int = IMG_WARN_BYTES
    img_high_bytes: int = IMG_HIGH_BYTES
    html_warn_bytes: int = HTML_WARN_BYTES
    html_high_bytes: int = HTML_HIGH_BYTES
    font_warn_bytes: int = FONT_WARN_BYTES
    font_high_bytes: int = FONT_HIGH_BYTES
    dom_warn: int = DOM_WARN
    dom_high: int = DOM_HIGH
    req_warn: int = REQ_WARN
    req_high: int = REQ_HIGH
    tp_ratio_warn: float = TP_RATIO_WARN
    tp_req_warn: int = TP_REQ_WARN
    redirect_warn: int = REDIRECT_WARN
    redirect_fail: int = REDIRECT_FAIL
    oversize_ratio: float = OVERSIZE_RATIO
    compress_min_bytes: int = COMPRESS_MIN_BYTES
    long_task_ms: int = LONG_TASK_MS
    long_task_total_warn_ms: int = LONG_TASK_TOTAL_WARN_MS

    def weight_for(self, check_id: str) -> int:
        return self.check_weights.get(check_id, 1)


DEFAULT_SCORING = PerfScoringConfig()
