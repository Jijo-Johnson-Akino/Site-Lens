"""Collect rendered DOM measurements in a single Playwright evaluate."""

from __future__ import annotations

from backend.analyzers.uiux.config import MIN_FONT_PX, OVERFLOW_TOLERANCE_PX
from backend.analyzers.uiux.models import ViewportSnapshot
from backend.analyzers.uiux.sanitizer import sanitize_selector, sanitize_text

MEASURE_JS = r"""() => {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const overflowTol = __OVERFLOW_TOL__;
  const minFont = __MIN_FONT__;
  function cssEscape(value) {
    if (window.CSS && window.CSS.escape) return window.CSS.escape(value);
    return String(value).replace(/["\\\\]/g, "\\\\$&");
  }

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

  const scrollWidth = Math.max(
    document.documentElement.scrollWidth || 0,
    document.body ? document.body.scrollWidth : 0
  );
  const scrollHeight = Math.max(
    document.documentElement.scrollHeight || 0,
    document.body ? document.body.scrollHeight : 0
  );
  const overflowPx = Math.max(0, scrollWidth - vw);
  const horizontalOverflow = overflowPx > overflowTol;

  const navEl = document.querySelector("nav, [role='navigation']");
  const headerEl = document.querySelector("header");
  const navRoot = navEl || headerEl;
  const navLinks = navRoot
    ? Array.from(navRoot.querySelectorAll("a")).filter(visible)
    : [];
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

  const menuBtn = Array.from(document.querySelectorAll("button, a, [role='button']")).find((el) => {
    const label = ((el.getAttribute("aria-label") || "") + " " + textOf(el) + " " + (el.className || "")).toLowerCase();
    return visible(el) && /(menu|hamburger|navbar-toggler|nav-toggle|drawer)/.test(label);
  });

  let logo = null;
  const logoCandidates = Array.from(document.querySelectorAll("header a, a[class*='logo' i], a[id*='logo' i]")).slice(0, 12);
  for (const a of logoCandidates) {
    if (!visible(a)) continue;
    const hasMark = a.querySelector("img, svg") || /logo|brand|home/.test((a.className || "") + a.id);
    if (hasMark || (headerEl && headerEl.contains(a) && a.querySelector("img, svg"))) {
      logo = {
        exists: true,
        selector: safeSel(a),
        href: a.getAttribute("href") || "",
        visible: true
      };
      break;
    }
  }

  const headings = Array.from(document.querySelectorAll("h1")).map((el) => ({
    selector: safeSel(el),
    text: textOf(el).slice(0, 140),
    visible: visible(el),
    in_viewport: inFirstScreen(el),
    clipped: el.scrollWidth > el.clientWidth + 4 || el.scrollHeight > el.clientHeight + 4
  }));
  const h1Visible = headings.some((h) => h.visible);

  const paragraphs = Array.from(document.querySelectorAll("p")).filter(visible);

  const buttonEls = Array.from(document.querySelectorAll("button, [role='button'], input[type='button'], input[type='submit']"));
  const buttons = [];
  for (const el of buttonEls.slice(0, 80)) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    const label = (el.getAttribute("value") || textOf(el) || el.getAttribute("aria-label") || "").trim();
    buttons.push({
      selector: safeSel(el),
      text: label.slice(0, 80),
      empty: !label,
      disabled: !!(el.disabled || el.getAttribute("aria-disabled") === "true"),
      visible: true,
      in_viewport: inFirstScreen(el),
      clipped: r.right > vw + overflowTol || r.left < -overflowTol || r.bottom < 0,
      overflow_px: Math.max(0, r.right - vw, -r.left),
      pointer_events: window.getComputedStyle(el).pointerEvents,
      width: r.width,
      height: r.height,
      top: r.top
    });
  }

  const linkEls = Array.from(document.querySelectorAll("a[href]"));
  const links = [];
  for (const el of linkEls.slice(0, 120)) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    links.push({
      selector: safeSel(el),
      text: textOf(el).slice(0, 80),
      href: (el.getAttribute("href") || "").slice(0, 180),
      visible: true,
      in_viewport: inFirstScreen(el),
      clipped: r.right > vw + overflowTol || r.left < -overflowTol
    });
  }

  const ctaRe = /get started|sign up|sign in|contact|buy|learn more|book|try|start|request|subscribe|demo|join|get a quote/i;
  const ctaCandidates = [];
  for (const item of buttons) {
    if (ctaRe.test(item.text)) ctaCandidates.push({ ...item, kind: "button" });
  }
  for (const item of links) {
    if (ctaRe.test(item.text)) ctaCandidates.push({ ...item, kind: "link" });
  }
  let primary = ctaCandidates.find((c) => c.in_viewport) || ctaCandidates[0] || null;
  if (!primary) {
    const large = buttons.filter((b) => b.width * b.height >= 2400 && b.in_viewport && !b.empty);
    if (large.length) primary = { ...large[0], kind: "button" };
  }

  const formEls = Array.from(document.querySelectorAll("form"));
  const forms = [];
  for (const form of formEls.slice(0, 12)) {
    if (!visible(form) && !form.querySelector("input, textarea, select, button")) continue;
    const fields = Array.from(form.querySelectorAll("input, textarea, select")).filter((el) => {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      return type !== "hidden" && visible(el);
    });
    let labeled = 0;
    for (const field of fields) {
      const id = field.id;
      const hasLabel = (id && document.querySelector("label[for='" + cssEscape(id) + "']")) || field.closest("label") || field.getAttribute("aria-label") || field.getAttribute("aria-labelledby") || field.getAttribute("placeholder");
      if (hasLabel) labeled += 1;
    }
    const submit = form.querySelector("button[type='submit'], input[type='submit'], button:not([type]), [type='image']");
    forms.push({
      selector: safeSel(form),
      visible: visible(form),
      fields: fields.length,
      labeled,
      has_submit: !!(submit && visible(submit))
    });
  }

  const imageEls = Array.from(document.querySelectorAll("img"));
  const images = [];
  for (const img of imageEls.slice(0, 80)) {
    const r = img.getBoundingClientRect();
    const vis = visible(img);
    const naturalW = img.naturalWidth || 0;
    const naturalH = img.naturalHeight || 0;
    const broken = vis && img.complete && naturalW === 0 && !!(img.currentSrc || img.getAttribute("src"));
    let overflow = false;
    const parent = img.parentElement;
    if (parent && vis) {
      const pr = parent.getBoundingClientRect();
      overflow = r.right > pr.right + overflowTol + 4 || r.width > vw + overflowTol;
    }
    let distorted = false;
    if (naturalW > 20 && naturalH > 20 && r.width > 40 && r.height > 40) {
      const nr = naturalW / naturalH;
      const rr = r.width / r.height;
      distorted = Math.abs(nr - rr) / nr > 0.4;
    }
    images.push({
      selector: safeSel(img),
      visible: vis,
      broken,
      overflow,
      distorted,
      width: r.width,
      height: r.height,
      natural_width: naturalW,
      natural_height: naturalH
    });
  }

  const overflowing = [];
  const fixedWidth = [];
  const nodes = Array.from(document.querySelectorAll("header, nav, main, section, article, footer, div, img, table, ul, form, h1, h2, p, a, button")).slice(0, 280);
  for (const el of nodes) {
    if (!visible(el) || el === document.body || el === document.documentElement) continue;
    const r = el.getBoundingClientRect();
    const extra = r.right - vw;
    if (extra > overflowTol + 4 && r.width > 24) {
      overflowing.push({ selector: safeSel(el), overflow_px: Math.round(extra), width: Math.round(r.width) });
    }
    const st = window.getComputedStyle(el);
    const declared = st.width;
    const minW = st.minWidth;
    const px = declared.endsWith("px") ? parseFloat(declared) : NaN;
    const minPx = minW.endsWith("px") ? parseFloat(minW) : NaN;
    const used = Math.max(px || 0, minPx || 0);
    if (used > vw * 1.25 && used >= 500) {
      fixedWidth.push({ selector: safeSel(el), width: Math.round(used) });
    }
  }

  const smallText = [];
  const clippedText = [];
  const textNodes = Array.from(document.querySelectorAll("p, li, span, a, button, label, h1, h2, h3, h4, td, th")).slice(0, 220);
  for (const el of textNodes) {
    if (!visible(el)) continue;
    const sample = textOf(el);
    if (sample.length < 8) continue;
    const st = window.getComputedStyle(el);
    const size = parseFloat(st.fontSize) || 0;
    if (size && size < minFont && sample.length > 20) {
      smallText.push({ selector: safeSel(el), font_size: size, text: sample.slice(0, 80) });
    }
    const isClip = st.overflow === "hidden" || st.overflowY === "hidden" || st.overflowX === "hidden" || st.textOverflow === "ellipsis";
    if (isClip && (el.scrollHeight > el.clientHeight + 6 || el.scrollWidth > el.clientWidth + 8) && sample.length > 16) {
      const tag = (el.tagName || "").toLowerCase();
      if (tag === "p" || tag === "h1" || tag === "h2" || tag === "h3" || tag === "li") {
        clippedText.push({ selector: safeSel(el), text: sample.slice(0, 80) });
      }
    }
  }

  const emptySections = [];
  const sectionEls = Array.from(document.querySelectorAll("section, article, main > div")).slice(0, 40);
  for (const el of sectionEls) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.height < 180 || r.width < 180) continue;
    const hasMedia = el.querySelector("img, svg, video, canvas, iframe, form, button, input, a");
    const copy = textOf(el);
    if (!hasMedia && copy.length < 2 && el.children.length <= 1) {
      emptySections.push({ selector: safeSel(el) });
    }
  }

  const overlayKeywords = /cookie|privacy|subscribe|newsletter|sign up|login|sign in|consent/;
  const overlays = [];
  const overlayEls = Array.from(document.querySelectorAll("div, aside, section, dialog")).slice(0, 180);
  for (const el of overlayEls) {
    const st = window.getComputedStyle(el);
    if (st.position !== "fixed" && st.position !== "sticky" && st.position !== "absolute") continue;
    if (!visible(el)) continue;
    const z = parseInt(st.zIndex, 10);
    if (!Number.isNaN(z) && z < 10) continue;
    const cov = coverage(el);
    if (cov < 0.35) continue;
    const sample = textOf(el).slice(0, 160);
    overlays.push({
      selector: safeSel(el),
      coverage: Math.round(cov * 100) / 100,
      keywords: overlayKeywords.test(sample.toLowerCase()),
      text: sample
    });
  }

  const overlapping = [];
  const overlapCandidates = Array.from(document.querySelectorAll("p, h1, h2, h3, button, a, label, li")).filter((el) => {
    if (!visible(el) || !inFirstScreen(el)) return false;
    if (el.closest("nav, header, footer")) return false;
    const r = el.getBoundingClientRect();
    return r.width * r.height >= 500 && textOf(el).length > 8;
  }).slice(0, 30);
  for (let i = 0; i < overlapCandidates.length; i += 1) {
    for (let j = i + 1; j < overlapCandidates.length; j += 1) {
      const a = overlapCandidates[i];
      const b = overlapCandidates[j];
      if (a.contains(b) || b.contains(a)) continue;
      const ar = a.getBoundingClientRect();
      const br = b.getBoundingClientRect();
      const ix = Math.max(0, Math.min(ar.right, br.right) - Math.max(ar.left, br.left));
      const iy = Math.max(0, Math.min(ar.bottom, br.bottom) - Math.max(ar.top, br.top));
      const inter = ix * iy;
      const smaller = Math.min(ar.width * ar.height, br.width * br.height);
      if (inter > 250 && smaller > 0 && inter / smaller > 0.45) {
        overlapping.push({
          a: safeSel(a),
          b: safeSel(b),
          intersection_px: Math.round(inter)
        });
      }
      if (overlapping.length >= 6) break;
    }
    if (overlapping.length >= 6) break;
  }

  const mainEl = document.querySelector("main, [role='main'], #main, #content, .main, .content") || document.body;
  const mainVisible = !!(mainEl && visible(mainEl) && (textOf(mainEl).length > 20 || mainEl.querySelector("img, h1, p, a")));

  const offscreen = [];
  const critical = Array.from(document.querySelectorAll("h1, nav, form, button, [role='button']")).slice(0, 40);
  for (const el of critical) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.right < -20 || r.left > vw + 20) {
      offscreen.push({ selector: safeSel(el), left: Math.round(r.left) });
    }
  }

  const disabledPrimary = buttons.filter((b) => b.disabled && b.in_viewport && b.width * b.height >= 2000);

  return {
    viewport: { width: vw, height: vh },
    page: { ready_state: document.readyState },
    layout: {
      scroll_width: scrollWidth,
      scroll_height: scrollHeight,
      viewport_width: vw,
      viewport_height: vh,
      horizontal_overflow: horizontalOverflow,
      overflow_px: Math.round(overflowPx)
    },
    navigation: {
      exists: !!(navEl || navLinks.length >= 3),
      has_nav_element: !!navEl,
      visible: navVisible || (navLinks.length > 0 && navLinks.some((a) => inFirstScreen(a))),
      links: navLinks.length,
      overflow: navOverflow,
      overflow_px: Math.round(navOverflowPx),
      overflow_selector: navOverflowSel,
      menu_button: menuBtn ? safeSel(menuBtn) : null,
      logo
    },
    content: {
      h1: headings.length,
      h1_visible: h1Visible,
      paragraphs: paragraphs.length
    },
    interactive: {
      buttons: buttons.length,
      links: links.length,
      forms: forms.length
    },
    typography: {
      small_count: smallText.length,
      clipped_count: clippedText.length
    },
    images,
    forms,
    overlays,
    overflowing_elements: overflowing.slice(0, 8),
    fixed_width_elements: fixedWidth.slice(0, 8),
    overlapping_pairs: overlapping,
    clipped_text: clippedText.slice(0, 6),
    small_text: smallText.slice(0, 6),
    empty_sections: emptySections.slice(0, 4),
    offscreen_critical: offscreen.slice(0, 6),
    cta: {
      exists: !!primary,
      selector: primary ? primary.selector : null,
      text: primary ? primary.text : null,
      visible: primary ? !!primary.visible : false,
      in_viewport: primary ? !!primary.in_viewport : false,
      clipped: primary ? !!primary.clipped : false,
      overflow_px: primary ? primary.overflow_px || 0 : 0
    },
    main: {
      exists: !!mainEl,
      visible: mainVisible,
      selector: mainEl ? safeSel(mainEl) : null
    },
    load: {
      ready_state: document.readyState,
      main_visible: mainVisible
    },
    buttons,
    links: links.slice(0, 40),
    headings,
    disabled_primary: disabledPrimary
  };
}"""


