import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  emptyRecommendationsCopy,
  issuesHref,
  RECOMMENDATION_CATEGORIES,
  RECOMMENDATION_METHODOLOGY,
  statusLabel,
  titleCase,
} from "./recommendations-ui";

describe("recommendations UI helpers", () => {
  it("labels statuses and title-cases values", () => {
    assert.equal(statusLabel("open"), "Open");
    assert.equal(statusLabel("in_progress"), "In Progress");
    assert.equal(statusLabel("completed"), "Completed");
    assert.equal(titleCase("structured_data"), "Structured Data");
  });

  it("returns empty-state copy", () => {
    assert.equal(emptyRecommendationsCopy("none").title, "No recommendations generated.");
    assert.equal(emptyRecommendationsCopy("filters").title, "No recommendations match your filters.");
    assert.match(emptyRecommendationsCopy("incomplete").title, /after analysis/i);
  });

  it("builds issue links from ids or keys", () => {
    assert.equal(issuesHref("scan_1", ["issue_a", "issue_b"], []), "/scan/scan_1/issues?issue_ids=issue_a%2Cissue_b");
    assert.equal(issuesHref("scan_1", [], ["seo.title.missing"]), "/scan/scan_1/issues?issue_key=seo.title.missing");
    assert.equal(issuesHref("scan_1", [], []), "/scan/scan_1/issues");
  });

  it("includes methodology and architecture in categories", () => {
    assert.match(RECOMMENDATION_METHODOLOGY, /do not guarantee/i);
    assert.ok(RECOMMENDATION_CATEGORIES.includes("Architecture"));
    assert.ok(RECOMMENDATION_CATEGORIES.includes("CRO"));
    assert.ok(RECOMMENDATION_CATEGORIES.includes("Trust"));
  });
});
