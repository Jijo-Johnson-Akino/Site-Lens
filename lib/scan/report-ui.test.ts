import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  compactCategoryLabel,
  containsForbiddenReportClaims,
  crawledPageSlices,
  classifyPageItem,
  displayScore,
  displayScoreOutOf100,
  emptyReportCopy,
  formatPercent,
  formatReportDate,
  headerStatusLabel,
  metricOrUnavailable,
  previousScanDelta,
  recommendationCategoryRows,
  REPORT_SECTIONS,
  reportStatusLabel,
  scoreHistoryFromReport,
  severitySlices,
  severitySummary,
  topIssues,
  truncateText,
} from "./report-ui";
import type { ScanReportResponse } from "./api";

describe("Report UI helpers", () => {
  it("labels report status and unavailable scores", () => {
    assert.equal(reportStatusLabel("ready"), "Ready");
    assert.equal(reportStatusLabel("partial"), "Partial");
    assert.equal(reportStatusLabel("unavailable"), "Unavailable");
    assert.equal(displayScore(82), "82");
    assert.equal(displayScore(null), "Unavailable");
    assert.equal(displayScoreOutOf100(82), "82 / 100");
    assert.equal(displayScoreOutOf100(undefined), "Unavailable");
    assert.equal(metricOrUnavailable(null, "ms"), "Unavailable");
    assert.equal(metricOrUnavailable(120, "ms"), "120 ms");
  });

  it("formats dates and empty states", () => {
    assert.match(formatReportDate("2026-09-22T10:00:00.000Z"), /September 22, 2026/);
    assert.equal(formatReportDate(null), "Unavailable");
    assert.equal(emptyReportCopy("loading").title, "Loading report");
    assert.equal(emptyReportCopy("error").title, "Unable to load report");
    assert.match(emptyReportCopy("error").body, /could not assemble the report/i);
    assert.match(emptyReportCopy("incomplete").body, /after the scan completes/i);
  });

  it("includes report navigation labels", () => {
    const labels = REPORT_SECTIONS.map((item) => item.label);
    assert.ok(labels.includes("Overview"));
    assert.ok(labels.includes("Score Breakdown"));
    assert.ok(labels.includes("Methodology"));
    assert.ok(labels.includes("Competitors"));
  });

  it("does not use ranking, compliance, or business-prediction claims", () => {
    const copy = [
      emptyReportCopy("error").body,
      emptyReportCopy("incomplete").body,
      "Detected trust and credibility signals",
      "Observable conversion-readiness signals",
    ].join(" ");
    assert.equal(containsForbiddenReportClaims(copy), false);
    assert.equal(containsForbiddenReportClaims("Your site will get a ChatGPT ranking."), true);
    assert.equal(containsForbiddenReportClaims("The website is WCAG compliant."), true);
    assert.equal(containsForbiddenReportClaims("This will increase conversions by 20%."), true);
  });

  it("truncates long report copy without changing short text", () => {
    assert.equal(truncateText("Ready"), "Ready");
    assert.equal(truncateText("   "), "");
    assert.equal(truncateText("abcdefghijklmnopqrstuvwxyz", 10), "abcdefghi…");
  });

  it("builds dashboard slices from stored report fields", () => {
    const report = {
      pages: {
        available: true,
        distribution: { healthy: 28, have_issues: 15, broken: 2, redirects: 3, blocked: 1 },
      },
      issues: {
        by_severity: { critical: 5, high: 12, medium: 20, low: 13 },
        priority_issues: [
          { issue_id: "b", title: "Low", category: "SEO", severity: "low", priority: "low", affected_page_count: 9, href: "/b" },
          { issue_id: "a", title: "Critical", category: "SEO", severity: "critical", priority: "high", affected_page_count: 4, href: "/a" },
        ],
      },
      recommendations: { by_category: { SEO: 3, Performance: 4, Accessibility: 4 } },
    } as unknown as ScanReportResponse;
    const pages = crawledPageSlices(report);
    assert.equal(pages.find((item) => item.id === "healthy")?.count, 28);
    assert.equal(formatPercent(28, 49), "57.1%");
    assert.equal(severitySlices(report.issues.by_severity)[0]?.count, 5);
    assert.match(severitySummary(severitySlices(report.issues.by_severity)), /50 total issues: 5 critical, 12 high, 20 medium, 13 low/);
    assert.equal(topIssues(report, 5)[0]?.issue_id, "a");
    assert.deepEqual(
      recommendationCategoryRows(report.recommendations.by_category).map((row) => row.label),
      ["Accessibility", "Performance", "SEO"],
    );
    assert.equal(compactCategoryLabel("AEO / AI Search Readiness"), "AEO");
    assert.equal(headerStatusLabel("completed", "ready"), "Completed");
    assert.deepEqual(scoreHistoryFromReport(report), []);
    assert.equal(previousScanDelta(report), null);
    assert.equal(classifyPageItem({ crawl_status: "crawled", issue_count: 0 }), "healthy");
    assert.equal(classifyPageItem({ crawl_status: "failed", failure_reason: "The page could not be reached." }), "broken");
    assert.equal(classifyPageItem({ crawl_status: "skipped", skip_reason: "Redirect left the scanned website." }), "redirects");
    assert.equal(classifyPageItem({ crawl_status: "skipped", skip_reason: "Disallowed destination." }), "blocked");
  });
});
