import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  categoryStatusLabel,
  containsForbiddenHealthClaims,
  coverageLabel,
  emptyHealthCopy,
  HEALTH_COVERAGE_NOTE,
  HEALTH_SCORE_NOTE,
  scoreOutOf100,
  weightPercent,
} from "./score-ui";

describe("Health Score UI helpers", () => {
  it("labels coverage, category status, and unavailable scores", () => {
    assert.equal(coverageLabel("complete"), "Complete");
    assert.equal(coverageLabel("partial"), "Partial");
    assert.equal(coverageLabel("limited"), "Limited");
    assert.equal(categoryStatusLabel("available"), "Available");
    assert.equal(categoryStatusLabel("failed"), "Failed");
    assert.equal(scoreOutOf100(82), "82 out of 100");
    assert.equal(scoreOutOf100(null), "Unavailable");
    assert.equal(weightPercent(15), "15%");
    assert.equal(weightPercent(7.5), "7.5%");
  });

  it("returns methodology copy and empty states", () => {
    assert.match(HEALTH_SCORE_NOTE, /not a prediction of search rankings/i);
    assert.match(HEALTH_COVERAGE_NOTE, /not a statistical confidence interval/i);
    assert.equal(emptyHealthCopy("unavailable").title, "Health score unavailable");
    assert.match(emptyHealthCopy("incomplete").title, /Calculating Health Score/);
    assert.match(emptyHealthCopy("loading").title, /Loading Health Score/);
  });

  it("does not use ranking, traffic, revenue, or trustworthiness claims", () => {
    const copy = [HEALTH_SCORE_NOTE, HEALTH_COVERAGE_NOTE, emptyHealthCopy("unavailable").body].join(" ");
    assert.equal(containsForbiddenHealthClaims(copy), false);
    assert.equal(containsForbiddenHealthClaims("Predicted traffic will increase."), true);
    assert.equal(containsForbiddenHealthClaims("This company is trustworthy."), true);
  });
});
