"""Collect rendered mobile DOM measurements in a single Playwright evaluate."""

from __future__ import annotations

from typing import Any

from backend.analyzers.mobile.config import (
    DEFAULT_SCORING,
    EDGE_PADDING_PX,
    MAX_MEASURE_NODES,
    MIN_FONT_HIGH_PX,
    MIN_FONT_WARN_PX,
    OVERFLOW_TOLERANCE_PX,
    TOUCH_BASELINE_PX,
    TOUCH_GAP_PX,
    TOUCH_SMALL_PX,
)
from backend.analyzers.mobile.models import MobileSnapshot
from backend.analyzers.uiux.sanitizer import sanitize_selector, sanitize_text

MEASURE_JS = r"""() => {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const overflowTol = __OVERFLOW_TOL__;
  const minFontWarn = __MIN_FONT_WARN__;
  const minFontHigh = __MIN_FONT_HIGH__;
  const touchBaseline = __TOUCH_BASELINE__;
  const touchSmall = __TOUCH_SMALL__;
  const touchGap = __TOUCH_GAP__;
  const edgePad = __EDGE_PAD__;
  const maxNodes = __MAX_NODES__;

  function visible(el) {
    if (!el || el.nodeType !== 1) return false;
    const st = window.getComputedStyle(el);
    if (!st || st.display === "none" || st.visibility === "hidden" || Number(st.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width >= 1 && r.height >= 1;
  }

  function inFirstScreen(el) {
    const r = el.getBoundingClientRect();
    return r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw;
  }

  function safeSel(el) {
    if (!el || el === document.documentElement) return "html";
    if (el === document.body) return "body";
    const tag = (el.tagName || "div").toLowerCase();
    let id = "";
    if (el.id && /^[A-Za-z][\w-]{0,40}$/.test(el.id) && !/@/.test(el.id)) id = "#" + el.id;
    let cls = "";
    const raw = typeof el.className === "string" ? el.className : "";
    const parts = raw.trim().split(/\s+/).filter((c) => /^[A-Za-z][\w-]{0,24}$/.test(c)).slice(0, 2);
    if (parts.length) cls = "." + parts.join(".");
    return (tag + id + cls).slice(0, 72);
  }

  function textOf(el) {
    return ((el && el.innerText) || "").replace(/\s+/g, " ").trim();
  }

  function coverage(el) {
    const r = el.getBoundingClientRect();
    const ix = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0));
    const iy = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
    const area = vw * vh;
    return area > 0 ? (ix * iy) / area : 0;
  }

  function box(el) {
    const r = el.getBoundingClientRect();
    return {
      selector: safeSel(el),
      left: Math.round(r.left),
      right: Math.round(r.right),
      top: Math.round(r.top),
      bottom: Math.round(r.bottom),
      width: Math.round(r.width),
      height: Math.round(r.height),
      overflow_px: Math.round(Math.max(0, r.right - vw, -r.left)),
      clipped: r.right > vw + overflowTol || r.left < -overflowTol,
      in_viewport: inFirstScreen(el),
      visible: visible(el)
    };
  }

  function overflowCause(el) {
    const tag = (el.tagName || "").toLowerCase();
    if (tag === "table" || el.closest("table")) return "table";
    if (tag === "img" || tag === "svg" || tag === "picture") return "image";
    if (tag === "video" || tag === "iframe" || tag === "embed" || tag === "object") return "media";
    if (tag === "pre" || tag === "code" || el.closest("pre, code")) return "code";
    if (tag === "nav" || el.closest("nav, [role='navigation']")) return "navigation";
    if (tag === "form" || el.closest("form")) return "form";
    const st = window.getComputedStyle(el);
    if (st.position === "absolute" || st.position === "fixed") return "positioned";
    if (st.transform && st.transform !== "none") return "transform";
    const rawText = (el.textContent || "").trim();
    if (rawText.length > 40 && (st.whiteSpace === "nowrap" || !/\s/.test(rawText))) return "unbroken_text";
    const minPx = st.minWidth.endsWith("px") ? parseFloat(st.minWidth) : NaN;
    if (minPx && minPx > vw + overflowTol) return "min_width";
    const px = st.width.endsWith("px") ? parseFloat(st.width) : NaN;
    if (px && px > vw + overflowTol) return "fixed_width";
    if (/widget|iframe|embed|third/.test(String(el.className || "") + (el.id || ""))) return "third_party";
    return "container";
  }

  function hasScrollParent(el) {
    let node = el ? el.parentElement : null;
    let depth = 0;
    while (node && node !== document.body && depth < 8) {
      const st = window.getComputedStyle(node);
      const ox = st.overflowX;
      if ((ox === "auto" || ox === "scroll") && node.scrollWidth > node.clientWidth + overflowTol) return true;
      node = node.parentElement;
      depth += 1;
    }
    return false;
  }

  const docEl = document.documentElement;
  const body = document.body;
  const scrollWidth = Math.max(docEl.scrollWidth || 0, body ? body.scrollWidth : 0);
  const bodyScrollWidth = body ? body.scrollWidth || 0 : 0;
  const overflowPx = Math.max(0, scrollWidth - vw);
  const horizontalOverflow = overflowPx > overflowTol;

  const meta = document.querySelector("meta[name='viewport' i]");
  const metaContent = meta ? (meta.getAttribute("content") || "") : "";

  const navEl = document.querySelector("nav, [role='navigation']");
  const headerEl = document.querySelector("header");
  const navRoot = navEl || headerEl;
  const navLinks = navRoot ? Array.from(navRoot.querySelectorAll("a")).filter(visible) : [];
  const navVisible = !!(navRoot && visible(navRoot) && inFirstScreen(navRoot));
  let navOverflow = false;
  let navOverflowSel = null;
  let navOverflowPx = 0;
  for (const link of navLinks.slice(0, 40)) {
    const r = link.getBoundingClientRect();
    const extra = r.right - vw;
    if (extra > overflowTol && visible(link)) {
      navOverflow = true;
      if (extra > navOverflowPx) {
        navOverflowPx = extra;
        navOverflowSel = safeSel(link);
      }
    }
  }

  const unsafeRe = /\b(delete|remove account|purchase|buy now|pay now|checkout|logout|log out|sign out|unsubscribe|submit|send message)\b/i;
  const menuBtn = Array.from(document.querySelectorAll("button, a, [role='button'], summary")).find((el) => {
    if (!visible(el)) return false;
    const type = (el.getAttribute("type") || "").toLowerCase();
    if (type === "submit") return false;
    const label = ((el.getAttribute("aria-label") || "") + " " + textOf(el) + " " + (el.className || "") + " " + (el.id || "")).toLowerCase();
    if (unsafeRe.test(label) || unsafeRe.test(el.getAttribute("href") || "")) return false;
    return /(menu|hamburger|navbar-toggler|nav-toggle|drawer|navicon)/.test(label);
  });
  const menuName = menuBtn
    ? (menuBtn.getAttribute("aria-label") || menuBtn.getAttribute("title") || textOf(menuBtn) || "").trim()
    : "";
  const menuSafe = !!(menuBtn && !unsafeRe.test(menuName) && (menuBtn.getAttribute("type") || "").toLowerCase() !== "submit");

  const overflowing = [];
  const minWidthEls = [];
  const clippedContainers = [];
  const offscreen = [];
  const nodes = Array.from(document.querySelectorAll("header, nav, main, section, article, footer, div, img, table, ul, ol, form, h1, h2, h3, p, a, button, pre, iframe, video, input, label")).slice(0, maxNodes);
  for (const el of nodes) {
    if (!visible(el) || el === body || el === docEl) continue;
    const r = el.getBoundingClientRect();
    const extra = Math.max(0, r.right - vw, -r.left);
    if (extra > overflowTol && r.width > 24) {
      overflowing.push({
        selector: safeSel(el),
        overflow_px: Math.round(extra),
        width: Math.round(r.width),
        left: Math.round(r.left),
        right: Math.round(r.right),
        cause: overflowCause(el),
        isolated_scroll: hasScrollParent(el)
      });
    }
    const st = window.getComputedStyle(el);
    const minPx = st.minWidth.endsWith("px") ? parseFloat(st.minWidth) : NaN;
    if (minPx && minPx > vw + overflowTol) {
      minWidthEls.push({ selector: safeSel(el), min_width: Math.round(minPx) });
    }
    if ((st.overflow === "hidden" || st.overflowX === "hidden") && el.scrollWidth > el.clientWidth + 6 && r.width > 40) {
      clippedContainers.push({ selector: safeSel(el), scroll_width: el.scrollWidth, client_width: el.clientWidth });
    }
    if (r.right < -20 || r.left > vw + 20) {
      const tag = (el.tagName || "").toLowerCase();
      if (tag === "h1" || tag === "nav" || tag === "form" || tag === "button" || tag === "a") {
        offscreen.push({ selector: safeSel(el), left: Math.round(r.left) });
      }
    }
  }
  overflowing.sort((a, b) => b.overflow_px - a.overflow_px);

  const smallText = [];
  const clippedText = [];
  const overflowingHeadings = [];
  const textNodes = Array.from(document.querySelectorAll("p, li, span, a, button, label, h1, h2, h3, h4, td, th")).slice(0, 240);
  for (const el of textNodes) {
    if (!visible(el)) continue;
    const sample = textOf(el);
    if (sample.length < 4) continue;
    const st = window.getComputedStyle(el);
    const size = parseFloat(st.fontSize) || 0;
    const tag = (el.tagName || "").toLowerCase();
    const uiChrome = el.closest("svg, [aria-hidden='true']");
    if (!uiChrome && size && size < minFontWarn && (sample.length > 12 || tag.startsWith("h"))) {
      smallText.push({ selector: safeSel(el), font_size: size, text: sample.slice(0, 80), high: size < minFontHigh });
    }
    const isClip = st.overflow === "hidden" || st.overflowX === "hidden" || st.textOverflow === "ellipsis" || st.whiteSpace === "nowrap";
    if (isClip && (el.scrollWidth > el.clientWidth + 8 || el.scrollHeight > el.clientHeight + 6) && sample.length > 8) {
      clippedText.push({ selector: safeSel(el), text: sample.slice(0, 80), tag });
    }
    if (tag.match(/^h[1-3]$/) && extraBeyond(el)) {
      overflowingHeadings.push({ selector: safeSel(el), text: sample.slice(0, 80), overflow_px: Math.round(el.getBoundingClientRect().right - vw) });
    }
  }
  function extraBeyond(el) {
    const r = el.getBoundingClientRect();
    return r.right > vw + overflowTol;
  }

  const headings = Array.from(document.querySelectorAll("h1")).map((el) => {
    const r = el.getBoundingClientRect();
    const st = window.getComputedStyle(el);
    return {
      selector: safeSel(el),
      text: textOf(el).slice(0, 140),
      visible: visible(el),
      in_viewport: inFirstScreen(el),
      clipped: el.scrollWidth > el.clientWidth + 4 || r.right > vw + overflowTol,
      overflow_px: Math.round(Math.max(0, r.right - vw)),
      font_size: parseFloat(st.fontSize) || 0
    };
  });

  const interactiveSel = "button, a[href], [role='button'], input, select, textarea, summary, [role='menuitem'], [role='tab']";
  const interactiveEls = Array.from(document.querySelectorAll(interactiveSel)).filter(visible).slice(0, 80);
  const touchTargets = [];
  for (const el of interactiveEls) {
    const r = el.getBoundingClientRect();
    const minDim = Math.min(r.width, r.height);
    const label = (el.getAttribute("aria-label") || el.getAttribute("value") || textOf(el) || "").trim();
    const tag = (el.tagName || "").toLowerCase();
    const inNav = !!el.closest("nav, [role='navigation']");
    const inParagraph = !!el.closest("p");
    touchTargets.push({
      selector: safeSel(el),
      tag,
      text: label.slice(0, 80),
      width: Math.round(r.width),
      height: Math.round(r.height),
      min_dim: Math.round(minDim),
      left: Math.round(r.left),
      top: Math.round(r.top),
      right: Math.round(r.right),
      bottom: Math.round(r.bottom),
      below_baseline: minDim < touchBaseline,
      very_small: minDim < touchSmall,
      in_nav: inNav,
      in_paragraph: inParagraph,
      named: !!label
    });
  }
  const closePairs = [];
  for (let i = 0; i < touchTargets.length; i += 1) {
    for (let j = i + 1; j < touchTargets.length; j += 1) {
      const a = touchTargets[i];
      const b = touchTargets[j];
      if (a.in_paragraph && b.in_paragraph) continue;
      if (a.in_nav && b.in_nav && a.height >= 36 && b.height >= 36 && a.tag === "a" && b.tag === "a") continue;
      const dx = Math.max(0, Math.max(a.left, b.left) - Math.min(a.right, b.right));
      const dy = Math.max(0, Math.max(a.top, b.top) - Math.min(a.bottom, b.bottom));
      const overlapping = dx === 0 && dy === 0;
      const adjacent = (dx === 0 && dy > 0 && dy < touchGap) || (dy === 0 && dx > 0 && dx < touchGap);
      if (overlapping || adjacent) {
        closePairs.push({ a: a.selector, b: b.selector, gap: overlapping ? 0 : (dx || dy) });
      }
      if (closePairs.length >= 8) break;
    }
    if (closePairs.length >= 8) break;
  }

  const forms = [];
  for (const form of Array.from(document.querySelectorAll("form")).slice(0, 20)) {
    if (!visible(form) && form.querySelector("input, select, textarea, button")) {
      /* still measure */
    }
    const r = form.getBoundingClientRect();
    const controls = Array.from(form.querySelectorAll("input, select, textarea, button")).filter(visible).slice(0, 30);
    const controlRows = [];
    for (const el of controls) {
      const cr = el.getBoundingClientRect();
      controlRows.push({
        selector: safeSel(el),
        type: (el.getAttribute("type") || el.tagName || "").toLowerCase(),
        inputmode: el.getAttribute("inputmode") || "",
        autocomplete: el.getAttribute("autocomplete") || "",
        width: Math.round(cr.width),
        overflow_px: Math.round(Math.max(0, cr.right - vw)),
        outside: cr.right > vw + overflowTol || cr.left < -overflowTol
      });
    }
    forms.push({
      selector: safeSel(form),
      width: Math.round(r.width),
      overflow_px: Math.round(Math.max(0, r.right - vw, r.width - vw)),
      overflowing: r.width > vw + overflowTol || r.right > vw + overflowTol,
      controls_outside: controlRows.filter((c) => c.outside).length,
      controls: controlRows,
      isolated_scroll: hasScrollParent(form)
    });
  }

  const images = [];
  for (const img of Array.from(document.querySelectorAll("img")).slice(0, 60)) {
    const r = img.getBoundingClientRect();
    const vis = visible(img);
    const st = window.getComputedStyle(img);
    const declared = st.width;
    const maxW = st.maxWidth;
    images.push({
      selector: safeSel(img),
      visible: vis,
      width: Math.round(r.width),
      height: Math.round(r.height),
      overflow_px: Math.round(Math.max(0, r.right - vw, r.width - vw)),
      overflowing: vis && (r.width > vw + overflowTol || r.right > vw + overflowTol),
      srcset: !!img.getAttribute("srcset"),
      sizes: !!img.getAttribute("sizes"),
      object_fit: st.objectFit || "",
      max_width: maxW,
      declared_width: declared,
      responsive: maxW === "100%" || declared === "100%" || (r.width <= vw + overflowTol)
    });
  }

  const tables = [];
  for (const table of Array.from(document.querySelectorAll("table")).slice(0, 20)) {
    const r = table.getBoundingClientRect();
    const isolated = hasScrollParent(table);
    tables.push({
      selector: safeSel(table),
      width: Math.round(r.width),
      overflow_px: Math.round(Math.max(0, r.width - vw, r.right - vw)),
      overflowing: r.width > vw + overflowTol,
      isolated_scroll: isolated,
      page_wide: !isolated && r.width > vw + overflowTol
    });
  }

  const media = [];
  for (const el of Array.from(document.querySelectorAll("video, audio, iframe, embed")).slice(0, 20)) {
    const r = el.getBoundingClientRect();
    const st = window.getComputedStyle(el);
    const px = st.width.endsWith("px") ? parseFloat(st.width) : NaN;
    media.push({
      selector: safeSel(el),
      tag: (el.tagName || "").toLowerCase(),
      width: Math.round(r.width),
      height: Math.round(r.height),
      overflowing: r.width > vw + overflowTol || r.right > vw + overflowTol,
      fixed_width: !!(px && px > vw + overflowTol),
      overflow_px: Math.round(Math.max(0, r.right - vw, r.width - vw))
    });
  }

  const sticky = [];
  const overlayKeywords = /cookie|privacy|subscribe|newsletter|sign up|consent|chat|promo|discount/;
  const overlays = [];
  const positioned = Array.from(document.querySelectorAll("div, aside, section, header, footer, dialog, nav")).slice(0, 220);
  for (const el of positioned) {
    const st = window.getComputedStyle(el);
    if (st.position !== "fixed" && st.position !== "sticky") continue;
    if (!visible(el)) continue;
    const cov = coverage(el);
    const r = el.getBoundingClientRect();
    const sample = textOf(el).slice(0, 160);
    const item = {
      selector: safeSel(el),
      position: st.position,
      coverage: Math.round(cov * 1000) / 1000,
      width: Math.round(r.width),
      height: Math.round(r.height),
      top: Math.round(r.top),
      bottom: Math.round(r.bottom),
      text: sample
    };
    sticky.push(item);
    const z = parseInt(st.zIndex, 10);
    if (cov >= 0.18 && (overlayKeywords.test(sample.toLowerCase()) || (!Number.isNaN(z) && z >= 10) || st.position === "fixed")) {
      overlays.push({ ...item, keywords: overlayKeywords.test(sample.toLowerCase()) });
    }
  }

  const ctaRe = /get started|sign up|sign in|contact|buy|learn more|book|try|start|request|subscribe|demo|join|get a quote/i;
  const ctaCandidates = [];
  for (const el of Array.from(document.querySelectorAll("a, button, [role='button']")).slice(0, 80)) {
    if (!visible(el)) continue;
    const label = textOf(el) || el.getAttribute("aria-label") || "";
    if (!ctaRe.test(label)) continue;
    const r = el.getBoundingClientRect();
    ctaCandidates.push({
      selector: safeSel(el),
      text: label.slice(0, 80),
      visible: true,
      in_viewport: inFirstScreen(el),
      clipped: r.right > vw + overflowTol || r.left < -overflowTol || r.bottom < 0,
      overflow_px: Math.round(Math.max(0, r.right - vw, -r.left)),
      width: Math.round(r.width),
      height: Math.round(r.height),
      min_dim: Math.round(Math.min(r.width, r.height))
    });
  }
  const cta = ctaCandidates.find((c) => c.in_viewport) || ctaCandidates[0] || null;

  const mainEl = document.querySelector("main, [role='main'], #main, #content, .main, .content") || document.body;
  const mainVisible = !!(mainEl && visible(mainEl) && (textOf(mainEl).length > 20 || mainEl.querySelector("img, h1, p, a")));

  const edgeText = [];
  const padded = [];
  const textContainers = Array.from(document.querySelectorAll("main p, main h1, article p, .content p, p")).slice(0, 30);
  for (const el of textContainers) {
    if (!visible(el) || !inFirstScreen(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 80) continue;
    const st = window.getComputedStyle(el);
    const padL = parseFloat(st.paddingLeft) || 0;
    const padR = parseFloat(st.paddingRight) || 0;
    const marL = parseFloat(st.marginLeft) || 0;
    if (r.left < edgePad && padL + marL < edgePad && textOf(el).length > 24) {
      edgeText.push({ selector: safeSel(el), left: Math.round(r.left), padding_left: padL });
    }
  }
  if (mainEl && visible(mainEl)) {
    const st = window.getComputedStyle(mainEl);
    const padL = parseFloat(st.paddingLeft) || 0;
    const padR = parseFloat(st.paddingRight) || 0;
    const r = mainEl.getBoundingClientRect();
    const inner = Math.max(0, r.width - padL - padR);
    if (vw > 0 && inner / vw < 0.5 && padL + padR > 80) {
      padded.push({ selector: safeSel(mainEl), inner_width: Math.round(inner), padding: Math.round(padL + padR) });
    }
  }

  return {
    viewport: { name: "mobile", width: vw, height: vh },
    layout: {
      scroll_width: scrollWidth,
      body_scroll_width: bodyScrollWidth,
      viewport_width: vw,
      viewport_height: vh,
      document_width: scrollWidth,
      horizontal_overflow: horizontalOverflow,
      overflow_px: overflowPx
    },
    viewport_meta: { present: !!meta, content: metaContent },
    navigation: {
      exists: !!navRoot,
      visible: navVisible,
      links: navLinks.length,
      overflow: navOverflow,
      overflow_selector: navOverflowSel,
      overflow_px: Math.round(navOverflowPx),
      menu_button: menuBtn ? safeSel(menuBtn) : null,
      menu_named: !!menuName,
      menu_name: menuName.slice(0, 80),
      menu_safe: menuSafe,
      desktop_like: !!(navRoot && navLinks.length >= 5 && !menuBtn)
    },
    overflowing_elements: overflowing.slice(0, 12),
    min_width_elements: minWidthEls.slice(0, 8),
    clipped_containers: clippedContainers.slice(0, 8),
    offscreen_critical: offscreen.slice(0, 8),
    small_text: smallText.slice(0, 12),
    clipped_text: clippedText.slice(0, 12),
    overflowing_headings: overflowingHeadings.slice(0, 8),
    headings,
    touch_targets: {
      interactive_elements: touchTargets.length,
      below_baseline: touchTargets.filter((t) => t.below_baseline && !t.in_paragraph).length,
      very_small: touchTargets.filter((t) => t.very_small && !t.in_paragraph).length,
      items: touchTargets.filter((t) => t.below_baseline && !t.in_paragraph).slice(0, 20),
      close_pairs: closePairs
    },
    forms,
    images,
    tables,
    media,
    overlays: overlays.slice(0, 8),
    sticky_elements: sticky.slice(0, 12),
    cta: cta ? { exists: true, ...cta } : { exists: false },
    content: {
      h1: headings.length,
      h1_visible: headings.some((h) => h.visible),
      h1_in_viewport: headings.some((h) => h.in_viewport),
      h1_clipped: headings.some((h) => h.clipped),
      main_visible: mainVisible,
      main_selector: mainEl ? safeSel(mainEl) : null
    },
    spacing: { edge_text: edgeText.slice(0, 6), excessive_padding: padded },
    environment: {
      innerWidth: vw,
      innerHeight: vh,
      devicePixelRatio: window.devicePixelRatio || 1,
      maxTouchPoints: navigator.maxTouchPoints || 0,
      touch_enabled: ("ontouchstart" in window) || ((navigator.maxTouchPoints || 0) > 0)
    }
  };
}"""


