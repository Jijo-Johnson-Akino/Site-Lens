import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { hierarchicalLayout } from "./architecture-layout";
import {
  architectureFlags,
  crawlDepthLabel,
  graphLimitMessage,
  nodeTone,
  urlPathDepthLabel,
} from "./architecture-ui";

describe("architecture UI helpers", () => {
  it("keeps crawl depth and URL path depth as separate labels", () => {
    assert.equal(crawlDepthLabel(1), "Depth 1");
    assert.equal(crawlDepthLabel(null), "Unknown");
    assert.equal(urlPathDepthLabel(2), "2");
    assert.equal(urlPathDepthLabel(undefined), "Unknown");
  });

  it("labels potential orphans and terminal pages without ranking", () => {
    assert.deepEqual(
      architectureFlags({ potential_orphan: true, terminal_page: false, dead_end: false }),
      ["Potential orphan page"],
    );
    assert.deepEqual(
      architectureFlags({ potential_orphan: false, terminal_page: true, dead_end: false }),
      ["Terminal page"],
    );
    assert.deepEqual(
      architectureFlags({ potential_orphan: false, terminal_page: false, dead_end: true }),
      ["Internal-link dead end"],
    );
  });

  it("uses issue and crawl states for node tone, not importance", () => {
    assert.equal(nodeTone({ crawl_status: "failed", issue_count: 0, potential_orphan: false }), "failed");
    assert.equal(
      nodeTone({ crawl_status: "crawled", issue_count: 2, severity_counts: { high: 1 }, potential_orphan: false }),
      "critical",
    );
    assert.equal(
      nodeTone({ crawl_status: "crawled", issue_count: 1, severity_counts: { low: 1 }, potential_orphan: false }),
      "warn",
    );
    assert.equal(nodeTone({ crawl_status: "crawled", issue_count: 0, potential_orphan: true }), "orphan");
    assert.equal(nodeTone({ crawl_status: "crawled", issue_count: 0, potential_orphan: false }), "default");
  });

  it("discloses graph limits", () => {
    assert.equal(graphLimitMessage(100, 250, true), "Showing 100 of 250 crawled pages.");
    assert.equal(graphLimitMessage(42, 42, false), null);
  });

  it("lays out nodes by crawl depth deterministically", () => {
    const positions = hierarchicalLayout([
      { id: "home", depth: 0, inbound: 0, url: "https://example.com/" },
      { id: "about", depth: 1, inbound: 2, url: "https://example.com/about" },
      { id: "blog", depth: 1, inbound: 1, url: "https://example.com/blog" },
      { id: "post", depth: 2, inbound: 1, url: "https://example.com/blog/post" },
    ]);
    assert.equal(positions.home.y < positions.about.y, true);
    assert.equal(positions.about.y, positions.blog.y);
    assert.equal(positions.about.x < positions.blog.x, true);
    assert.equal(positions.post.y > positions.about.y, true);
    const again = hierarchicalLayout([
      { id: "post", depth: 2, inbound: 1, url: "https://example.com/blog/post" },
      { id: "blog", depth: 1, inbound: 1, url: "https://example.com/blog" },
      { id: "about", depth: 1, inbound: 2, url: "https://example.com/about" },
      { id: "home", depth: 0, inbound: 0, url: "https://example.com/" },
    ]);
    assert.deepEqual(positions, again);
  });
});
