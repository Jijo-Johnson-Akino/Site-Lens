import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  crawlStatusLabel,
  httpLabel,
  indexableLabel,
  pageTitle,
  scoreLabel,
} from "./pages-ui";

describe("pages UI helpers", () => {
  it("uses Untitled page when title is missing", () => {
    assert.equal(pageTitle(null), "Untitled page");
    assert.equal(pageTitle("  "), "Untitled page");
    assert.equal(pageTitle("Homepage"), "Homepage");
  });

  it("labels crawl status, HTTP, indexability, and scores", () => {
    assert.equal(crawlStatusLabel("crawled"), "Crawled");
    assert.equal(crawlStatusLabel("failed"), "Failed");
    assert.equal(crawlStatusLabel("skipped"), "Skipped");
    assert.equal(httpLabel(200), "200");
    assert.equal(httpLabel(null), "—");
    assert.equal(indexableLabel(true), "Indexable");
    assert.equal(indexableLabel(false), "Noindex");
    assert.equal(indexableLabel(null), "Unknown");
    assert.equal(scoreLabel(82), "82");
    assert.equal(scoreLabel(null), "Not analyzed");
  });
});
