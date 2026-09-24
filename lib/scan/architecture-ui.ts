import type { ArchitectureNode } from "@/lib/scan/api";
import { pageTitle } from "@/lib/scan/pages-ui";

export function crawlDepthLabel(depth: number | null | undefined): string {
  if (typeof depth !== "number") {
    return "Unknown";
  }
  return `Depth ${depth}`;
}

export function urlPathDepthLabel(depth: number | null | undefined): string {
  if (typeof depth !== "number") {
    return "Unknown";
  }
  return String(depth);
}

export function architectureFlags(node: Pick<ArchitectureNode, "potential_orphan" | "terminal_page" | "dead_end">): string[] {
  const flags: string[] = [];
  if (node.potential_orphan) {
    flags.push("Potential orphan page");
  }
  if (node.terminal_page) {
    flags.push("Terminal page");
  } else if (node.dead_end) {
    flags.push("Internal-link dead end");
  }
  return flags;
}

export function nodeTone(
  node: Pick<ArchitectureNode, "crawl_status" | "issue_count" | "severity_counts" | "potential_orphan">,
): "failed" | "critical" | "warn" | "orphan" | "default" {
  if (node.crawl_status === "failed") {
    return "failed";
  }
  const counts = node.severity_counts || {};
  if ((counts.critical || 0) > 0 || (counts.high || 0) > 0) {
    return "critical";
  }
  if ((node.issue_count || 0) > 0) {
    return "warn";
  }
  if (node.potential_orphan) {
    return "orphan";
  }
  return "default";
}

export function nodeHeading(node: Pick<ArchitectureNode, "title" | "path">): string {
  return pageTitle(node.title);
}

export function graphLimitMessage(shown: number, matching: number, limited: boolean): string | null {
  if (!limited) {
    return null;
  }
  return `Showing ${shown} of ${matching} crawled pages.`;
}
