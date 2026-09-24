"""Capture highlighted issue screenshots after analysis. Failures never block scan results."""

from __future__ import annotations

import io
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from backend.analyzers.uiux.config import USER_AGENT
from backend.config import ISSUE_SCREENSHOT_MAX_PER_SCAN, issue_screenshots_enabled
from backend.issues.config import ACTIONABLE_STATUSES
from backend.issues.media import (
    caption_for,
    collect_selectors,
    screenshot_summary_note,
    viewport_type_for,
    visual_kind_for,
)
from backend.issues.models import IssuesPayload, ScreenshotCaptureSummary, UnifiedIssue
from backend.store.issue_screenshots import IssueScreenshotStore

logger = logging.getLogger("sitebench.issue_capture")

DESKTOP = {"width": 1366, "height": 768}
MOBILE = {"width": 390, "height": 844}
PAGE_TIMEOUT_MS = 15_000
NETWORK_IDLE_MS = 8_000
MAX_PAGE_WORKERS = 3
CROP_PAD = 120
MAX_WIDTH = 1000
HIGHLIGHT_COLOR = "#E11D48"
HIGHLIGHT_FILL = "rgba(225, 29, 72, 0.12)"

FIND_JS = """(selectors) => {
  const picked = [];
  const seen = new Set();
  for (const raw of selectors || []) {
    if (!raw || picked.length >= 3) break;
    let nodes = [];
    try { nodes = Array.from(document.querySelectorAll(raw)); } catch (e) { continue; }
    for (const el of nodes) {
      if (!el || seen.has(el) || picked.length >= 3) continue;
      const rect = el.getBoundingClientRect();
      const width = Math.max(rect.width || 0, el.offsetWidth || 0);
      const height = Math.max(rect.height || 0, el.offsetHeight || 0);
      if (width < 1 || height < 1) continue;
      seen.add(el);
      picked.push(el);
    }
  }
  if (picked[0]) {
    try { picked[0].scrollIntoView({ block: "center", inline: "nearest" }); } catch (e) {}
  }
  return picked.length;
}"""

OVERLAY_JS = """(selectors) => {
  const picked = [];
  const seen = new Set();
  for (const raw of selectors || []) {
    if (!raw || picked.length >= 3) break;
    let nodes = [];
    try { nodes = Array.from(document.querySelectorAll(raw)); } catch (e) { continue; }
    for (const el of nodes) {
      if (!el || seen.has(el) || picked.length >= 3) continue;
      const rect = el.getBoundingClientRect();
      const width = Math.max(rect.width || 0, el.offsetWidth || 0);
      const height = Math.max(rect.height || 0, el.offsetHeight || 0);
      if (width < 1 || height < 1) continue;
      seen.add(el);
      picked.push(el);
    }
  }
  document.querySelectorAll("[data-sitebench-issue-overlay]").forEach((node) => node.remove());
  const vw = window.innerWidth || 0;
  const vh = window.innerHeight || 0;
  const boxes = [];
  picked.forEach((el, index) => {
    const rect = el.getBoundingClientRect();
    const pageWide = rect.width >= vw * 0.85 && rect.height >= vh * 0.85;
    const top = pageWide ? 8 : Math.max(0, rect.top);
    const left = pageWide ? 8 : Math.max(0, rect.left);
    const width = pageWide ? Math.max(1, vw - 16) : Math.max(1, rect.width);
    const height = pageWide ? Math.max(1, vh - 16) : Math.max(1, rect.height);
    const overlay = document.createElement("div");
    overlay.setAttribute("data-sitebench-issue-overlay", "1");
    overlay.style.cssText = [
      "position:fixed",
      `top:${top}px`,
      `left:${left}px`,
      `width:${width}px`,
      `height:${height}px`,
      "border:3px solid #E11D48",
      "background:rgba(225,29,72,0.12)",
      "border-radius:4px",
      "pointer-events:none",
      "z-index:2147483646",
      "box-sizing:border-box"
    ].join(";");
    const badge = document.createElement("div");
    badge.textContent = ["①","②","③"][index] || String(index + 1);
    badge.style.cssText = [
      "position:absolute",
      "top:-10px",
      "left:-10px",
      "min-width:18px",
      "height:18px",
      "padding:0 4px",
      "border-radius:999px",
      "background:#E11D48",
      "color:#fff",
      "font:700 11px/18px sans-serif",
      "text-align:center"
    ].join(";");
    overlay.appendChild(badge);
    document.documentElement.appendChild(overlay);
    boxes.push({ x: left, y: top, width, height, pageWide });
  });
  return { boxes, pageWide: boxes.some((box) => box.pageWide) };
}"""

DISMISS_JS = """() => {
  const labels = /^(accept|agree|allow|ok|got it|i agree|accept all|close|dismiss|continue)$/i;
  const nodes = Array.from(document.querySelectorAll("button, [role='button'], a"));
  for (const node of nodes.slice(0, 40)) {
    const text = (node.innerText || node.getAttribute("aria-label") || "").trim();
    if (!labels.test(text)) continue;
    const rect = node.getBoundingClientRect();
    if (rect.width < 8 || rect.height < 8) continue;
    try { node.click(); return true; } catch (e) {}
  }
  return false;
}"""