def measurement_script(
    overflow_tolerance: int | None = None,
    min_font_warn: float | None = None,
    min_font_high: float | None = None,
    touch_baseline: int | None = None,
    touch_small: int | None = None,
    touch_gap: int | None = None,
    edge_padding: int | None = None,
    max_nodes: int | None = None,
) -> str:
    scoring = DEFAULT_SCORING
    script = MEASURE_JS
    replacements = {
        "__OVERFLOW_TOL__": str(int(overflow_tolerance if overflow_tolerance is not None else scoring.overflow_tolerance_px)),
        "__MIN_FONT_WARN__": str(float(min_font_warn if min_font_warn is not None else scoring.min_font_warn_px)),
        "__MIN_FONT_HIGH__": str(float(min_font_high if min_font_high is not None else scoring.min_font_high_px)),
        "__TOUCH_BASELINE__": str(int(touch_baseline if touch_baseline is not None else scoring.touch_baseline_px)),
        "__TOUCH_SMALL__": str(int(touch_small if touch_small is not None else scoring.touch_small_px)),
        "__TOUCH_GAP__": str(int(touch_gap if touch_gap is not None else scoring.touch_gap_px)),
        "__EDGE_PAD__": str(int(edge_padding if edge_padding is not None else EDGE_PADDING_PX)),
        "__MAX_NODES__": str(int(max_nodes if max_nodes is not None else MAX_MEASURE_NODES)),
    }
    for token, value in replacements.items():
        script = script.replace(token, value)
    return script


