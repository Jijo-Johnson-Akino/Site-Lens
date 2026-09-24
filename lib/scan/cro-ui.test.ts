import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  categoryLabel,
  checkStatusLabel,
  containsForbiddenCroClaims,
  conversionPathCopy,
  CRO_CRAWL_NOTE,
  CRO_METHODOLOGY,
  CRO_SCORE_NOTE,
  emptyCroCopy,
  filterFindings,
  scoreLabel,
} from "./cro-ui";

describe("CRO UI helpers", () => {
  it("labels statuses, categories, and unavailable scores", () => {
    assert.equal(checkStatusLabel("pass"), "Pass");
    assert.equal(checkStatusLabel("warning"), "Warning");
    assert.equal(checkStatusLabel("fail"), "Fail");
    assert.equal(checkStatusLabel("not_applicable"), "N/A");
    assert.equal(categoryLabel("primary_cta"), "Primary CTA");
    assert.equal(categoryLabel("value_proposition"), "Value Proposition");
    assert.equal(scoreLabel(78), "78");
    assert.equal(scoreLabel(null), "Unavailable");
    assert.equal(scoreLabel(undefined), "Unavailable");
  });

  it("returns methodology, crawl note, and empty-state copy", () => {
    assert.match(CRO_METHODOLOGY, /does not measure actual conversion rates/i);
    assert.match(CRO_CRAWL_NOTE, /observable within the SiteLens crawl/i);
    assert.match(CRO_SCORE_NOTE, /observable conversion-related website signals/i);
    assert.equal(emptyCroCopy("unavailable").title, "CRO analysis unavailable.");
    assert.match(emptyCroCopy("incomplete").title, /Running CRO Analysis/);
    assert.match(emptyCroCopy("loading").title, /Loading CRO results/);
  });

  it("filters findings by status, severity, and search", () => {
    const rows = [
      { name: "Primary CTA not visible", group: "primary_cta", status: "fail", severity: "high", message: "Not in viewport", page_url: "https://example.com/", recommendation: "Keep visible" },
      { name: "Form length", group: "forms", status: "warning", severity: "medium", message: "Form contains 8 fields", page_url: "https://example.com/contact", recommendation: null },
      { name: "CTA wording", group: "cta_clarity", status: "pass", severity: "low", message: "Labels describe an action", page_url: "https://example.com/", recommendation: null },
    ];
    assert.equal(filterFindings(rows, { status: "fail" }).length, 1);
    assert.equal(filterFindings(rows, { severity: "medium" })[0].name, "Form length");
    assert.equal(filterFindings(rows, { query: "viewport" }).length, 1);
    assert.equal(filterFindings(rows, { query: "missing" }).length, 0);
  });

  it("renders conversion paths from crawled nodes only", () => {
    assert.equal(
      conversionPathCopy([
        { page_type: "homepage", url: "https://example.com/" },
        { page_type: "contact", url: "https://example.com/contact" },
      ]),
      "homepage → contact",
    );
    assert.equal(conversionPathCopy([], null), "No conversion path could be determined from the crawled links.");
  });

  it("does not use conversion-rate or revenue claims", () => {
    const copy = [CRO_METHODOLOGY, CRO_SCORE_NOTE, CRO_CRAWL_NOTE, emptyCroCopy("unavailable").body].join(" ");
    assert.equal(containsForbiddenCroClaims(copy), false);
    assert.equal(containsForbiddenCroClaims("Conversion probability 12%"), true);
    assert.equal(containsForbiddenCroClaims("guaranteed sales increase"), true);
  });
});
