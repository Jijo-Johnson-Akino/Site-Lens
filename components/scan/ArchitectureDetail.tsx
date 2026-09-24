"use client";

import Link from "next/link";

import type { ArchitectureNeighbor, ArchitecturePageResponse } from "@/lib/scan/api";
import { architectureFlags, crawlDepthLabel, nodeHeading, urlPathDepthLabel } from "@/lib/scan/architecture-ui";
import { crawlStatusLabel, httpLabel, indexableLabel, pageTitle } from "@/lib/scan/pages-ui";
import { cn } from "@/lib/utils";

export function ArchitectureDetail({
  scanId,
  detail,
  onSelectPage,
}: {
  scanId: string;
  detail: ArchitecturePageResponse;
  onSelectPage: (id: string) => void;
}) {
  const page = detail.page;
  const flags = architectureFlags(page);
  const counts = page.severity_counts || {};
  return (
    <aside className="flex max-h-[720px] flex-col overflow-y-auto rounded-2xl border border-border bg-card p-5 shadow-sm">
      <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">Page</p>
      <h2 className="mt-2 text-lg font-semibold text-foreground">{nodeHeading(page)}</h2>
      <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{page.final_url || page.url}</p>
      <dl className="mt-4 grid gap-3 text-sm">
        <Info label="Page type" value={page.page_type_label || page.page_type} />
        <Info label="Crawl status" value={crawlStatusLabel(page.crawl_status)} />
        <Info label="HTTP status" value={httpLabel(page.http_status)} />
      </dl>

      <h3 className="mt-6 text-sm font-semibold text-foreground">Architecture</h3>
      <dl className="mt-3 grid gap-3 text-sm">
        <Info label="Crawl depth" value={crawlDepthLabel(detail.architecture.crawl_depth)} />
        <Info label="URL path depth" value={urlPathDepthLabel(detail.architecture.url_path_depth)} />
        <Info label="Inbound internal links" value={String(detail.architecture.inbound_internal_links)} />
        <Info label="Outbound internal links" value={String(detail.architecture.outbound_internal_links)} />
      </dl>
      {flags.length ? (
        <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
          {flags.map((flag) => (
            <li key={flag}>{flag}</li>
          ))}
        </ul>
      ) : null}
      {page.potential_orphan ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Potential orphan page based on the crawled internal-link graph.
        </p>
      ) : null}

      {(page.indexable != null || page.canonical_url) && (
        <>
          <h3 className="mt-6 text-sm font-semibold text-foreground">SEO</h3>
          <dl className="mt-3 grid gap-3 text-sm">
            {page.indexable != null ? <Info label="Indexability" value={indexableLabel(page.indexable)} /> : null}
            <Info label="Canonical" value={page.canonical_url} mono />
          </dl>
        </>
      )}

      {(page.word_count != null || page.page_type) && (
        <>
          <h3 className="mt-6 text-sm font-semibold text-foreground">Content</h3>
          <dl className="mt-3 grid gap-3 text-sm">
            <Info label="Word count" value={page.word_count != null ? String(page.word_count) : null} />
            <Info label="Page type" value={page.page_type_label || page.page_type} />
          </dl>
        </>
      )}

      <h3 className="mt-6 text-sm font-semibold text-foreground">Issues</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        {page.issue_count === 1 ? "1 issue" : `${page.issue_count} issues`}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        {[
          counts.critical ? `${counts.critical} Critical` : null,
          counts.high ? `${counts.high} High` : null,
          counts.medium ? `${counts.medium} Medium` : null,
          counts.low ? `${counts.low} Low` : null,
        ]
          .filter(Boolean)
          .join(" · ")}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Link
          href={`/scan/${scanId}/issues?page_url=${encodeURIComponent(page.normalized_url)}`}
          className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-muted/40"
        >
          View Issues
        </Link>
        <Link href={`/scan/${scanId}/pages/${page.id}`} className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-muted/40">
          View Page
        </Link>
      </div>

      <h3 className="mt-6 text-sm font-semibold text-foreground">Inbound links</h3>
      <NeighborList
        items={detail.inbound_links}
        empty="No inbound internal links were observed in this crawl."
        onSelectPage={onSelectPage}
        kind="source"
      />
      <h3 className="mt-6 text-sm font-semibold text-foreground">Outbound links</h3>
      <NeighborList
        items={detail.outbound_links}
        empty="No outbound internal links were observed in this crawl."
        onSelectPage={onSelectPage}
        kind="destination"
      />
    </aside>
  );
}

function NeighborList({
  items,
  empty,
  onSelectPage,
  kind,
}: {
  items: ArchitectureNeighbor[];
  empty: string;
  onSelectPage: (id: string) => void;
  kind: "source" | "destination";
}) {
  if (!items.length) {
    return <p className="mt-2 text-sm text-muted-foreground">{empty}</p>;
  }
  return (
    <ul className="mt-2 space-y-2 text-sm">
      {items.map((item) => (
        <li key={item.id} className="rounded-lg border border-border bg-muted/20 px-3 py-2">
          <button type="button" className="text-left font-medium text-foreground hover:underline" onClick={() => onSelectPage(item.page_id)}>
            {pageTitle(item.title)}
          </button>
          <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{item.path}</p>
          {item.anchor_text ? <p className="mt-1 text-xs text-muted-foreground">“{item.anchor_text}”</p> : null}
          <p className="sr-only">{kind} page</p>
        </li>
      ))}
    </ul>
  );
}

function Info({ label, value, mono }: { label: string; value: string | null | undefined; mono?: boolean }) {
  if (value == null || value === "" || value === "—") {
    return null;
  }
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={cn("mt-0.5 break-all text-foreground", mono && "font-mono text-xs")}>{value}</dd>
    </div>
  );
}