MENU_AFTER_JS = r"""() => {
  const vw = window.innerWidth;
  const expanded = document.querySelector("[aria-expanded='true']");
  const panel = document.querySelector("dialog[open], [role='dialog'], [role='menu'], nav.open, .nav-open, .is-open, [aria-expanded='true'] + *, [aria-expanded='true']");
  function visible(el) {
    if (!el) return false;
    const st = window.getComputedStyle(el);
    if (st.display === "none" || st.visibility === "hidden") return false;
    const r = el.getBoundingClientRect();
    return r.width >= 1 && r.height >= 1;
  }
  const nav = document.querySelector("nav, [role='navigation']");
  const navVisible = visible(nav);
  let overflow = false;
  let overflowPx = 0;
  const root = (panel && visible(panel) ? panel : nav);
  if (root && visible(root)) {
    const r = root.getBoundingClientRect();
    overflowPx = Math.max(0, r.right - vw);
    overflow = overflowPx > 2;
  }
  const closer = Array.from(document.querySelectorAll("button, [role='button'], a")).find((el) => {
    const label = ((el.getAttribute("aria-label") || "") + " " + (el.innerText || "")).toLowerCase();
    return visible(el) && /(close|dismiss|menu)/.test(label) && !/\b(delete|logout|purchase|checkout|pay)\b/.test(label);
  });
  function safeSel(el) {
    if (!el) return null;
    const tag = (el.tagName || "div").toLowerCase();
    let id = "";
    if (el.id && /^[A-Za-z][\w-]{0,40}$/.test(el.id)) id = "#" + el.id;
    return (tag + id).slice(0, 72);
  }
  return {
    opened: !!(expanded || (panel && visible(panel)) || navVisible),
    panel_visible: !!(panel && visible(panel)) || navVisible,
    overflow,
    overflow_px: Math.round(overflowPx),
    close_selector: closer ? safeSel(closer) : null,
    close_safe: !!closer
  };
}"""