BLOCKED_TITLE = (
    "just a moment",
    "attention required",
    "access denied",
    "verify you are human",
    "checking your browser",
    "login",
    "sign in",
)


class IssueCaptureEngine:
    def __init__(self, store: IssueScreenshotStore | None = None) -> None:
        self._store = store or IssueScreenshotStore()

    @property
    def store(self) -> IssueScreenshotStore:
        return self._store

    def attach(
        self,
        scan_id: str,
        payload: IssuesPayload,
        *,
        persist: Callable[[IssuesPayload], None] | None = None,
    ) -> IssuesPayload:
        visual = [
            issue
            for issue in payload.issues
            if visual_kind_for(issue.check_id) == "screenshot" and issue.check_status in ACTIONABLE_STATUSES
        ]
        enabled = issue_screenshots_enabled()
        payload.screenshot_capture = ScreenshotCaptureSummary(
            status="running" if visual and enabled else "completed",
            captured=0,
            visual=len(visual),
            note=screenshot_summary_note(0, len(visual)) if visual else None,
        )
        if persist:
            persist(payload)
        if not visual or not enabled:
            return payload
        jobs = self._select_jobs(visual)
        grouped: dict[tuple[str, str], list[tuple[UnifiedIssue, list[str]]]] = defaultdict(list)
        for issue, selectors, viewport in jobs:
            page = issue.page_url or (issue.pages[0] if issue.pages else "")
            if not page:
                issue.screenshot_unavailable = True
                issue.screenshot_unavailable_reason = "Screenshot unavailable for this page"
                continue
            grouped[(page, viewport)].append((issue, selectors))
        captured = 0
        try:
            pages = list(grouped.items())
            workers = min(MAX_PAGE_WORKERS, max(1, len(pages)))
            if workers == 1:
                for key, items in pages:
                    captured += self._capture_page(scan_id, key[0], key[1], items)
                    payload.screenshot_capture.captured = captured
                    payload.screenshot_capture.note = screenshot_summary_note(captured, len(visual))
                    if persist:
                        persist(payload)
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = {
                        pool.submit(self._capture_page, scan_id, page, viewport, items): (page, viewport)
                        for (page, viewport), items in pages
                    }
                    for future in as_completed(futures):
                        try:
                            captured += int(future.result() or 0)
                        except Exception:
                            logger.exception("issue_capture_page_failed")
                        payload.screenshot_capture.captured = captured
                        payload.screenshot_capture.note = screenshot_summary_note(captured, len(visual))
                        if persist:
                            persist(payload)
        except Exception:
            logger.exception("issue_capture_failed scan_id=%s", scan_id)
        payload.screenshot_capture.status = "completed"
        payload.screenshot_capture.captured = captured
        payload.screenshot_capture.note = screenshot_summary_note(captured, len(visual))
        if persist:
            persist(payload)
        return payload

    def _select_jobs(self, issues: list[UnifiedIssue]) -> list[tuple[UnifiedIssue, list[str], str]]:
        selected: list[tuple[UnifiedIssue, list[str], str]] = []
        seen: set[tuple[str, str]] = set()
        ranked = sorted(issues, key=lambda item: (item.priority_score, item.affected_element_count), reverse=True)
        for issue in ranked:
            if len(selected) >= ISSUE_SCREENSHOT_MAX_PER_SCAN:
                continue
            page = issue.page_url or (issue.pages[0] if issue.pages else "")
            key = (issue.check_id or issue.issue_key, page)
            if key in seen:
                continue
            selectors = collect_selectors(issue)
            if not selectors:
                continue
            seen.add(key)
            selected.append((issue, selectors, viewport_type_for(issue)))
        return selected

    def _capture_page(
        self,
        scan_id: str,
        page_url: str,
        viewport: str,
        items: list[tuple[UnifiedIssue, list[str]]],
    ) -> int:
        captured = 0
        browser = None
        playwright = None
        context = None
        page = None
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.info("issue_capture_skipped reason=playwright_missing")
            return 0
        size = MOBILE if viewport == "mobile" else DESKTOP
        try:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
            kwargs: dict[str, Any] = {
                "viewport": size,
                "user_agent": USER_AGENT,
            }
            if viewport == "mobile":
                kwargs["has_touch"] = True
                kwargs["device_scale_factor"] = 2
            context = browser.new_context(**kwargs)
            context.set_default_timeout(PAGE_TIMEOUT_MS)
            context.set_default_navigation_timeout(PAGE_TIMEOUT_MS)
            page = context.new_page()
            page.goto(page_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            try:
                page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_MS)
            except Exception:
                pass
            _scroll_once(page)
            try:
                page.evaluate(DISMISS_JS)
            except Exception:
                pass
            try:
                page.wait_for_timeout(250)
            except Exception:
                pass
            if _looks_blocked(page):
                for issue, _selectors in items:
                    issue.screenshot_unavailable = True
                    issue.screenshot_unavailable_reason = "Screenshot unavailable for this page"
                return 0
            for issue, selectors in items:
                try:
                    if self._capture_issue(page, scan_id, issue, selectors, viewport, size):
                        captured += 1
                except Exception:
                    logger.info("issue_capture_item_failed issue_id=%s", issue.issue_id)
                    issue.screenshot_unavailable = True
                    issue.screenshot_unavailable_reason = "Screenshot unavailable for this page"
            return captured
        except Exception as exc:
            logger.info("issue_capture_navigate_failed url=%s error=%s", page_url, type(exc).__name__)
            for issue, _selectors in items:
                issue.screenshot_unavailable = True
                issue.screenshot_unavailable_reason = "Screenshot unavailable for this page"
            return captured
        finally:
            for closer in (page, context, browser):
                if closer is None:
                    continue
                try:
                    closer.close()
                except Exception:
                    pass
            if playwright is not None:
                try:
                    playwright.stop()
                except Exception:
                    pass

    def _capture_issue(
        self,
        page: Any,
        scan_id: str,
        issue: UnifiedIssue,
        selectors: list[str],
        viewport: str,
        size: dict[str, int],
    ) -> bool:
        found = page.evaluate(FIND_JS, selectors)
        if not found:
            return False
        try:
            page.wait_for_timeout(180)
        except Exception:
            pass
        result = page.evaluate(OVERLAY_JS, selectors)
        boxes = result.get("boxes") if isinstance(result, dict) else result
        if not isinstance(boxes, list) or not boxes:
            return False
        extra = max(0, max(issue.affected_element_count, len(selectors)) - len(boxes))
        page_wide = bool(isinstance(result, dict) and result.get("pageWide"))
        clip = None if page_wide else _clip_from_viewport_boxes(boxes, size)
        png = page.screenshot(type="png", clip=clip, timeout=PAGE_TIMEOUT_MS)
        encoded, content_type = _to_webp(png)
        url = self._store.put(scan_id, issue.issue_id, encoded, content_type)
        if not url:
            return False
        used = [selectors[index] for index in range(min(3, len(selectors)))]
        issue.screenshot_url = url
        issue.highlighted_selector = used[0] if used else None
        issue.viewport_type = viewport  # type: ignore[assignment]
        issue.screenshot_caption = caption_for(issue, used, extra)
        issue.screenshot_unavailable = False
        issue.screenshot_unavailable_reason = None
        try:
            page.evaluate("""() => document.querySelectorAll("[data-sitebench-issue-overlay]").forEach((n) => n.remove())""")
        except Exception:
            pass
        return True


