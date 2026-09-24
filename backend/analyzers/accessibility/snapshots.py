"""Collect accessibility-related DOM facts in one Playwright evaluate."""

from __future__ import annotations

from backend.analyzers.accessibility.models import AccessibleSnapshot
from backend.analyzers.uiux.sanitizer import sanitize_selector, sanitize_text

COLLECT_JS = r"""() => {
  function visible(el) {
    if (!el || el.nodeType !== 1) return false;
    const st = getComputedStyle(el);
    if (!st || st.display === "none" || st.visibility === "hidden") return false;
    const r = el.getBoundingClientRect();
    return r.width >= 1 && r.height >= 1;
  }
  function safeSel(el) {
    if (!el || el === document.documentElement) return "html";
    if (el === document.body) return "body";
    const tag = (el.tagName || "div").toLowerCase();
    let id = "";
    if (el.id && /^[A-Za-z][\w-]{0,40}$/.test(el.id) && !/@/.test(el.id)) id = "#" + el.id;
    const raw = typeof el.className === "string" ? el.className : "";
    const parts = raw.trim().split(/\s+/).filter((c) => /^[A-Za-z][\w-]{0,24}$/.test(c)).slice(0, 2);
    const cls = parts.length ? "." + parts.join(".") : "";
    return (tag + id + cls).slice(0, 72);
  }
  function accName(el) {
    const labelled = el.getAttribute("aria-labelledby");
    if (labelled) {
      const text = labelled.split(/\s+/).map((id) => (document.getElementById(id) || {}).innerText || "").join(" ").trim();
      if (text) return text;
    }
    return (el.getAttribute("aria-label") || el.getAttribute("alt") || el.getAttribute("title") || el.innerText || el.getAttribute("value") || "").replace(/\s+/g, " ").trim();
  }
  function hasAccName(el) {
    return accName(el).length > 0;
  }

  const html = document.documentElement;
  const langPresent = html.hasAttribute("lang") || html.hasAttribute("xml:lang");
  const lang = (html.getAttribute("lang") || html.getAttribute("xml:lang") || "").trim();
  const dir = (html.getAttribute("dir") || document.body.getAttribute("dir") || "").trim().toLowerCase();
  const title = (document.title || "").trim();
  const viewport = document.querySelector('meta[name="viewport"]');
  const viewportContent = viewport ? (viewport.getAttribute("content") || "") : "";

  const mains = Array.from(document.querySelectorAll("main, [role='main']"));
  const navs = Array.from(document.querySelectorAll("nav, [role='navigation']"));
  const headers = Array.from(document.querySelectorAll("header, [role='banner']"));
  const footers = Array.from(document.querySelectorAll("footer, [role='contentinfo']"));
  const unnamedNavs = navs.filter((el) => !el.getAttribute("aria-label") && !el.getAttribute("aria-labelledby"));
  const emptyLandmarks = [];
  for (const el of [...mains, ...navs, ...headers, ...footers].slice(0, 20)) {
    const text = (el.innerText || "").trim();
    if (visible(el) && text.length < 1 && !el.querySelector("a, button, img, input, svg")) {
      emptyLandmarks.push(safeSel(el));
    }
  }

  const headings = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6")).slice(0, 40).map((el) => ({
    level: Number((el.tagName || "H1").slice(1)),
    selector: safeSel(el),
    text: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 120),
    empty: !accName(el),
    hidden: el.getAttribute("aria-hidden") === "true"
  }));

  const images = Array.from(document.querySelectorAll("img")).slice(0, 60).map((el) => ({
    selector: safeSel(el),
    alt: el.getAttribute("alt"),
    has_alt: el.hasAttribute("alt"),
    in_link: !!(el.closest("a") || el.closest("button")),
    visible: visible(el)
  }));
  const imageInputs = Array.from(document.querySelectorAll("input[type='image']")).slice(0, 10).map((el) => ({
    selector: safeSel(el),
    alt: el.getAttribute("alt") || "",
    named: hasAccName(el)
  }));

  const links = Array.from(document.querySelectorAll("a")).slice(0, 80).map((el) => ({
    selector: safeSel(el),
    href: el.getAttribute("href"),
    name: accName(el).slice(0, 80),
    named: hasAccName(el),
    visible: visible(el)
  }));

  const controls = Array.from(document.querySelectorAll("button, [role='button'], input[type='button'], input[type='submit'], input[type='reset']")).slice(0, 60).map((el) => ({
    selector: safeSel(el),
    name: accName(el).slice(0, 80),
    named: hasAccName(el),
    disabled: !!(el.disabled || el.getAttribute("aria-disabled") === "true"),
    visible: visible(el)
  }));

  const fieldEls = Array.from(document.querySelectorAll("input, select, textarea")).filter((el) => {
    const type = (el.getAttribute("type") || "text").toLowerCase();
    return type !== "hidden" && type !== "submit" && type !== "button" && type !== "reset" && type !== "image";
  }).slice(0, 50);
  const fields = fieldEls.map((el) => {
    const id = el.id;
    const label = id ? document.querySelector("label[for='" + CSS.escape(id) + "']") : null;
    return {
      selector: safeSel(el),
      named: !!(label || el.closest("label") || hasAccName(el) || el.getAttribute("aria-label") || el.getAttribute("title")),
      required: el.required || el.getAttribute("aria-required") === "true",
      type: (el.getAttribute("type") || el.tagName || "").toLowerCase()
    };
  });
  const forms = Array.from(document.querySelectorAll("form")).slice(0, 12).map((form) => {
    const submit = form.querySelector("button[type='submit'], input[type='submit'], button:not([type])");
    return {
      selector: safeSel(form),
      has_submit: !!submit,
      submit_named: submit ? hasAccName(submit) : false,
      fieldsets: form.querySelectorAll("fieldset legend").length
    };
  });
  const radios = Array.from(document.querySelectorAll("input[type='radio']"));
  const radioNames = {};
  for (const el of radios) {
    const n = el.getAttribute("name") || "";
    if (!n) continue;
    radioNames[n] = (radioNames[n] || 0) + 1;
  }

  const ids = {};
  const dupes = [];
  for (const el of Array.from(document.querySelectorAll("[id]")).slice(0, 400)) {
    const id = el.id;
    if (!id) continue;
    ids[id] = (ids[id] || 0) + 1;
  }
  for (const [id, count] of Object.entries(ids)) {
    if (count > 1) dupes.push(id.slice(0, 40));
  }

  const brokenRefs = [];
  for (const el of Array.from(document.querySelectorAll("[aria-labelledby], [aria-describedby]")).slice(0, 80)) {
    const refs = ((el.getAttribute("aria-labelledby") || "") + " " + (el.getAttribute("aria-describedby") || "")).trim().split(/\s+/).filter(Boolean);
    for (const ref of refs) {
      if (!document.getElementById(ref)) brokenRefs.push({ selector: safeSel(el), ref: ref.slice(0, 40) });
    }
  }

  const hiddenFocusable = [];
  for (const root of Array.from(document.querySelectorAll("[aria-hidden='true']")).slice(0, 40)) {
    const inner = root.querySelector("a[href], button, input, select, textarea, [tabindex]");
    if (inner) hiddenFocusable.push(safeSel(inner));
  }

  const positiveTab = Array.from(document.querySelectorAll("[tabindex]")).filter((el) => {
    const n = Number(el.getAttribute("tabindex"));
    return Number.isFinite(n) && n > 0;
  }).slice(0, 20).map(safeSel);

  const tables = Array.from(document.querySelectorAll("table")).slice(0, 12).map((el) => ({
    selector: safeSel(el),
    headers: el.querySelectorAll("th").length,
    caption: !!(el.querySelector("caption") && (el.querySelector("caption").innerText || "").trim()),
    role: el.getAttribute("role") || ""
  }));

  const iframes = Array.from(document.querySelectorAll("iframe")).slice(0, 12).map((el) => ({
    selector: safeSel(el),
    title: (el.getAttribute("title") || el.getAttribute("aria-label") || "").trim(),
    named: hasAccName(el) || !!(el.getAttribute("title") || "").trim()
  }));

  const dialogs = Array.from(document.querySelectorAll("dialog, [role='dialog'], [role='alertdialog']")).slice(0, 10).map((el) => ({
    selector: safeSel(el),
    named: hasAccName(el),
    open: el.tagName === "DIALOG" ? el.open : visible(el)
  }));

  const media = Array.from(document.querySelectorAll("video, audio")).slice(0, 10).map((el) => ({
    selector: safeSel(el),
    kind: (el.tagName || "").toLowerCase(),
    controls: el.hasAttribute("controls"),
    tracks: el.querySelectorAll("track").length
  }));

  const skip = Array.from(document.querySelectorAll("a[href^='#']")).find((el) => /skip/i.test(accName(el) + (el.getAttribute("href") || "")));
  const live = Array.from(document.querySelectorAll("[aria-live], [role='status'], [role='alert'], [role='log']")).slice(0, 10).map((el) => ({
    selector: safeSel(el),
    live: el.getAttribute("aria-live") || el.getAttribute("role")
  }));

  const focusable = Array.from(document.querySelectorAll("a[href], button, input, select, textarea, [tabindex]:not([tabindex='-1'])")).filter(visible).length;

  return {
    page: { ready_state: document.readyState },
    document: { lang, dir, title, lang_present: langPresent },
    landmarks: {
      main: mains.length,
      nav: navs.length,
      header: headers.length,
      footer: footers.length,
      unnamed_navs: unnamedNavs.length,
      empty: emptyLandmarks
    },
    headings,
    images,
    image_inputs: imageInputs,
    links,
    controls,
    fields,
    forms,
    radio_groups: Object.keys(radioNames).length,
    radio_groups_without_fieldset: Object.keys(radioNames).filter((name) => {
      const el = document.querySelector("input[type='radio'][name='" + CSS.escape(name) + "']");
      return el && !el.closest("fieldset");
    }).length,
    aria: { broken_refs: brokenRefs.slice(0, 8), hidden_focusable: hiddenFocusable.slice(0, 8) },
    ids: { duplicates: dupes.slice(0, 8) },
    tables,
    iframes,
    dialogs,
    media,
    focus: { tabindex_positive: positiveTab, hidden_focusable: hiddenFocusable, focusable_count: focusable },
    viewport_meta: { content: viewportContent, present: !!viewport },
    skip: { exists: !!skip, selector: skip ? safeSel(skip) : null },
    live
  };
}"""


def _clean(items: list[dict] | None) -> list[dict]:
    cleaned: list[dict] = []
    for item in items or []:
        row = dict(item)
        if "selector" in row:
            row["selector"] = sanitize_selector(row.get("selector"))
        if "text" in row:
            row["text"] = sanitize_text(row.get("text"))
        if "name" in row:
            row["name"] = sanitize_text(row.get("name"), 80)
        cleaned.append(row)
    return cleaned


def normalize_snapshot(raw: dict, *, url: str, final_url: str) -> AccessibleSnapshot:
    data = dict(raw or {})
    data["page"] = {**(data.get("page") or {}), "url": url, "final_url": final_url}
    for key in ("headings", "images", "image_inputs", "links", "controls", "fields", "forms", "tables", "iframes", "dialogs", "media", "live"):
        if key in data and isinstance(data[key], list):
            data[key] = _clean(data[key])
    aria = dict(data.get("aria") or {})
    if aria.get("broken_refs"):
        aria["broken_refs"] = _clean(aria.get("broken_refs"))
    data["aria"] = aria
    return AccessibleSnapshot.model_validate(data)
