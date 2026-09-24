import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  barWidth,
  COMPETITOR_LIMITATIONS,
  COMPETITOR_METHODOLOGY,
  competitorStatusLabel,
  displayCell,
  emptyCompetitorsCopy,
} from "./competitors-ui";

describe("competitors UI helpers", () => {
  it("labels statuses and empty copy", () => {
    assert.equal(competitorStatusLabel("scanning"), "Scanning");
    assert.equal(competitorStatusLabel("failed"), "Failed");
    assert.equal(emptyCompetitorsCopy("none").title, "No competitor websites have been added to this scan.");
    assert.match(emptyCompetitorsCopy("incomplete").title, /update when the competitor scan completes/i);
  });

  it("does not treat unavailable values as zero", () => {
    assert.equal(displayCell(false, 0), "Unavailable");
    assert.equal(displayCell(true, 82), "82");
    assert.equal(barWidth(50, 100), 50);
    assert.equal(barWidth(null, 100), 0);
  });

  it("includes methodology limitations", () => {
    assert.match(COMPETITOR_METHODOLOGY, /independently crawled/i);
    assert.match(COMPETITOR_LIMITATIONS, /should not be interpreted as search rankings/i);
  });
});