def _scroll_once(page: Any) -> None:
    try:
        page.evaluate(
            """async () => {
              window.scrollTo(0, Math.min(document.body.scrollHeight || 0, window.innerHeight * 2));
              await new Promise((resolve) => setTimeout(resolve, 200));
              window.scrollTo(0, 0);
            }"""
        )
    except Exception:
        pass


def _looks_blocked(page: Any) -> bool:
    try:
        title = (page.title() or "").lower()
        url = (page.url or "").lower()
    except Exception:
        return False
    if any(token in title for token in BLOCKED_TITLE):
        return True
    if "challenge" in url or "captcha" in url:
        return True
    return False


def _clip_from_viewport_boxes(boxes: list[dict[str, Any]], size: dict[str, int]) -> dict[str, int]:
    xs = []
    ys = []
    rights = []
    bottoms = []
    for box in boxes:
        x = float(box.get("x") or 0)
        y = float(box.get("y") or 0)
        w = float(box.get("width") or 0)
        h = float(box.get("height") or 0)
        xs.append(x)
        ys.append(y)
        rights.append(x + w)
        bottoms.append(y + h)
    view_w = float(size["width"])
    view_h = float(size["height"])
    left = max(0.0, min(xs) - CROP_PAD)
    top = max(0.0, min(ys) - CROP_PAD)
    right = min(view_w, max(rights) + CROP_PAD)
    bottom = min(view_h, max(bottoms) + CROP_PAD)
    width = max(1.0, right - left)
    height = max(1.0, bottom - top)
    if left + width > view_w:
        width = max(1.0, view_w - left)
    if top + height > view_h:
        height = max(1.0, view_h - top)
    return {"x": int(left), "y": int(top), "width": int(width), "height": int(height)}


def _to_webp(png: bytes) -> tuple[bytes, str]:
    try:
        from PIL import Image
    except ImportError:
        return png, "image/png"
    image = Image.open(io.BytesIO(png))
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    if image.width > MAX_WIDTH:
        ratio = MAX_WIDTH / float(image.width)
        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
        image = image.resize((MAX_WIDTH, max(1, int(image.height * ratio))), resample)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=80, method=4)
    return buffer.getvalue(), "image/webp"
