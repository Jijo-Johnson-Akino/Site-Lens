"""Collect navigation timing, resources, vitals, and DOM performance signals."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlsplit

from backend.analyzers.performance.config import MAX_LONG_TASKS, MAX_RESOURCES, WAIT_AFTER_LOAD_MS
from backend.analyzers.performance.models import PerformanceSnapshot
from backend.analyzers.performance.sanitize import first_party, pick_headers, sanitize_url

HEADER_KEYS = ("content-type", "content-encoding", "cache-control", "etag", "last-modified", "expires")

VITALS_INIT = """
window.__sbLcp = null;
window.__sbCls = 0;
window.__sbClsSources = [];
window.__sbLongTasks = [];
try {
  const lcpObs = new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const last = entries[entries.length - 1];
    if (!last) return;
    window.__sbLcp = {
      value: last.startTime,
      size: last.size || 0,
      url: last.url || "",
      id: last.id || ""
    };
  });
  lcpObs.observe({ type: "largest-contentful-paint", buffered: true });
} catch (e) {}
try {
  const clsObs = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.hadRecentInput) continue;
      window.__sbCls += entry.value;
      const sources = entry.sources || [];
      for (const source of sources) {
        const node = source.node;
        if (!node || node.nodeType !== 1 || window.__sbClsSources.length >= 3) continue;
        const tag = (node.tagName || "div").toLowerCase();
        const id = node.id ? "#" + String(node.id).replace(/[^a-zA-Z0-9_-]/g, "") : "";
        const cls = node.classList && node.classList[0] ? "." + String(node.classList[0]).replace(/[^a-zA-Z0-9_-]/g, "") : "";
        window.__sbClsSources.push({ selector: (tag + id + cls).slice(0, 72) });
      }
    }
  });
  clsObs.observe({ type: "layout-shift", buffered: true });
} catch (e) {}
try {
  const longObs = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (window.__sbLongTasks.length >= 40) break;
      window.__sbLongTasks.push({ duration: entry.duration, start: entry.startTime });
    }
  });
  longObs.observe({ type: "longtask", buffered: true });
} catch (e) {}
"""

COLLECT_JS = r"""() => {
  function num(value) {
    return (typeof value === "number" && Number.isFinite(value) && value >= 0) ? value : null;
  }
  function delta(end, start) {
    if (end == null || start == null) return null;
    const n = end - start;
    return Number.isFinite(n) && n >= 0 ? n : null;
  }
  const nav = (performance.getEntriesByType("navigation")[0] || null);
  const paints = performance.getEntriesByType("paint") || [];
  const fcp = paints.find((item) => item.name === "first-contentful-paint");
  const navResources = nav ? [{
    url: String(location.href || "").slice(0, 300),
    initiator: "navigation",
    transfer_bytes: nav.transferSize || 0,
    encoded_bytes: nav.encodedBodySize || 0,
    decoded_bytes: nav.decodedBodySize || 0,
    duration_ms: num(nav.duration)
  }] : [];
  const resources = navResources.concat((performance.getEntriesByType("resource") || []).slice(0, 150).map((item) => ({
    url: String(item.name || "").slice(0, 300),
    initiator: item.initiatorType || "",
    transfer_bytes: item.transferSize || 0,
    encoded_bytes: item.encodedBodySize || 0,
    decoded_bytes: item.decodedBodySize || 0,
    duration_ms: num(item.duration)
  })));
  const imgs = Array.from(document.images || []).slice(0, 40).map((img) => {
    const rect = img.getBoundingClientRect();
    return {
      src: String(img.currentSrc || img.src || "").slice(0, 300),
      natural_width: img.naturalWidth || 0,
      natural_height: img.naturalHeight || 0,
      rendered_width: Math.round(rect.width || img.clientWidth || 0),
      rendered_height: Math.round(rect.height || img.clientHeight || 0),
      loading: img.getAttribute("loading") || "",
      srcset: !!img.getAttribute("srcset"),
      sizes: !!img.getAttribute("sizes"),
      below_fold: rect.top > (window.innerHeight || 0)
    };
  });
  const scripts = Array.from(document.scripts || []).slice(0, 40).map((el) => ({
    src: String(el.src || "").slice(0, 300),
    async: !!el.async,
    defer: !!el.defer,
    inline_bytes: el.src ? 0 : Math.min((el.textContent || "").length, 200000),
    in_head: !!(el.parentElement && el.parentElement.tagName === "HEAD")
  }));
  const stylesheets = Array.from(document.querySelectorAll('link[rel~="stylesheet"]')).slice(0, 30).map((el) => ({
    href: String(el.href || "").slice(0, 300),
    media: el.media || "",
    in_head: !!(el.parentElement && el.parentElement.tagName === "HEAD")
  }));
  const hints = Array.from(document.querySelectorAll('link[rel="preload"], link[rel="preconnect"], link[rel="dns-prefetch"]')).slice(0, 20).map((el) => ({
    rel: el.rel,
    href: String(el.href || "").slice(0, 180)
  }));
  function maxDepth(root, limit) {
    let max = 0;
    function walk(node, depth) {
      if (depth > max) max = depth;
      if (depth >= limit) return;
      const children = node.children || [];
      for (let i = 0; i < Math.min(children.length, 40); i++) walk(children[i], depth + 1);
    }
    walk(root, 1);
    return max;
  }
  const timing = nav ? {
    navigation_start_ms: 0,
    fetch_start_ms: delta(nav.fetchStart, 0),
    dns_ms: delta(nav.domainLookupEnd, nav.domainLookupStart),
    connection_ms: delta(nav.connectEnd, nav.connectStart),
    tls_ms: (nav.secureConnectionStart > 0) ? delta(nav.connectEnd, nav.secureConnectionStart) : null,
    ttfb_ms: delta(nav.responseStart, nav.requestStart),
    response_end_ms: delta(nav.responseEnd, 0),
    dom_interactive_ms: delta(nav.domInteractive, 0),
    dom_content_loaded_ms: delta(nav.domContentLoadedEventEnd, 0),
    load_event_ms: delta(nav.loadEventEnd, 0),
    redirect_ms: delta(nav.redirectEnd, nav.redirectStart),
    redirect_count: Number.isFinite(nav.redirectCount) ? nav.redirectCount : null,
    fcp_ms: fcp ? num(fcp.startTime) : null
  } : {};
  return {
    timing,
    vitals: {
      lcp: window.__sbLcp || null,
      cls: (typeof window.__sbCls === "number") ? window.__sbCls : null,
      cls_sources: (window.__sbClsSources || []).slice(0, 3),
      long_tasks: (window.__sbLongTasks || []).slice(0, 40)
    },
    resources,
    document: {
      node_count: document.getElementsByTagName("*").length,
      depth: maxDepth(document.documentElement, 25),
      title: document.title || ""
    },
    scripts,
    stylesheets,
    images: imgs,
    hints
  };
}"""


def _ms(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return number


def _header_length(headers: dict) -> int:
    raw = (headers or {}).get("content-length")
    if not raw:
        return 0
    try:
        return max(int(raw), 0)
    except (TypeError, ValueError):
        return 0


def _bytes_of(item: dict) -> int:
    transfer = int(item.get("transfer_bytes") or 0)
    encoded = int(item.get("encoded_bytes") or 0)
    return transfer if transfer > 0 else encoded


def _resource_type(playwright_type: str | None, initiator: str | None, content_type: str | None, url: str) -> str:
    mapped = (playwright_type or initiator or "").lower()
    aliases = {
        "document": "document",
        "navigation": "document",
        "stylesheet": "stylesheet",
        "css": "stylesheet",
        "script": "script",
        "image": "image",
        "img": "image",
        "font": "font",
        "media": "media",
        "video": "media",
        "audio": "media",
        "fetch": "fetch",
        "xhr": "xhr",
        "xmlhttprequest": "xhr",
        "websocket": "websocket",
    }
    if mapped in aliases:
        return aliases[mapped]
    ctype = (content_type or "").lower()
    if "javascript" in ctype or url.endswith(".js"):
        return "script"
    if "css" in ctype or url.endswith(".css"):
        return "stylesheet"
    if ctype.startswith("image/") or url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif")):
        return "image"
    if "font" in ctype or url.endswith((".woff", ".woff2", ".ttf", ".otf")):
        return "font"
    if ctype.startswith("text/html"):
        return "document"
    return "other"


class PerformanceCollector:
    def __init__(
        self,
        *,
        html: str | None = None,
        page_url: str = "https://example.com/",
        extra_routes: dict[str, dict] | None = None,
        document_headers: dict[str, str] | None = None,
        document_delay_ms: int = 0,
        max_resources: int = MAX_RESOURCES,
    ) -> None:
        self.html = html
        self.page_url = page_url
        self.extra_routes = extra_routes or {}
        self.document_headers = document_headers or {}
        self.document_delay_ms = document_delay_ms
        self.max_resources = max_resources
        self.serves_html = html is not None
        self.responses: list[dict[str, Any]] = []
        self.redirect_hops: list[dict[str, Any]] = []

    def setup(self, page: Any) -> None:
        page.context.add_init_script(VITALS_INIT)
        page.on("response", self._on_response)
        if self.html is not None:
            page.route("**/*", self._fulfill)

    def _on_response(self, response: Any) -> None:
        if len(self.responses) >= self.max_resources:
            return
        try:
            request = response.request
            headers = pick_headers(dict(response.headers or {}))
            status = response.status
            row = {
                "url": sanitize_url(response.url),
                "raw_url": response.url,
                "status": status,
                "resource_type": request.resource_type,
                "headers": headers,
            }
            self.responses.append(row)
            if 300 <= int(status) < 400 and len(self.redirect_hops) < 8:
                location = None
                try:
                    location = (response.headers or {}).get("location")
                except Exception:
                    location = None
                self.redirect_hops.append(
                    {
                        "url": row["url"],
                        "status": status,
                        "location": sanitize_url(location) if location else None,
                    }
                )
        except Exception:
            return

    def _fulfill(self, route: Any) -> None:
        request = route.request
        url = request.url
        for needle, payload in self.extra_routes.items():
            if needle in url:
                route.fulfill(
                    status=payload.get("status", 200),
                    body=payload.get("body", b""),
                    headers=payload.get("headers") or {"content-type": payload.get("content_type", "application/octet-stream")},
                )
                return
        page_path = urlsplit(self.page_url).path or "/"
        req_path = urlsplit(url).path or "/"
        if request.resource_type == "document" or req_path.rstrip("/") == page_path.rstrip("/"):
            delay = min(max(int(self.document_delay_ms or 0), 0), 4_000)
            if delay:
                time.sleep(delay / 1000)
            headers = {"content-type": "text/html; charset=utf-8", **self.document_headers}
            route.fulfill(status=200, body=self.html or "", headers=headers)
            return
        route.abort()

    def collect(self, page: Any, final_url: str, environment: dict | None = None) -> PerformanceSnapshot:
        try:
            raw = page.evaluate(COLLECT_JS) or {}
        except Exception:
            raw = {}
        return normalize_snapshot(
            raw,
            responses=self.responses,
            url=self.page_url,
            final_url=final_url,
            environment=environment or {},
            redirect_hops=self.redirect_hops,
        )


def normalize_snapshot(
    raw: dict,
    *,
    responses: list[dict] | None = None,
    url: str,
    final_url: str,
    environment: dict | None = None,
    redirect_hops: list[dict] | None = None,
) -> PerformanceSnapshot:
    data = dict(raw or {})
    timing = dict(data.get("timing") or {})
    for key, value in list(timing.items()):
        if key.endswith("_ms"):
            timing[key] = _ms(value)
    vitals_raw = dict(data.get("vitals") or {})
    lcp = vitals_raw.get("lcp")
    if isinstance(lcp, dict) and lcp.get("value") is not None:
        lcp = {**lcp, "value": _ms(lcp.get("value")), "url": sanitize_url(lcp.get("url"))}
    long_tasks = []
    for item in (vitals_raw.get("long_tasks") or [])[:MAX_LONG_TASKS]:
        duration = _ms(item.get("duration"))
        if duration is None:
            continue
        long_tasks.append({"duration": duration, "start": _ms(item.get("start"))})
    cls_value = vitals_raw.get("cls")
    try:
        cls_value = float(cls_value) if cls_value is not None else None
    except (TypeError, ValueError):
        cls_value = None
    cls_sources = []
    for item in (vitals_raw.get("cls_sources") or [])[:3]:
        if isinstance(item, dict) and item.get("selector"):
            cls_sources.append({"selector": str(item.get("selector"))[:72]})

    response_by_url = {(item.get("raw_url") or item.get("url")): item for item in responses or []}
    resources: list[dict[str, Any]] = []
    for item in (data.get("resources") or [])[:MAX_RESOURCES]:
        res_url = sanitize_url(item.get("url"))
        raw_url = item.get("url") or ""
        match = response_by_url.get(raw_url) or next(
            (row for row in response_by_url.values() if row.get("url") == res_url),
            {},
        )
        headers = match.get("headers") or {}
        rtype = _resource_type(match.get("resource_type"), item.get("initiator"), headers.get("content-type"), raw_url)
        transfer = int(item.get("transfer_bytes") or 0)
        encoded = int(item.get("encoded_bytes") or 0)
        decoded = int(item.get("decoded_bytes") or 0)
        header_len = _header_length(headers)
        if transfer <= 0 and header_len:
            transfer = header_len
        if encoded <= 0 and header_len:
            encoded = header_len
        row = {
            "url": res_url,
            "domain": urlsplit(raw_url).hostname,
            "type": rtype,
            "initiator": item.get("initiator"),
            "transfer_bytes": transfer,
            "encoded_bytes": encoded,
            "decoded_bytes": decoded,
            "duration_ms": _ms(item.get("duration_ms")),
            "status": match.get("status"),
            "content_type": headers.get("content-type"),
            "first_party": first_party(raw_url, final_url or url),
            "cache_control": headers.get("cache-control"),
            "content_encoding": headers.get("content-encoding"),
            "etag": bool(headers.get("etag")),
            "last_modified": bool(headers.get("last-modified")),
            "expires": headers.get("expires"),
        }
        resources.append(row)

    seen = {item.get("url") for item in resources}
    for match in responses or []:
        res_url = match.get("url") or sanitize_url(match.get("raw_url"))
        if res_url in seen:
            continue
        raw_url = match.get("raw_url") or res_url
        headers = match.get("headers") or {}
        rtype = _resource_type(match.get("resource_type"), None, headers.get("content-type"), raw_url)
        length = headers.get("content-length")
        try:
            encoded = int(length) if length else 0
        except ValueError:
            encoded = 0
        resources.append(
            {
                "url": res_url,
                "domain": urlsplit(raw_url).hostname,
                "type": rtype,
                "initiator": None,
                "transfer_bytes": encoded,
                "encoded_bytes": encoded,
                "decoded_bytes": encoded,
                "duration_ms": None,
                "status": match.get("status"),
                "content_type": headers.get("content-type"),
                "first_party": first_party(raw_url, final_url or url),
                "cache_control": headers.get("cache-control"),
                "content_encoding": headers.get("content-encoding"),
                "etag": bool(headers.get("etag")),
                "last_modified": bool(headers.get("last-modified")),
                "expires": headers.get("expires"),
            }
        )
        seen.add(res_url)
        if len(resources) >= MAX_RESOURCES:
            break

    totals = _totals(resources)
    third_party_domains: dict[str, dict[str, int]] = {}
    for item in resources:
        if item.get("first_party"):
            continue
        host = item.get("domain") or "unknown"
        bucket = third_party_domains.setdefault(host, {"requests": 0, "bytes": 0})
        bucket["requests"] += 1
        bucket["bytes"] += _bytes_of(item)

    images = []
    for item in data.get("images") or []:
        row = dict(item)
        row["src"] = sanitize_url(row.get("src"))
        images.append(row)
    scripts = []
    for item in data.get("scripts") or []:
        row = dict(item)
        row["src"] = sanitize_url(row.get("src"))
        scripts.append(row)
    stylesheets = []
    for item in data.get("stylesheets") or []:
        row = dict(item)
        row["href"] = sanitize_url(row.get("href"))
        stylesheets.append(row)

    redirect_count = timing.get("redirect_count")
    hops = list(redirect_hops or [])[:8]
    if hops:
        try:
            nav_count = int(redirect_count) if redirect_count is not None else 0
        except (TypeError, ValueError):
            nav_count = 0
        redirect_count = max(nav_count, len(hops))
        timing["redirect_count"] = redirect_count
    return PerformanceSnapshot.model_validate(
        {
            "page": {"url": url, "final_url": final_url},
            "environment": environment or {},
            "timing": timing,
            "vitals": {
                "lcp": lcp,
                "cls": cls_value,
                "cls_sources": cls_sources,
                "inp": None,
                "inp_reason": "No representative interaction was available during the automated run.",
            },
            "resources": resources,
            "totals": totals,
            "document": data.get("document") or {},
            "scripts": scripts,
            "stylesheets": stylesheets,
            "images": images,
            "hints": data.get("hints") or [],
            "long_tasks": long_tasks,
            "redirects": {"count": redirect_count, "duration_ms": timing.get("redirect_ms"), "hops": hops},
            "third_party_domains": [
                {"domain": host, **counts} for host, counts in sorted(third_party_domains.items(), key=lambda item: item[1]["bytes"], reverse=True)[:12]
            ],
        }
    )


def _totals(resources: list[dict]) -> dict[str, Any]:
    buckets = {
        "document": 0,
        "stylesheet": 0,
        "script": 0,
        "image": 0,
        "font": 0,
        "media": 0,
        "other": 0,
    }
    transfer = 0
    decoded = 0
    third_bytes = 0
    third_req = 0
    for item in resources:
        size = _bytes_of(item)
        transfer += size
        decoded += int(item.get("decoded_bytes") or 0)
        rtype = item.get("type") or "other"
        if rtype in buckets:
            buckets[rtype] += size
        else:
            buckets["other"] += size
        if not item.get("first_party"):
            third_bytes += size
            third_req += 1
    percentages = {}
    if transfer:
        percentages = {
            "html": round(100 * buckets["document"] / transfer, 1),
            "css": round(100 * buckets["stylesheet"] / transfer, 1),
            "javascript": round(100 * buckets["script"] / transfer, 1),
            "images": round(100 * buckets["image"] / transfer, 1),
            "fonts": round(100 * buckets["font"] / transfer, 1),
            "third_party": round(100 * third_bytes / transfer, 1),
        }
    return {
        "total_requests": len(resources),
        "transfer_bytes": transfer,
        "resource_bytes": decoded,
        "html_bytes": buckets["document"],
        "css_bytes": buckets["stylesheet"],
        "js_bytes": buckets["script"],
        "image_bytes": buckets["image"],
        "font_bytes": buckets["font"],
        "media_bytes": buckets["media"],
        "other_bytes": buckets["other"],
        "third_party_bytes": third_bytes,
        "third_party_requests": third_req,
        "percentages": percentages,
    }


WAIT_MS = WAIT_AFTER_LOAD_MS
