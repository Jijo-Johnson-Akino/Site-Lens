import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  ACTION_PLAN_INTRO,
  analyzerHref,
  bandCounts,
  emptyActionPlanCopy,
  groupActionsByPriority,
  pagesHref,
  priorityGroupLabel,
} from "./action-plan-ui";
import type { RecommendationListItem } from "./api";

function rec(partial: Partial<RecommendationListItem> & { id: string; priority: RecommendationListItem["priority"] }): RecommendationListItem {
  return {
    recommendation_key: partial.id,
    title: partial.title || partial.id,
    summary: "summary",
    category: "SEO",
    impact: "high",
    effort: "small",
    status: "open",
    affected_page_count: 1,
    affected_element_count: 0,
    issue_count: 1,
    issue_keys: ["seo.title.missing"],
    source_kind: "issues",
    ...partial,
  };
}

describe("action plan helpers", () => {
  it("groups by existing recommendation priority", () => {
    const groups = groupActionsByPriority([
      rec({ id: "a", priority: "high" }),
      rec({ id: "b", priority: "low" }),
      rec({ id: "c", priority: "high" }),
    ]);
    assert.deepEqual(
      groups.map((group) => [group.id, group.items.length]),
      [
        ["high", 2],
        ["low", 1],
      ],
    );
    assert.equal(priorityGroupLabel("high"), "High Priority");
    assert.match(ACTION_PLAN_INTRO, /Prioritized actions/);
  });

  it("counts high as critical plus high", () => {
    const bands = bandCounts({
      total: 10,
      open: 4,
      in_progress: 2,
      completed: 3,
      dismissed: 1,
      high_priority: 5,
      critical: 1,
      high: 4,
      medium: 3,
      low: 2,
      info: 0,
      by_category: {},
      by_priority: {},
      by_status: {},
      high_priority_by_category: {},
    });
    assert.equal(bands.high, 5);
    assert.equal(bands.medium, 3);
    assert.equal(bands.low, 2);
  });

  it("links actions to pages and analyzers", () => {
    assert.equal(pagesHref("scan_1", ["page_a"]), "/scan/scan_1/pages/page_a");
    assert.equal(pagesHref("scan_1", ["page_a", "page_b"]), "/scan/scan_1/pages");
    assert.equal(analyzerHref("scan_1", "SEO"), "/scan/scan_1/seo");
    assert.equal(emptyActionPlanCopy("none").title, "No actions were generated from the detected findings.");
  });
});