OVERFLOW_JS = r"""() => {
  const vw = window.innerWidth;
  const scrollWidth = Math.max(document.documentElement.scrollWidth || 0, document.body ? document.body.scrollWidth : 0);
  return { viewport_width: vw, document_width: scrollWidth, overflow_px: Math.max(0, scrollWidth - vw) };
}"""


def parse_viewport_meta(content: str | None) -> dict[str, Any]:
    if not content or not str(content).strip():
        return {
            "present": False,
            "content": None,
            "width": None,
            "device_width": False,
            "zoom_restricted": False,
            "fixed_width": False,
        }
    parts: dict[str, str] = {}
    for token in str(content).split(","):
        item = token.strip()
        if not item:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
            parts[key.strip().lower()] = value.strip().lower()
        else:
            parts[item.lower()] = "true"
    width = parts.get("width")
    max_scale = parts.get("maximum-scale")
    user_scalable = parts.get("user-scalable")
    zoom_restricted = user_scalable in {"no", "0"} or _scale_at_most_one(max_scale)
    fixed_width = bool(width and width not in {"device-width", "device-height"} and _is_number(width))
    return {
        "present": True,
        "content": content,
        "width": width,
        "initial_scale": parts.get("initial-scale"),
        "user_scalable": user_scalable,
        "maximum_scale": max_scale,
        "device_width": width == "device-width",
        "zoom_restricted": zoom_restricted,
        "fixed_width": fixed_width,
    }


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _scale_at_most_one(value: str | None) -> bool:
    if value is None:
        return False
    try:
        return float(value) <= 1.0
    except (TypeError, ValueError):
        return False