def measurement_script(
    overflow_tolerance_px: int = OVERFLOW_TOLERANCE_PX,
    min_font_px: float = MIN_FONT_PX,
) -> str:
    return MEASURE_JS.replace("__OVERFLOW_TOL__", str(int(overflow_tolerance_px))).replace(
        "__MIN_FONT__", str(float(min_font_px))
    )


def _clean_elements(items: list[dict] | None) -> list[dict]:
    cleaned: list[dict] = []
    for item in items or []:
        row = dict(item)
        if "selector" in row:
            row["selector"] = sanitize_selector(row.get("selector"))
        if "a" in row:
            row["a"] = sanitize_selector(row.get("a"))
        if "b" in row:
            row["b"] = sanitize_selector(row.get("b"))
        if "overflow_selector" in row:
            row["overflow_selector"] = sanitize_selector(row.get("overflow_selector"))
        if "text" in row:
            row["text"] = sanitize_text(row.get("text"))
        cleaned.append(row)
    return cleaned


def normalize_snapshot(
    raw: dict,
    *,
    viewport_name: str,
    width: int,
    height: int,
    url: str,
    final_url: str,
) -> ViewportSnapshot:
    data = dict(raw or {})
    data["viewport"] = {
        "name": viewport_name,
        "width": int((raw.get("viewport") or {}).get("width") or width),
        "height": int((raw.get("viewport") or {}).get("height") or height),
    }
    data["page"] = {
        "url": url,
        "final_url": final_url,
        "ready_state": (raw.get("page") or raw.get("load") or {}).get("ready_state"),
    }
    nav = dict(data.get("navigation") or {})
    if nav.get("overflow_selector"):
        nav["overflow_selector"] = sanitize_selector(nav.get("overflow_selector"))
    logo = nav.get("logo") or {}
    if isinstance(logo, dict) and logo.get("selector"):
        logo = dict(logo)
        logo["selector"] = sanitize_selector(logo.get("selector"))
        nav["logo"] = logo
    if nav.get("menu_button"):
        nav["menu_button"] = sanitize_selector(nav.get("menu_button"))
    data["navigation"] = nav
    cta = dict(data.get("cta") or {})
    cta["selector"] = sanitize_selector(cta.get("selector"))
    cta["text"] = sanitize_text(cta.get("text"), 80)
    data["cta"] = cta
    main = dict(data.get("main") or {})
    main["selector"] = sanitize_selector(main.get("selector"))
    data["main"] = main
    for key in (
        "overflowing_elements",
        "fixed_width_elements",
        "overlapping_pairs",
        "clipped_text",
        "small_text",
        "empty_sections",
        "offscreen_critical",
        "images",
        "forms",
        "overlays",
        "buttons",
        "links",
        "headings",
        "disabled_primary",
    ):
        if key in data:
            data[key] = _clean_elements(data.get(key) if isinstance(data.get(key), list) else [])
    return ViewportSnapshot.model_validate(data)
