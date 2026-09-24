import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  authorSummary,
  categoryLabel,
  checkStatusLabel,
  containsForbiddenTrustClaims,
  emptyTrustCopy,
  filterFindings,
  passedSignalMessages,
  policyDetectedLabel,
  scoreLabel,
  TRUST_CRAWL_NOTE,
  TRUST_METHODOLOGY,
  TRUST_SCORE_NOTE,
} from "./trust-ui";

describe("Trust UI helpers", () => {
  it("labels statuses, categories, and unavailable scores", () => {
    assert.equal(checkStatusLabel("pass"), "Pass");
    assert.equal(checkStatusLabel("warning"), "Warning");
    assert.equal(checkStatusLabel("fail"), "Fail");
    assert.equal(checkStatusLabel("not_applicable"), "N/A");
    assert.equal(categoryLabel("identity"), "Identity");
    assert.equal(categoryLabel("social_proof"), "Social Proof");
    assert.equal(scoreLabel(78), "78");
    assert.equal(scoreLabel(null), "Unavailable");
    assert.equal(scoreLabel(undefined), "Unavailable");
  });

  it("returns methodology, crawl note, and empty-state copy", () => {
    assert.match(TRUST_METHODOLOGY, /does not verify the truth/i);
    assert.match(TRUST_CRAWL_NOTE, /outside the SiteLens crawl scope/i);
    assert.match(TRUST_SCORE_NOTE, /not a legitimacy/i);
    assert.equal(emptyTrustCopy("unavailable").title, "Trust & Credibility analysis unavailable.");
    assert.match(emptyTrustCopy("incomplete").title, /Running Trust/);
    assert.match(emptyTrustCopy("loading").title, /Loading Trust/);
  });

  it("filters findings and summarizes authors and policies", () => {
    const rows = [
      { name: "About page", group: "transparency", status: "warning", severity: "low", message: "No dedicated About page was detected within the crawled pages.", page_url: "https://example.com/", recommendation: null },
      { name: "HTTPS", group: "security", status: "pass", severity: "info", message: "HTTPS enabled.", page_url: "https://example.com/", recommendation: null },
    ];
    assert.equal(filterFindings(rows, { status: "warning" }).length, 1);
    assert.equal(filterFindings(rows, { query: "HTTPS enabled" }).length, 1);
    assert.match(authorSummary([{ author: "Ada", publication_date: "2026-01-01" }, { author: null, publication_date: null }]), /2 articles analyzed/);
    assert.equal(policyDetectedLabel(false), "Not detected within crawl");
    assert.equal(policyDetectedLabel(true, "Detected"), "Detected");
    assert.deepEqual(
      passedSignalMessages(
        [
          { group: "security", status: "pass", message: "HTTPS enabled." },
          { group: "security", status: "not_applicable", message: "No payment provider branding was detected." },
        ],
        "security",
      ),
      ["HTTPS enabled."],
    );
  });

  it("does not use legitimacy, safety, or legal-compliance claims", () => {
    const copy = [TRUST_METHODOLOGY, TRUST_SCORE_NOTE, TRUST_CRAWL_NOTE, emptyTrustCopy("unavailable").body].join(" ");
    assert.equal(containsForbiddenTrustClaims(copy), false);
    assert.equal(containsForbiddenTrustClaims("This company is trustworthy."), true);
    assert.equal(containsForbiddenTrustClaims("Website is secure."), true);
    assert.equal(containsForbiddenTrustClaims("GDPR compliant"), true);
  });
});