def normalize_snapshot(data: dict[str, Any], *, viewport_name: str, width: int, height: int, url: str, final_url: str) -> MobileSnapshot:
    payload = dict(data or {})
    viewport = dict(payload.get("viewport") or {})
    viewport["name"] = viewport_name
    viewport["width"] = int(viewport.get("width") or width)
    viewport["height"] = int(viewport.get("height") or height)
    payload["viewport"] = viewport
    payload["page"] = {"url": url, "final_url": final_url, "ready_state": (payload.get("page") or {}).get("ready_state")}
    meta = dict(payload.get("viewport_meta") or {})
    parsed = parse_viewport_meta(meta.get("content") if meta.get("present") else None)
    parsed["present"] = bool(meta.get("present"))
    if meta.get("content"):
        parsed["content"] = meta.get("content")
    payload["viewport_meta"] = parsed

    def _clean_list(items: Any, text_key: str = "text") -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []
        for item in items or []:
            row = dict(item)
            row["selector"] = sanitize_selector(row.get("selector"))
            if text_key in row:
                row[text_key] = sanitize_text(row.get(text_key), 80)
            cleaned.append(row)
        return cleaned

    payload["overflowing_elements"] = _clean_list(payload.get("overflowing_elements"))
    payload["min_width_elements"] = _clean_list(payload.get("min_width_elements"))
    payload["clipped_containers"] = _clean_list(payload.get("clipped_containers"))
    payload["overflowing_headings"] = _clean_list(payload.get("overflowing_headings"))
    payload["offscreen_critical"] = _clean_list(payload.get("offscreen_critical"))
    payload["small_text"] = _clean_list(payload.get("small_text"))
    payload["clipped_text"] = _clean_list(payload.get("clipped_text"))
    payload["headings"] = _clean_list(payload.get("headings"))
    payload["forms"] = _clean_list(payload.get("forms"))
    payload["images"] = _clean_list(payload.get("images"))
    payload["tables"] = _clean_list(payload.get("tables"))
    payload["media"] = _clean_list(payload.get("media"))
    payload["overlays"] = _clean_list(payload.get("overlays"))
    payload["sticky_elements"] = _clean_list(payload.get("sticky_elements"))
    nav = dict(payload.get("navigation") or {})
    nav["menu_button"] = sanitize_selector(nav.get("menu_button"))
    nav["menu_name"] = sanitize_text(nav.get("menu_name"), 80)
    payload["navigation"] = nav
    cta = dict(payload.get("cta") or {})
    cta["selector"] = sanitize_selector(cta.get("selector"))
    cta["text"] = sanitize_text(cta.get("text"), 80)
    payload["cta"] = cta
    touch = dict(payload.get("touch_targets") or {})
    touch["items"] = _clean_list(touch.get("items"))
    payload["touch_targets"] = touch
    return MobileSnapshot.model_validate(payload)
